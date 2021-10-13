import asyncio
import dataclasses
from asyncio import Queue
from typing import Type, Set, Optional, Iterable, Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from strawberry.types import Info

from strawberry_mage.backends.python.converter import SQLAlchemyModelConverter
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.backend import DummyDataBackend
from strawberry_mage.core.types import IEntityModel, GraphQLOperation


class PythonBackend(DummyDataBackend):
    dataset = None

    def __init__(self, engines_count=100):
        self.converter = SQLAlchemyModelConverter(create_async_engine('sqlite+aiosqlite:///'))
        self.engines = Queue(maxsize=engines_count)

    def _collect_references(self, mappings: Dict[PythonEntityModel, _SQLAlchemyModel], entry: IEntityModel):
        for a in entry.get_attributes():
            attr = getattr(entry, a, None)
            if attr and isinstance(attr, PythonEntityModel):
                if attr not in mappings:
                    mappings[attr] = attr.sqla_model(**dataclasses.asdict(attr))
                    self._collect_references(mappings, attr)

    def _build_dataset(self, dataset: Iterable[PythonEntityModel]):
        mappings: Dict[PythonEntityModel, _SQLAlchemyModel] = {}
        for entry in dataset:
            mappings[entry] = entry.sqla_model(**dataclasses.asdict(entry))
            self._collect_references(mappings, entry)
        return mappings

    def add_dataset(self, dataset: Iterable[PythonEntityModel]):
        self.dataset = self._build_dataset(dataset).values()

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
        return {GraphQLOperation(i) for i in range(1, 9)}

    async def resolve(self, model: Type[PythonEntityModel], operation: GraphQLOperation, info: Info, data: Any,
                      dataset: Optional[Iterable[PythonEntityModel]] = None) -> Any:
        while self.engines.empty():
            await asyncio.sleep(0.00001)
        engine: AsyncEngine = await self.engines.get()
        if dataset:
            self.add_dataset(dataset)
        with AsyncSession(engine) as session:
            session.add_all(self.dataset)
            await session.commit()
        res = await model.sqla_model.__backend__.resolve(model.sqla_model, operation, info, data,
                                                         sessionmaker(engine, expire_on_commit=False,
                                                                      class_=AsyncSession))
        async with AsyncSession(engine) as session:
            for m in self.converter.base.metadata.sorted_tables:
                await session.run_sync(lambda s: s.query(m).delete())
        await self.engines.put(engine)
        return res

    def pre_setup(self, models: Iterable[Type['IEntityModel']]) -> None:
        for _ in range(self.engines.maxsize):
            e = create_async_engine('sqlite+aiosqlite://')
            self.engines.put_nowait(e)

            async def set_up():
                async with e.begin() as conn:
                    await conn.run_sync(self.converter.base.metadata.create_all)

            asyncio.get_event_loop().create_task(set_up()).__await__()

    async def post_setup(self) -> None:
        pass
