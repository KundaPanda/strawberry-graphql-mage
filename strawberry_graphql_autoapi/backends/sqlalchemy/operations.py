import dataclasses
from functools import partial
from typing import List, Type, Any, Union, Dict

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.orm import DeclarativeMeta, Session
from sqlalchemy.sql.expression import ColumnOperators as ops

from strawberry_graphql_autoapi.core.strawberry_types import DeleteResult, OrderingDirection, ObjectFilter
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


def add_default_ordering(model: Type[Union[DeclarativeMeta, IEntityModel]], ordering: List[Any]):
    ordering_type = model.get_strawberry_type().ordering
    return ordering + [ordering_type(**{k: OrderingDirection.DESC for k in model.get_primary_key()})]


def create_filter_op(column: Any, op_name: str, value: Any):
    return {
        'exact': ops.__eq__(column, value)
    }.get(op_name)


def create_object_filters(model: Type[Union[DeclarativeMeta, IEntityModel]], path: str, filter_: ObjectFilter):
    filters = []
    for col, value in dataclasses.asdict(filter_).items():
        if value is None:
            continue
        if col == 'AND_':
            filters.append(and_(*[create_object_filters(model, path, f) for f in value]))
        elif col == 'OR_':
            filters.append(or_(*[create_object_filters(model, path, f) for f in value]))
        elif isinstance(value, ObjectFilter):
            # TODO: model, joins
            # noinspection PyTypeChecker
            filters.append(create_object_filters(model.get_schema_manager().get_model_for_name(col), f'{path}.{col}', value))
        else:
            for operation, scalar_value in dataclasses.asdict(value).items():
                filters.append(create_filter_op(getattr(model, col), operation, scalar_value))
    return and_(*filters)


def list_(session: Session, model: Type[DeclarativeMeta], data: Any):
    ordering = add_default_ordering(model, getattr(data, 'ordering', []))
    return session.execute(select(model)).scalars()
