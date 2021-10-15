import asyncio
import dataclasses
from asyncio import Queue
from concurrent.futures import ThreadPoolExecutor
from inspect import ismethod
from typing import Type, Set, Optional, Iterable, Dict, Any, List, Union

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from strawberry.types import Info

from strawberry_mage.backends.python.converter import SQLAlchemyModelConverter
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.backend import DummyDataBackend
from strawberry_mage.core.types import IEntityModel, GraphQLOperation


class PythonBackend(DummyDataBackend):
    dataset: List[_SQLAlchemyModel] = []
    _dataset_dirty = False

    def __init__(self, engines_count=100):
        self.converter = SQLAlchemyModelConverter(create_async_engine('sqlite+aiosqlite:///'))
        self.engines = Queue(maxsize=engines_count)

    def _create_entity(self, mappings: Dict[PythonEntityModel, _SQLAlchemyModel], original: PythonEntityModel):
        data = {
            **{k: v for k, v in vars(original).items() if not k.startswith('_') and not ismethod(v)},
            **self._collect_references(mappings, original)
        }
        return original.sqla_model(**data)

    def _collect_references(self, mappings: Dict[PythonEntityModel, _SQLAlchemyModel], entry: IEntityModel):
        results: Dict[str, Union[_SQLAlchemyModel, Iterable[_SQLAlchemyModel]]] = {}
        for a in entry.get_attributes():
            attr = getattr(entry, a, None)
            if attr and isinstance(attr, PythonEntityModel):
                if attr not in mappings:
                    mappings[attr] = self._create_entity(mappings, attr)
                results[a] = mappings[attr]
            elif isinstance(attr, list):
                converted = []
                for e in attr:
                    if e not in mappings:
                        mappings[e] = self._create_entity(mappings, e)
                    converted.append(mappings[e])
                results[a] = converted
        return results

    def _build_dataset(self, dataset: Iterable[PythonEntityModel]):
        mappings: Dict[PythonEntityModel, _SQLAlchemyModel] = {}
        for entry in dataset:
            data = {**{k: v for k, v in vars(entry).items() if not k.startswith('_') and not ismethod(v)},
                    **self._collect_references(mappings, entry)}
            mappings[entry] = entry.sqla_model(**data)
        return mappings

    def add_dataset(self, dataset: Iterable[PythonEntityModel]):
        self.dataset = list(self._build_dataset(dataset).values())

    def _remove_pks(self, model, attrs):
        return [a for a in attrs if a not in self.get_primary_key(model)]

    def get_attributes(self, model: Type[IEntityModel], operation: Optional[GraphQLOperation] = None) -> Iterable[str]:
        all_ = super().get_attributes(model, operation)
        if operation in {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY, None}:
            return all_
        all_ = self._remove_pks(model, all_)
        if operation in {GraphQLOperation.CREATE_ONE, GraphQLOperation.CREATE_MANY, GraphQLOperation.UPDATE_ONE,
                         GraphQLOperation.UPDATE_MANY}:
            return all_
        return []

    def get_parent_class_name(self, model: Type[IEntityModel]):
        if model.mro()[1].__name__ != 'PythonEntityModel':
            return model.mro()[1].__name__

    def get_operations(self, model: Type[IEntityModel]) -> Set[GraphQLOperation]:
        return {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY}

    async def resolve(self, model: Type[PythonEntityModel], operation: GraphQLOperation, info: Info, data: Any,
                      dataset: Optional[Iterable[PythonEntityModel]] = None) -> Any:
        while self.engines.empty() or self._dataset_dirty:
            await asyncio.sleep(0.00001)
        engine: AsyncEngine = await self.engines.get()
        if dataset:
            self.add_dataset(dataset)
        async with AsyncSession(engine) as session:
            self._dataset_dirty = True
            session.add_all(self.dataset)
            await session.commit()
            session.expunge_all()
            self._dataset_dirty = False
        res = await model.sqla_model.__backend__.resolve(model.sqla_model, operation, info, data,
                                                         sessionmaker(engine, expire_on_commit=False,
                                                                      class_=AsyncSession))
        async with AsyncSession(engine) as session:
            for m in self.converter.base.metadata.sorted_tables:
                await session.run_sync(lambda s: s.query(m).delete())
        await self.engines.put(engine)
        return res

    def pre_setup(self, models: Iterable[Type['IEntityModel']]) -> None:
        pass

    def post_setup(self) -> None:
        for _ in range(self.engines.maxsize):
            e = create_async_engine('sqlite+aiosqlite://')
            self.engines.put_nowait(e)

            async def set_up():
                async with e.begin() as conn:
                    await conn.run_sync(self.converter.base.metadata.create_all)

            pool = ThreadPoolExecutor()
            pool.submit(asyncio.run, set_up()).result()
