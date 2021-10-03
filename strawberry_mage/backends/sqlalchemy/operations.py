import dataclasses
from enum import Enum
from functools import partial
from inspect import isclass
from typing import List, Type, Any, Union, Dict, Callable, Tuple

from sqlalchemy import select, delete, and_, or_, Table, inspect, not_
from sqlalchemy.orm import Session, aliased, contains_eager
from sqlalchemy.orm.util import AliasedClass, with_polymorphic
from sqlalchemy.sql import Join, ColumnElement
from sqlalchemy.sql.expression import desc, func
from sqlalchemy.sql.operators import ColumnOperators as ColOps
from strawberry.arguments import is_unset, UNSET

from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.strawberry_types import DeleteResult, OrderingDirection, QueryMany, \
    PrimaryKeyField
from strawberry_mage.core.type_creator import strip_typename
from strawberry_mage.core.types import IEntityModel

SelectablesType = Dict[str, Union[Join, Type[_SQLAlchemyModel]]]


def _build_pk_query(model: Type[_SQLAlchemyModel], selectable: Union[Table, Type[_SQLAlchemyModel]], data: Any):
    pk = model.get_primary_key()
    attribute_getter = data.get if isinstance(data, dict) else partial(getattr, data)
    column_getter = partial(getattr, selectable) \
        if isclass(selectable) and issubclass(selectable, IEntityModel) \
        else partial(getattr, selectable.c)
    return and_(*(column_getter(key) == attribute_getter(key) for key in pk))


def _build_multiple_pk_query(model: Type[Union[_SQLAlchemyModel, IEntityModel]], selectable, data: List[Any]):
    return or_(
        _build_pk_query(model, selectable, {k: getattr(entry.primary_key_, k) for k in model.get_primary_key()})
        for entry in data)


def _get_model_pk_values(model: Type[Union[_SQLAlchemyModel, IEntityModel]], data: dataclasses.dataclass):
    return tuple(getattr(data, key) for key in model.get_primary_key())


def _get_dict_pk_values(model: Type[Union[_SQLAlchemyModel, IEntityModel]], data: Dict[str, Any]):
    return tuple(data.get(key) for key in model.get_primary_key())


def _create_pk_class(data: Dict[str, Any]):
    return type('StubInput', (), {'primary_key_': type('StubPk', (), data)})()


def _set_instance_attrs(model: Type[Union[_SQLAlchemyModel, IEntityModel]], instance: object,
                        input_object: dataclasses.dataclass, session: Session):
    for prop in input_object.__dataclass_fields__:
        value = getattr(input_object, prop)
        if is_unset(value) or prop == 'primary_key_':
            continue
        prop_type = strip_typename(model.get_attribute_type(prop))
        if isinstance(prop_type, str):
            related_model = model.get_schema_manager().get_model_for_name(prop_type)
            if isinstance(value, list):
                expr = select(related_model).where(_build_multiple_pk_query(related_model, related_model, value))
                setattr(instance, prop, session.execute(expr).scalars().all())
            elif isinstance(value, Enum):
                setattr(instance, prop, value.name)
            else:
                setattr(instance, prop, session.query(related_model).get(dataclasses.asdict(value.primary_key_)))
        else:
            setattr(instance, prop, value)


def _apply_nested(model: Type[_SQLAlchemyModel], path: str, input_: Any, op: Callable, attribute: str,
                  selectables: SelectablesType, eager_options: Any = None):
    nested_path = f'{path}.{attribute}'
    select_from = selectables[path]
    attr_getter = partial(getattr, select_from) \
        if (isinstance(select_from, AliasedClass) or isinstance(select_from, _SQLAlchemyModel)) \
        else partial(getattr, select_from.c)
    prop = attr_getter(attribute)
    if nested_path not in selectables:
        related_type_name = strip_typename(model.get_attribute_type(attribute))
        related_model_raw = model.get_schema_manager().get_model_for_name(related_type_name)
        related_model = with_polymorphic(related_model_raw, '*', aliased=True)
        selectables[nested_path] = related_model
        ex = prop.expression
        join_expression = ex.left == getattr(related_model, ex.right.key) \
            if inspect(select_from).local_table == ex.left.table \
            else ex.right == getattr(related_model, ex.left.key)
        selectables['__joins__'] = selectables['__joins__'].join(related_model, join_expression, isouter=True)
    eager_options = contains_eager(prop.of_type(selectables[nested_path])) \
        if eager_options is None \
        else eager_options.contains_eager(prop.of_type(selectables[nested_path]))
    return op(selectables[nested_path], nested_path, input_, selectables, eager_options)


