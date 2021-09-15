from functools import lru_cache
from typing import Iterable, Any, Type, Dict, Tuple, Set, Union, Optional, List

from sqlalchemy import inspect, Integer, String
from sqlalchemy.orm import ColumnProperty, DeclarativeMeta, RelationshipProperty, Mapper, ONETOMANY, MANYTOMANY, \
    Session, sessionmaker

from strawberry_graphql_autoapi.backends.sqlalchemy.operations import list_, create_, retrieve_, update_, delete_
from strawberry_graphql_autoapi.core.backend import DataBackendBase
from strawberry_graphql_autoapi.core.types import IEntityModel, GraphQLOperation


class SQLAlchemyBackend(DataBackendBase):
    _TYPE_MAP = {
        Integer: int,
        String: str
    }

    def __init__(self, session_maker: sessionmaker):
        self._session = session_maker

    @staticmethod
    def _remove_polymorphic_cols(model: Type[Union[IEntityModel, DeclarativeMeta]], cols: List[str]) -> List[str]:
        inspection: Mapper = inspect(model)
        if inspection.polymorphic_on is None:
            return cols
        return [c for c in cols if c != inspection.polymorphic_on.key]

    @staticmethod
    def _remove_pk_cols(model: Type[Union[IEntityModel, DeclarativeMeta]], cols: List[str]):
        return [c for c in cols if c not in model.get_primary_key()]

    @staticmethod
    def _is_nullable(col: Union[ColumnProperty, RelationshipProperty]):
        if isinstance(col, ColumnProperty):
            return getattr(col, 'nullable', False) or getattr(col.expression, 'nullable', False)
        if col.direction in {ONETOMANY}:
            return True
        return all((c.nullable for c in col.local_columns))

    def get_attributes(self, model: Type[Union[IEntityModel, DeclarativeMeta]],
                       operation: Optional[GraphQLOperation] = None) -> List[str]:
        all_ = [a.key for a in inspect(model).attrs]
        if operation in {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY, None}:
            return all_
        all_ = self._remove_polymorphic_cols(model, all_)
        all_ = self._remove_pk_cols(model, all_)
        if operation in {GraphQLOperation.CREATE_ONE, GraphQLOperation.CREATE_MANY, GraphQLOperation.UPDATE_ONE,
                         GraphQLOperation.UPDATE_MANY}:
            return all_
        return []

    @lru_cache
    def _get_attribute_type(self, attr: Union[ColumnProperty, RelationshipProperty]) -> Type:
        python_type = attr.expression.type.python_type \
            if isinstance(attr, ColumnProperty) \
            else attr.entity.class_.__name__
        if self._is_nullable(attr):
            python_type = Optional[python_type]
        if isinstance(attr, RelationshipProperty) and attr.direction in {ONETOMANY, MANYTOMANY}:
            python_type = List[python_type]
            # if self._is_nullable(attr):
            #     python_type = Optional[python_type]
        return python_type

    @lru_cache
    def get_attribute_type(self, model: Type[Union[IEntityModel, DeclarativeMeta]], attr: str) -> Type:
        col: Union[ColumnProperty, RelationshipProperty] = getattr(inspect(model).attrs, attr)
        return self._get_attribute_type(col)

    def get_attribute_types(self, model: Type[Union[IEntityModel, DeclarativeMeta]]) -> Dict[str, Type]:
        return {attr.key: self._get_attribute_type(attr) for attr in inspect(model).attrs}

    def get_primary_key(self, model: Type[Union[IEntityModel, DeclarativeMeta]]) -> Tuple:
        return tuple(a.key for a in inspect(model).primary_key)

    def get_operations(self, model: Type[Union[IEntityModel, DeclarativeMeta]]) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    def resolve(self, model: Type[Union[IEntityModel, DeclarativeMeta]], operation: GraphQLOperation, data: Any) -> Any:
        with self._session() as s:
            if operation == GraphQLOperation.QUERY_MANY:
                return list_(s, model, data)
            if operation == GraphQLOperation.QUERY_ONE:
                return retrieve_(s, model, data)
            if operation == GraphQLOperation.CREATE_ONE:
                return [*create_(s, model, [data]), None][0]
            if operation == GraphQLOperation.CREATE_MANY:
                return create_(s, model, data)
            if operation == GraphQLOperation.UPDATE_ONE:
                return [*update_(s, model, [data]), None][0]
            if operation == GraphQLOperation.UPDATE_MANY:
                return update_(s, model, data)
            if operation == GraphQLOperation.DELETE_ONE:
                return delete_(s, model, [data])
            if operation == GraphQLOperation.DELETE_MANY:
                return delete_(s, model, data)
