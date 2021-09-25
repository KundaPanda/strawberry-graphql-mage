import dataclasses
from functools import partial
from typing import List, Type, Any, Union, Dict, Callable, Tuple

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.orm import DeclarativeMeta, Session, aliased, contains_eager
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql import Join, ColumnElement
from sqlalchemy.sql.expression import ColumnOperators as ops, join, desc
from sqlalchemy.sql.operators import ColumnOperators
from strawberry.arguments import is_unset, UNSET

from strawberry_graphql_autoapi.core.strawberry_types import DeleteResult, OrderingDirection, QueryMany, \
    PrimaryKeyField
from strawberry_graphql_autoapi.core.type_creator import strip_typename
from strawberry_graphql_autoapi.core.types import IEntityModel

JoinsType = Dict[str, Tuple[Type[Union[AliasedClass, DeclarativeMeta]], Union[Join, Type[DeclarativeMeta]]]]


def _build_pk_query(model: Type[Union[DeclarativeMeta, IEntityModel]], data: Any):
    pk = model.get_primary_key()
    if isinstance(data, dict):
        attribute_getter = data.get
    else:
        attribute_getter = partial(getattr, data)
    return and_(*(getattr(model, key) == attribute_getter(key) for key in pk))


def _build_multiple_pk_query(model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    return or_(
        _build_pk_query(model, {k: getattr(entry.primary_key_, k) for k in model.get_primary_key()}) for entry in data)


def _get_model_pk_values(model: Type[Union[DeclarativeMeta, IEntityModel]], data: dataclasses.dataclass):
    return tuple(getattr(data, key) for key in model.get_primary_key())


def _get_dict_pk_values(model: Type[Union[DeclarativeMeta, IEntityModel]], data: Dict[str, Any]):
    return tuple(data.get(key) for key in model.get_primary_key())


def _create_pk_class(data: Dict[str, Any]):
    return type('StubInput', (), {'primary_key_': type('StubPk', (), data)})()


def _set_instance_attrs(model: Type[Union[DeclarativeMeta, IEntityModel]], instance: object,
                        input_object: dataclasses.dataclass, session: Session):
    for prop in input_object.__dataclass_fields__:
        value = getattr(input_object, prop)
        if is_unset(value) or prop == 'primary_key_':
            continue
        dtype = strip_typename(model.get_attribute_type(prop))
        if isinstance(dtype, str):
            related_model = model.get_schema_manager().get_model_for_name(dtype)
            if isinstance(value, list):
                expr = select(related_model).where(_build_multiple_pk_query(related_model, value))
                setattr(instance, prop, session.execute(expr).scalars().all())
            else:
                setattr(instance, prop, session.query(related_model).get(dataclasses.asdict(value.primary_key_)))
        else:
            setattr(instance, prop, value)


def create_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any],
            selection: Dict[str, Dict]):
    # TODO: create related models as well maybe?
    models = []
    for create_type in data:
        instance = model()
        _set_instance_attrs(model, instance, create_type, session)
        models.append(instance)
    session.add_all(models)
    session.flush(models)
    primary_keys = [{key: getattr(instance, key) for key in model.get_primary_key()} for instance in models]
    session.commit()

    joins: JoinsType = {'': (model, model)}

    eager_options = create_selection_joins(model, '', selection, joins)
    ordering = create_ordering(model, '', add_default_ordering(model, []), joins)

    expression = select(model, *[j[0] for j in joins.values()]) \
        .select_from(*[j[1] for j in joins.values()]) \
        .filter(_build_multiple_pk_query(model, [_create_pk_class(instance) for instance in primary_keys])) \
        .order_by(*ordering)
    if eager_options is not None:
        expression = expression.options(eager_options)
    return session.execute(expression).unique().scalars().all()


def update_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any],
            selection: Dict[str, Dict]):
    pk_filter = _build_multiple_pk_query(model, data)
    entities = {_get_model_pk_values(model, en): en
                for en in session.execute(select(model).where(pk_filter)).scalars().all()}
    for entry in data:
        model_instance = entities[_get_model_pk_values(model, entry.primary_key_)]
        _set_instance_attrs(model, model_instance, entry, session)
    session.add_all(entities.values())
    session.commit()

    joins: JoinsType = {'': (model, model)}

    eager_options = create_selection_joins(model, '', selection, joins)
    ordering = create_ordering(model, '', add_default_ordering(model, []), joins)

    expression = select(model, *[j[0] for j in joins.values()]) \
        .select_from(*[j[1] for j in joins.values()]) \
        .filter(pk_filter) \
        .order_by(*ordering)
    if eager_options is not None:
        expression = expression.options(eager_options)
    return session.execute(expression).unique().scalars().all()


def delete_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    pk_q = _build_multiple_pk_query(model, data)
    statement = delete(model).where(pk_q)
    r = session.execute(statement)
    session.commit()
    return DeleteResult(affected_rows=r.rowcount)