def create_(session: Session, model: Type[Union[_SQLAlchemyModel, IEntityModel]], data: List[Any],
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

    data = [_create_pk_class(instance) for instance in primary_keys]
    model_query = select(with_polymorphic(model, '*')).subquery()
    selectables: SelectablesType = {'': aliased(model, model_query), '__joins__': model_query}
    pk_filter = _build_multiple_pk_query(model, model_query, data)

    eager_options = create_selection_joins(model, '', selection, selectables)
    ordering = create_ordering(model, '', add_default_ordering(model, []), selectables)

    expression = select(selectables[''], selectables['__joins__']) \
        .select_from(selectables['__joins__']) \
        .filter(pk_filter) \
        .order_by(*ordering)
    if eager_options != (None,):
        expression = expression.options(*eager_options)
    return session.execute(expression).unique().scalars().all()


def update_(session: Session, model: Type[_SQLAlchemyModel], data: List[Any],
            selection: Dict[str, Dict]):
    pk_filter = _build_multiple_pk_query(model, model, data)
    entities = {_get_model_pk_values(model, en): en
                for en in session.execute(select(model).where(pk_filter)).scalars().all()}
    if len(entities) != len(data):
        return [None]
    for entry in data:
        model_instance = entities[_get_model_pk_values(model, entry.primary_key_)]
        _set_instance_attrs(model, model_instance, entry, session)
    session.add_all(entities.values())
    session.commit()

    model_query = select(with_polymorphic(model, '*')).subquery()
    selectables: SelectablesType = {'': aliased(model, model_query), '__joins__': model_query}
    pk_filter = _build_multiple_pk_query(model, model_query, data)

    eager_options = create_selection_joins(model, '', selection, selectables)
    ordering = create_ordering(model, '', add_default_ordering(model, []), selectables)

    expression = select(selectables[''], selectables['__joins__']) \
        .select_from(selectables['__joins__']) \
        .filter(pk_filter) \
        .order_by(*ordering)
    if eager_options != (None,):
        expression = expression.options(*eager_options)
    return session.execute(expression).unique().scalars().all()


def delete_(session: Session, model: Type[_SQLAlchemyModel], data: List[Any]):
    pk_q = _build_multiple_pk_query(model, model, data)
    statement = delete(model).where(pk_q)
    r = session.execute(statement)
    session.commit()
    return DeleteResult(affected_rows=r.rowcount)


def retrieve_(session: Session, model: Type[_SQLAlchemyModel],
              data: Union[PrimaryKeyField, dataclasses.dataclass], selection: Dict[str, Dict]):
    model_query = select(with_polymorphic(model, '*')).subquery()
    selectables: SelectablesType = {'': aliased(model, model_query), '__joins__': model_query}
    pk_filter = _build_pk_query(model, model_query, data.primary_key_)

    eager_options = create_selection_joins(model, '', selection, selectables)

    expression = select(selectables[''], selectables['__joins__']) \
        .select_from(selectables['__joins__']) \
        .filter(pk_filter)
    if eager_options != (None,):
        expression = expression.options(*eager_options)
    return session.execute(expression).unique().scalar()


def add_default_ordering(model: Type[_SQLAlchemyModel], ordering: List[Dict]):
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


def create_selection_joins(model: Type[_SQLAlchemyModel], path: str, selection: Dict[Union[str, Type], Dict],
                           selectables: SelectablesType, eager_options: Any = None) -> Tuple:
    eager_options_created = []
    for attr, sub_selection in selection.items():
        if isclass(attr) and issubclass(attr, _SQLAlchemyModel):
            sub_path = f'{path}-{attr.__name__}'
            selectables[sub_path] = getattr(model, attr.__name__)
            eager_options_created.extend(
                create_selection_joins(getattr(model, attr.__name__), sub_path, sub_selection,
                                       selectables, eager_options))
        else:
            eager_options_created.extend(
                _apply_nested(model, path, sub_selection, create_selection_joins, attr, selectables, eager_options))
    return tuple(eager_options_created) if eager_options_created else (eager_options,)


def create_ordering(model: Type[_SQLAlchemyModel], path: str, ordering: List[Dict], selectables: SelectablesType, *_) \
        -> List[ColumnElement]:
    result_ordering = []
    for entry in ordering:
        for attribute, value in entry.items():
            if isinstance(value, OrderingDirection):
                select_from = selectables[path]
                col = getattr(select_from, attribute) \
                    if (isinstance(select_from, AliasedClass) or isinstance(select_from, _SQLAlchemyModel)) \
                    else getattr(select_from.c, attribute)
                result_ordering.append(desc(col) if value == OrderingDirection.DESC else col)
            else:
                result_ordering.extend(_apply_nested(model, path, value, create_ordering, attribute, selectables))
    return result_ordering


def create_filter_op(column: Any, op_name: str, value: Any, negate: bool) -> ColOps:
    op = {
        'exact': ColOps.__eq__(column, value),
        'iexact': ColOps.__eq__(func.lower(column), func.lower(value)),
        'contains': ColOps.contains(column, value),
        'icontains': ColOps.contains(func.lower(column), func.lower(value)),
        'like': ColOps.like(column, value),
        'ilike': ColOps.ilike(column, value),
        'gt': ColOps.__gt__(column, value),
        'gte': ColOps.__ge__(column, value),
        'lt': ColOps.__lt__(column, value),
        'lte': ColOps.__le__(column, value),
    }.get(op_name)
    if negate:
        op = not_(op)
    return op


def create_object_filters(model: Type[_SQLAlchemyModel], path: str, filters: List[Dict], selectables: SelectablesType,
                          *_) \
        -> List[ColOps]:
    result_filters = []
    for filter_ in filters:
        for attribute, value in filter_.items():
            if is_unset(value):
                continue
            if attribute == 'AND_':
                nested_filters = create_object_filters(model, path, value, selectables)
                result_filters.append(and_(*nested_filters))
            elif attribute == 'OR_':
                nested_filters = create_object_filters(model, path, value, selectables)
                result_filters.append(or_(*nested_filters))
            elif isinstance(value, list):
                # Nested filter
                result_filters.extend(_apply_nested(model, path, value, create_object_filters, attribute, selectables))
            else:
                negate = value['NOT_']
                del value['NOT_']
                for operation, filter_value in value.items():
                    if is_unset(filter_value):
                        continue
                    else:
                        select_from = selectables[path]
                        col = getattr(select_from, attribute) \
                            if (isinstance(select_from, AliasedClass) or isinstance(select_from, _SQLAlchemyModel)) \
                            else getattr(select_from.c, attribute)
                        result_filters.append(create_filter_op(col, operation, filter_value, negate))
    return result_filters


def list_(session: Session, model: Type[Union[_SQLAlchemyModel, IEntityModel]], data: QueryMany,
          selection: Dict[str, Dict]):
    model_query = select(with_polymorphic(model, '*')).subquery()
    selectables: SelectablesType = {'': aliased(model, model_query), '__joins__': model_query}

    eager_options = create_selection_joins(model, '', selection, selectables)

    expression = select(selectables[''], selectables['__joins__']) \
        .select_from(selectables['__joins__'])

    if eager_options != (None,):
        expression = expression.options(*eager_options)

    if not is_unset(data):
        if not is_unset(data.filters):
            raw_filter = [dataclasses.asdict(f) for f in data.filters]
            filters = create_object_filters(model, '', raw_filter, selectables)
            expression = expression.filter(*filters)

        if not is_unset(data.ordering):
            raw_ordering = [dataclasses.asdict(o) for o in data.ordering]
            ordering = add_default_ordering(model, raw_ordering)
            ordering = cleanup_ordering(ordering)
            ordering = create_ordering(model, '', ordering, selectables)
            expression = expression.order_by(*ordering)

        if not is_unset(data.page_size):
            expression = expression.limit(data.page_size)
            if not is_unset(data.page_number):
                expression = expression.offset((data.page_number - 1) * data.page_size)

    return session.execute(expression).unique().scalars().all()
