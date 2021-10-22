import asyncio
from asyncio import Lock, Queue
from concurrent.futures import ThreadPoolExecutor
from dataclasses import MISSING
from typing import Any, Dict, Iterable, List, Optional, Set, Type

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import make_transient, sessionmaker
from strawberry.schema.types import ConcreteType
from strawberry.types import Info

from strawberry_mage.backends.python.converter import SQLAlchemyModelConverter
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.backend import DataBackendBase
from strawberry_mage.core.schema import SchemaManager
from strawberry_mage.core.types import GraphQLOperation, IEntityModel


class PythonBackend(DataBackendBase[PythonEntityModel]):
    dataset: List[_SQLAlchemyModel] = []
    _dataset_lock: Optional[Lock] = None
    _models: Iterable[Type[PythonEntityModel]]
    _sqla_manager: SchemaManager

    def __init__(self, engines_count=20):
        self.converter = SQLAlchemyModelConverter(create_async_engine("sqlite+aiosqlite:///"))
        self.engines = Queue(maxsize=engines_count)

    def __del__(self):
        while self.engines.get_nowait():
            pass

    def __create_entity(
        self,
        mappings: Dict[PythonEntityModel, _SQLAlchemyModel],
        original: PythonEntityModel,
    ):
        return original.sqla_model(**self.__extract_attributes(mappings, original))

    def __extract_attributes(self, mappings: Dict[PythonEntityModel, _SQLAlchemyModel], entry: IEntityModel):
        results: Dict[str, Any] = {}
        for a in entry.get_attributes():
            attr = getattr(entry, a, MISSING)
            if attr and isinstance(attr, PythonEntityModel):
                if attr not in mappings:
                    mappings[attr] = self.__create_entity(mappings, attr)
                results[a] = mappings[attr]
            elif isinstance(attr, list):
                converted = []
                for e in attr:
                    if isinstance(e, PythonEntityModel):
                        if e not in mappings:
                            mappings[e] = self.__create_entity(mappings, e)
                        converted.append(mappings[e])
                    else:
                        converted.append(e)
                results[a] = converted
            elif attr != MISSING:
                results[a] = attr
        return results

    def __build_dataset(self, dataset: Iterable[PythonEntityModel]):
        mappings: Dict[PythonEntityModel, _SQLAlchemyModel] = {}
        for entry in dataset:
            mappings[entry] = self.__create_entity(mappings, entry)
        return mappings

    def add_dataset(self, dataset: Iterable[PythonEntityModel], *args, **kwargs):
        self.dataset = list(self.__build_dataset(dataset).values())

    def _remove_pks(self, model, attrs):
        return [a for a in attrs if a not in self.get_primary_key(model)]

    def get_attributes(self, model: Type[PythonEntityModel], operation: Optional[GraphQLOperation] = None) -> List[str]:
        all_ = super().get_attributes(model, operation)
        if operation in {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY, None}:
            return all_
        all_ = self._remove_pks(model, all_)
        if operation in {
            GraphQLOperation.CREATE_ONE,
            GraphQLOperation.CREATE_MANY,
            GraphQLOperation.UPDATE_ONE,
            GraphQLOperation.UPDATE_MANY,
        }:
            return all_
        return []

    def get_parent_class_name(self, model: Type[IEntityModel]):
        if model.mro()[1].__name__ != "PythonEntityModel":
            return model.mro()[1].__name__
        elif model.__subclasses__():
            return model.__name__

    def get_operations(self, model: Type[IEntityModel]) -> Set[GraphQLOperation]:
        return {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY}

    def get_polymorphic_type(self, base_type: ConcreteType):
        return base_type.implementation

    async def resolve(
        self,
        model: Type[PythonEntityModel],
        operation: GraphQLOperation,
        info: Info,
        data: Any,
        *args,
        dataset: Optional[Iterable[PythonEntityModel]] = None,
        **kwargs
    ) -> Any:
        if self._dataset_lock is None:
            self._dataset_lock = Lock()
        while self.engines.empty():
            await asyncio.sleep(0.00001)
        engine: AsyncEngine = await self.engines.get()
        if dataset:
            self.add_dataset(dataset)
        session_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with session_factory() as session:
            async with self._dataset_lock:
                session.add_all(self.dataset)
                await session.commit()
                for instance in self.dataset:
                    make_transient(instance)
        res = await model.get_sqla_model().__backend__.resolve(
            model.get_sqla_model(), operation, info, data, session_factory
        )
        async with engine.begin() as conn:
            await conn.run_sync(self.converter.base.metadata.drop_all)
            await conn.run_sync(self.converter.base.metadata.create_all)
        await self.engines.put(engine)
        return res

    def pre_setup(self, models: Iterable[Type[PythonEntityModel]]) -> None:
        self._models = models

    def post_setup(self) -> None:
        self._sqla_manager = SchemaManager(
            *[m.get_sqla_model() for m in self._models],
            backend=self.converter.base.__backend__,
        )
        for i in range(self.engines.maxsize):
            e = create_async_engine("sqlite+aiosqlite://")
            self.engines.put_nowait(e)

            async def set_up():
                async with e.begin() as conn:
                    await conn.run_sync(self.converter.base.metadata.create_all)

            pool = ThreadPoolExecutor()
            pool.submit(asyncio.run, set_up()).result()
