import dataclasses
from functools import partial
from typing import List, Type, Any, Union, Dict

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.orm import DeclarativeMeta, Session
from sqlalchemy.sql.expression import ColumnOperators as ops
from strawberry.arguments import is_unset

from strawberry_graphql_autoapi.core.strawberry_types import DeleteResult, OrderingDirection, QueryMany
from strawberry_graphql_autoapi.core.types import IEntityModel, GraphQLOperation


def _build_pk_query(model: Type[Union[DeclarativeMeta, IEntityModel]], data: Any):
    pk = model.get_primary_key()
    attribute_getter = partial(getattr, data)
    if isinstance(data, dict):
        attribute_getter = data.get
    return and_(*(getattr(model, key) == attribute_getter(key) for key in pk))


def _build_multiple_pk_query(model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    return or_(
        _build_pk_query(model, {k: getattr(entry._primary_key, k) for k in model.get_primary_key()}) for entry in data)


def _get_model_pk_values(model: Type[Union[DeclarativeMeta, IEntityModel]], data: DeclarativeMeta):
    return tuple(getattr(data, key) for key in model.get_primary_key())


def _get_dict_pk_values(model: Type[Union[DeclarativeMeta, IEntityModel]], data: Dict[str, Any]):
    return tuple(data.get(key) for key in model.get_primary_key())


def create_(session: Session, model: Type[DeclarativeMeta], data: List[Any]):
    models = [model(**dataclasses.asdict(create_type)) for create_type in data]
    session.add_all(models)
    session.commit()
    [session.refresh(m) for m in models]
    return models


def update_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    input_values = model.get_attributes(GraphQLOperation.CREATE_ONE)
    pk_filter = _build_multiple_pk_query(model, data)
    entities = {_get_model_pk_values(model, en): en for en in session.execute(select(model).where(pk_filter)).scalars()}
    for entry in data:
        for column in input_values:
            model_instance = entities[_get_dict_pk_values(model, entry)]
            setattr(model_instance, column,
                    getattr(entry, column,
                            getattr(model_instance, column)))
    session.add_all(entities.values())
    session.commit()
    [session.refresh(e) for e in entities.values()]
    return entities.values()


def delete_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    pk_q = _build_multiple_pk_query(model, data)
    statement = delete(model).where(pk_q)
    r = session.execute(statement)
    session.commit()
    return DeleteResult(affected_rows=r.rowcount)


def retrieve_(session: Session, model: Type[DeclarativeMeta], data: Any):
    return session.query(model).get(_get_model_pk_values(model, data))


def create_default_ordering(model: Type[Union[DeclarativeMeta, IEntityModel]], ordering: List[Dict]):
    return ordering + [{k: OrderingDirection.DESC for k in model.get_primary_key()}]


def cleanup_ordering(ordering: List[Dict]):
    result_ordering = []
    for ordering_entry in ordering:
        for field, value in ordering_entry.items():
            if isinstance(value, list):
                result_ordering.append({field: cleanup_ordering(value)})
            elif not is_unset(value):
                result_ordering.append({field: value})
    return result_ordering


def create_filter_op(column: Any, op_name: str, value: Any):
    return {
        'exact': ops.__eq__(column, value),
        'gt': ops.__gt__(column, value),
    }.get(op_name)


def strip_typename(type_: Union[str, Type]) -> str:
    while hasattr(type_, '__args__'):
        type_ = type_.of_type
    if isinstance(type_, str):
        return type_
    return type_.__name__


def create_object_filters(model: Type[IEntityModel], path: str, filters: List[Dict], aggregate_op=and_):
    result_filters = []
    for filter_ in filters:
        for col, value in filter_.items():
            if is_unset(value):
                continue
            if col == 'AND_':
                result_filters.append(create_object_filters(model, path, value))
            elif col == 'OR_':
                result_filters.append(create_object_filters(model, path, value, or_))
            else:
                for operation, filter_value in value.items():
                    if is_unset(filter_value):
                        continue
                    if isinstance(filter_value, dict):
                        # Nested filter
                        # TODO: model, joins
                        related_type_name = strip_typename(model.get_attribute_type(col))
                        related_model = model.get_schema_manager().get_model_for_name(related_type_name)
                        result_filters.append(create_object_filters(related_model, f'{path}.{col}', [filter_value]))
                    else:
                        result_filters.append(create_filter_op(getattr(model, col), operation, filter_value))
    return aggregate_op(*result_filters)


def list_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: QueryMany):
    dict_ordering = [dataclasses.asdict(o) for o in getattr(data, 'ordering', [])]
    ordering = create_default_ordering(model, dict_ordering)
    ordering = cleanup_ordering(ordering)
    dict_filter = [dataclasses.asdict(f) for f in getattr(data, 'filters', [])]
    filter_ = create_object_filters(model, 'root', dict_filter)
    return session.execute(select(model)).scalars()