def retrieve_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]],
              data: Union[PrimaryKeyField, dataclasses.dataclass], selection: Dict[str, Dict]):
    pk_filter = _build_pk_query(model, data.primary_key_)
    joins: JoinsType = {'': (model, model)}

    eager_options = create_selection_joins(model, '', selection, joins)

    expression = select(model, *[j[0] for j in joins.values()]) \
        .select_from(*[j[1] for j in joins.values()]) \
        .filter(pk_filter)
    if eager_options is not None:
        expression = expression.options(eager_options)
    return session.execute(expression).unique().scalar()


def add_default_ordering(model: Type[Union[DeclarativeMeta, IEntityModel]], ordering: List[Dict]):
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


def create_selection_joins(model: Type[IEntityModel], path: str, selection: Dict[str, Dict], joins: JoinsType,
                           eager_options: Any = None):
    for attr, sub_selection in selection.items():
        eager_options = _apply_nested(model, path, sub_selection, create_selection_joins, attr, joins, eager_options)
    return eager_options


def _apply_nested(model: Type[IEntityModel], path: str, input_: Any, op: Callable, attribute: str, joins: JoinsType,
                  eager_options: Any = None):
    nested_path = f'{path}.{attribute}'
    if nested_path not in joins:
        related_type_name = strip_typename(model.get_attribute_type(attribute))
        related_model = aliased(model.get_schema_manager().get_model_for_name(related_type_name), name=nested_path)
        ex = getattr(model, attribute).expression
        join_expression = getattr(model, ex.left.key) == getattr(related_model, ex.right.key) \
            if ex.right.table == related_model.__table__ \
            else getattr(model, ex.right.key) == getattr(related_model, ex.left.key)
        joins[nested_path] = related_model, join(joins[path][1], related_model, join_expression, isouter=True)
    eager_options = contains_eager(getattr(model, attribute).of_type(joins[nested_path][0])) \
        if eager_options is None \
        else eager_options.contains_eager(getattr(model, attribute).of_type(joins[nested_path][0]))
    return op(joins[nested_path][0], nested_path, input_, joins, eager_options)


def create_ordering(model: Type[IEntityModel], path: str, ordering: List[Dict], joins: JoinsType, *_) \
        -> List[ColumnElement]:
    result_ordering = []
    for entry in ordering:
        for attribute, value in entry.items():
            if isinstance(value, OrderingDirection):
                attr = getattr(model, attribute)
                result_ordering.append(desc(attr) if value == OrderingDirection.DESC else attr)
            else:
                result_ordering.extend(_apply_nested(model, path, value, create_ordering, attribute, joins))
    return result_ordering


def create_filter_op(column: Any, op_name: str, value: Any) -> ColumnOperators:
    return {
        'exact': ops.__eq__(column, value),
        'gt': ops.__gt__(column, value),
    }.get(op_name)


def create_object_filters(model: Type[IEntityModel], path: str, filters: List[Dict], joins: JoinsType, *_) \
        -> List[ColumnOperators]:
    result_filters = []
    for filter_ in filters:
        for attribute, value in filter_.items():
            if is_unset(value):
                continue
            if attribute == 'AND_':
                nested_filters = create_object_filters(model, path, value, joins)
                result_filters.append(and_(*nested_filters))
            elif attribute == 'OR_':
                nested_filters = create_object_filters(model, path, value, joins)
                result_filters.append(or_(*nested_filters))
            elif isinstance(value, list):
                # Nested filter
                result_filters.extend(_apply_nested(model, path, value, create_object_filters, attribute, joins))
            else:
                for operation, filter_value in value.items():
                    if is_unset(filter_value):
                        continue
                    else:
                        result_filters.append(create_filter_op(getattr(model, attribute), operation, filter_value))
    return result_filters


def list_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: QueryMany,
          selection: Dict[str, Dict]):
    joins: JoinsType = {'': (model, model)}

    eager_options = create_selection_joins(model, '', selection, joins)

    raw_ordering = [dataclasses.asdict(o) for o in getattr(data, 'ordering', [])]
    ordering = add_default_ordering(model, raw_ordering)
    ordering = cleanup_ordering(ordering)
    ordering = create_ordering(model, '', ordering, joins)

    raw_filter = [dataclasses.asdict(f) for f in getattr(data, 'filters', [])]
    filters = create_object_filters(model, '', raw_filter, joins)

    expression = select(model, *[j[0] for j in joins.values()]) \
        .select_from(*[j[1] for j in joins.values()]) \
        .filter(*filters) \
        .order_by(*ordering)
    if eager_options is not None:
        expression = expression.options(eager_options)

    if not is_unset(getattr(data, 'page_size', UNSET)):
        expression = expression.limit(data.page_size)
        if not is_unset(getattr(data, 'page_number', UNSET)):
            expression = expression.offset((data.page_number - 1) * data.page_size)

    return session.execute(expression).unique().scalars().all()
