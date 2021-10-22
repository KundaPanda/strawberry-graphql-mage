from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type, Union

from sqlalchemy import Integer, String, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    ColumnProperty,
    Mapper,
    RelationshipProperty,
    sessionmaker,
)
from sqlalchemy.orm.interfaces import MANYTOMANY, ONETOMANY
from sqlalchemy.orm.util import AliasedInsp
from strawberry.schema.types import ConcreteType
from strawberry.types import Info

from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.backends.sqlalchemy.operations import (
    create_,
    delete_,
    list_,
    retrieve_,
    update_,
)
from strawberry_mage.core.backend import DataBackendBase
from strawberry_mage.core.types import GraphQLOperation, IEntityModel


class SQLAlchemyBackend(DataBackendBase):
    _TYPE_MAP = {Integer: int, String: str}

    def __init__(self, engine: Engine):
        self._session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @staticmethod
    def _remove_polymorphic_cols(model: Type[Union[IEntityModel, _SQLAlchemyModel]], cols: List[str]) -> List[str]:
        inspection: Mapper = inspect(model)
        if inspection.polymorphic_on is None:
            return cols
        return [c for c in cols if c != inspection.polymorphic_on.key]

    @staticmethod
    def _remove_pk_cols(model: Type[Union[IEntityModel, _SQLAlchemyModel]], cols: List[str]):
        return [c for c in cols if c not in model.get_primary_key()]

    @staticmethod
    def _is_nullable(col: Union[ColumnProperty, RelationshipProperty]):
        if isinstance(col, ColumnProperty):
            return getattr(col, "nullable", False) or getattr(col.expression, "nullable", False)
        if col.direction in {ONETOMANY}:
            return True
        return all((c.nullable for c in col.local_columns))

    def get_attributes(
        self,
        model: Type[Union[IEntityModel, _SQLAlchemyModel]],
        operation: Optional[GraphQLOperation] = None,
    ) -> List[str]:
        inspection = inspect(model)
        all_ = [a.key for a in (inspection.mapper.attrs if isinstance(inspection, AliasedInsp) else inspection.attrs)]
        if operation in {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY, None}:
            return all_
        all_ = self._remove_polymorphic_cols(model, all_)
        all_ = self._remove_pk_cols(model, all_)
        if operation in {
            GraphQLOperation.CREATE_ONE,
            GraphQLOperation.CREATE_MANY,
            GraphQLOperation.UPDATE_ONE,
            GraphQLOperation.UPDATE_MANY,
        }:
            return all_
        return []

    @lru_cache
    def _get_attribute_type(self, attr: Union[ColumnProperty, RelationshipProperty]) -> Type:
        python_type = (
            attr.expression.type.python_type if isinstance(attr, ColumnProperty) else attr.entity.class_.__name__
        )
        if self._is_nullable(attr):
            python_type = Optional[python_type]
        if isinstance(attr, RelationshipProperty) and attr.direction in {
            ONETOMANY,
            MANYTOMANY,
        }:
            python_type = List[python_type]
            # if self._is_nullable(attr):
            #     python_type = Optional[python_type]
        return python_type

    @lru_cache
    def get_attribute_type(self, model: Type[Union[IEntityModel, _SQLAlchemyModel]], attr: str) -> Type:
        inspection = inspect(model)
        col: Union[ColumnProperty, RelationshipProperty] = getattr(
            inspection.mapper.attrs if isinstance(inspection, AliasedInsp) else inspection.attrs,
            attr,
        )
        return self._get_attribute_type(col)

    @lru_cache
    def get_attribute_types(self, model: Type[Union[IEntityModel, _SQLAlchemyModel]]) -> Dict[str, Type]:
        return {attr: self.get_attribute_type(model, attr) for attr in self.get_attributes(model)}

    def get_primary_key(self, model: Type[Union[IEntityModel, _SQLAlchemyModel]]) -> Tuple:
        return tuple(a.key for a in inspect(model).primary_key)

    def get_parent_class_name(self, model: Type["IEntityModel"]) -> Optional[str]:
        inspection = inspect(model)
        if inspection.polymorphic_on is not None:
            return [
                m.class_.__name__
                for m in inspection.polymorphic_map.values()
                if m.local_table == inspection.polymorphic_on.table
            ][0]
        return None

    def get_children_class_names(self, model: Type[_SQLAlchemyModel]) -> Optional[List[str]]:
        inspection = inspect(model)
        if inspection.polymorphic_on is not None and inspection.polymorphic_on.table == model.__table__:
            return [m.class_.__name__ for m in inspection.polymorphic_map.values()]
        return None

    def get_operations(self, model: Type[Union[IEntityModel, _SQLAlchemyModel]]) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    def get_polymorphic_type(self, base_type: ConcreteType):
        return base_type.implementation

    async def resolve(
        self,
        model: Type[Union[IEntityModel, _SQLAlchemyModel]],
        operation: GraphQLOperation,
        info: Info,
        data: Any,
        session_factory: Optional[sessionmaker] = None,
    ) -> Any:
        async with (session_factory if session_factory else self._session)() as s:
            for field in info.selected_fields:  # type: ignore
                selection = self._build_selection(field, model.get_schema_manager())
                if operation == GraphQLOperation.QUERY_MANY:
                    return await list_(s, model, data, selection)
                if operation == GraphQLOperation.QUERY_ONE:
                    return await retrieve_(s, model, data, selection)
                if operation == GraphQLOperation.CREATE_ONE:
                    return [*(await create_(s, model, [data], selection)), None][0]
                if operation == GraphQLOperation.CREATE_MANY:
                    return await create_(s, model, data, selection)
                if operation == GraphQLOperation.UPDATE_ONE:
                    return [*(await update_(s, model, [data], selection)), None][0]
                if operation == GraphQLOperation.UPDATE_MANY:
                    return await update_(s, model, data, selection)
                if operation == GraphQLOperation.DELETE_ONE:
                    return await delete_(s, model, [data])
                if operation == GraphQLOperation.DELETE_MANY:
                    return await delete_(s, model, data)

    def pre_setup(self, models: Iterable[Type["IEntityModel"]]) -> None:
        pass

    def post_setup(self) -> None:
        pass
