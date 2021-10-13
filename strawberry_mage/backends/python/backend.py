import asyncio
from asyncio import Queue
from typing import Type, Set, Optional, Iterable, Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from strawberry.types import Info

from strawberry_mage.backends.python.converter import SQLAlchemyModelConverter
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.backend import DummyDataBackend
from strawberry_mage.core.types import IEntityModel, GraphQLOperation


class PythonBackend(DummyDataBackend):
    dataset = None

    def __init__(self, engines_count=100):
        self.converter = SQLAlchemyModelConverter(create_async_engine('sqlite+aiosqlite:///'))
        self.engines = Queue(maxsize=engines_count)

    def _collect_references(self, results: Dict[Type[IEntityModel], Set[IEntityModel]], entry: IEntityModel):
        for a in entry.get_attributes():
            attr = getattr(entry, a, None)
            if attr and isinstance(attr, IEntityModel):
                if attr not in results[type(attr)]:
                    results[type(attr)].add(attr)
                    self._collect_references(results, attr)

    def _build_dataset(self, model: IEntityModel, dataset: Iterable[IEntityModel]):
        resulting_dataset: Dict[Type[IEntityModel], Set[IEntityModel]] \
            = {m: {} for m in model.get_schema_manager().get_models()}
        for entry in dataset:
            if type(entry) not in resulting_dataset:
                raise AttributeError(f"Unknown model data type {type(entry)}")
            resulting_dataset[type(entry)].add(entry)
        for type_, entries in resulting_dataset.items():
            for entry in entries:
                self._collect_references(resulting_dataset, entry)

    def add_dataset(self, dataset: Iterable[IEntityModel]):
        self.dataset = dataset

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

    async def resolve(self, model: Type[PythonEntityModel], operation: GraphQLOperation, info: Info, data: Any) -> Any:
        while self.engines.empty():
            await asyncio.sleep(0.00001)
        engine = await self.engines.get()
        res = await model.sqla_model.__backend__.resolve(model.sqla_model, operation, info, data,
                                                         sessionmaker(engine, expire_on_commit=False,
                                                                      class_=AsyncSession))
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

    # def resolve(self, model: Type[IEntityModel], operation: GraphQLOperation, info: Info, data: Any) -> Any:
    #     for field in info.selected_fields:
    #         selection = self._build_selection(field, model.get_schema_manager())
    #         if operation == GraphQLOperation.QUERY_MANY:
    #             return list_(model, data, selection)
    #         if operation == GraphQLOperation.QUERY_ONE:
    #             return retrieve_(model, data, selection)
    #         if operation == GraphQLOperation.CREATE_ONE:
    #             return [*create_(model, [data], selection), None][0]
    #         if operation == GraphQLOperation.CREATE_MANY:
    #             return create_(model, data, selection)
    #         if operation == GraphQLOperation.UPDATE_ONE:
    #             return [*update_(model, [data], selection), None][0]
    #         if operation == GraphQLOperation.UPDATE_MANY:
    #             return update_(model, data, selection)
    #         if operation == GraphQLOperation.DELETE_ONE:
    #             return delete_(model, [data])
    #         if operation == GraphQLOperation.DELETE_MANY:
    #             return delete_(model, data)
