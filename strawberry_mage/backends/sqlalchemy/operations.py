"""SQLAlchemy operations for resolving graphql queries."""
import dataclasses
from enum import Enum
from functools import partial
from inspect import isclass, iscoroutinefunction
from math import ceil
from typing import Any, Callable, Dict, List, Tuple, Type, Union, cast

from sqlalchemy import Table, and_, delete, inspect, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, RelationshipProperty, contains_eager, selectinload
from sqlalchemy.orm.base import MANYTOMANY
from sqlalchemy.orm.util import AliasedClass, with_polymorphic
from sqlalchemy.sql import ColumnElement, Join
from sqlalchemy.sql.elements import BooleanClauseList, ColumnClause
from sqlalchemy.sql.expression import case, desc, func, nulls_last
from sqlalchemy.sql.functions import count
from sqlalchemy.sql.operators import ColumnOperators as ColOps
from strawberry import UNSET

from strawberry_mage.backends.sqlalchemy.models import SQLAlchemyModel
from strawberry_mage.core.strawberry_types import (
    DeleteResult,
    OrderingDirection,
    PrimaryKeyField,
    QueryMany,
)
from strawberry_mage.core.type_creator import strip_defer_typename
from strawberry_mage.core.types import IEntityModel, IsDataclass

SelectablesType = Dict[str, Union[Join, Type[SQLAlchemyModel], AliasedClass]]


def _build_pk_query(
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    selectable: Union[Table, Type[SQLAlchemyModel], AliasedClass],
    data: Any,
):
    primary_key = model.get_primary_key()
    attribute_getter = data.get if isinstance(data, dict) else partial(getattr, data)
    column_getter = (
        partial(getattr, selectable)
        if (isclass(selectable) and (issubclass(selectable, IEntityModel) or issubclass(selectable, SQLAlchemyModel)))
        or isinstance(selectable, AliasedClass)
        else partial(getattr, cast(Table, selectable).c)
    )
    conditions = [column_getter(key) == attribute_getter(key) for key in primary_key]
    return and_(*conditions)


def _build_multiple_pk_query(model: Type[Union[SQLAlchemyModel, IEntityModel]], selectable, data: List[Any]):
    if not data:
        return None
    return or_(
        _build_pk_query(
            model,
            selectable,
            {k: getattr(entry.primary_key_, k) for k in model.get_primary_key()},
        )
        for entry in data
    )


def _get_model_pk_values(model: Type[Union[SQLAlchemyModel, IEntityModel]], data: IsDataclass):
    return tuple(getattr(data, key) for key in model.get_primary_key())


def _get_dict_pk_values(model: Type[Union[SQLAlchemyModel, IEntityModel]], data: Dict[str, Any]):
    return tuple(data.get(key) for key in model.get_primary_key())


def _create_pk_class(data: Dict[str, Any]):
    return type("StubInput", (), {"primary_key_": type("StubPk", (), data)})()


async def _set_instance_attrs(
    model: Type[Union[SQLAlchemyModel, IEntityModel]],
    instance: object,
    input_object: IsDataclass,
    session: AsyncSession,
):
    for prop in input_object.__dataclass_fields__:
        value = getattr(input_object, prop)
        if value is UNSET or prop == "primary_key_":
            continue
        prop_type = strip_defer_typename(model.get_attribute_type(prop))
        if isinstance(prop_type, str):
            related_model = model.get_schema_manager().get_model_for_name(prop_type)
            if related_model is None:
                raise Exception(f"Unable to resolve related type for {prop_type} on {model}")
            if isinstance(value, list):
                expr = select(related_model).where(_build_multiple_pk_query(related_model, related_model, value))
                setattr(instance, prop, (await session.execute(expr)).scalars().all())
            elif isinstance(value, Enum):
                setattr(instance, prop, value.name)
            else:
                setattr(
                    instance,
                    prop,
                    await session.get(related_model, dataclasses.asdict(value.primary_key_)),
                )
        else:
            setattr(instance, prop, value)


def _create_join(
    selectables: SelectablesType,
    related_model: Union[Type[IEntityModel], Type[SQLAlchemyModel], AliasedClass],
    property_: InstrumentedAttribute,
    nested_path: str,
    select_from: Union[Join, Type[SQLAlchemyModel], AliasedClass],
) -> ColumnClause:
    expression = property_.expression
    if isinstance(expression, BooleanClauseList):
        if property_.property.direction == MANYTOMANY and len(expression.clauses) == 2:
            m2m_path = f"{nested_path}._m2m"
            if m2m_path not in selectables:
                selectables[m2m_path] = expression.clauses[0].right.table
                selectables["__selection__"] = selectables["__selection__"].join(
                    selectables[m2m_path], expression.clauses[0], isouter=True
                )
            # noinspection PyTypeChecker
            join_expression: ColumnClause = getattr(
                selectables[m2m_path].c, expression.clauses[1].right.key
            ) == getattr(inspect(related_model).local_table.c, expression.clauses[1].left.key)
            selectables["__selection__"] = selectables["__selection__"].join(
                related_model, join_expression, isouter=True
            )
            return join_expression
        else:
            raise NotImplementedError("Relationships on multiple clauses are not yet implemented")
    else:
        # noinspection PyTypeChecker
        join_expression: ColumnClause = (
            expression.left == getattr(related_model, expression.right.key)
            if inspect(select_from).local_table == expression.left.table
            else expression.right == getattr(related_model, expression.left.key)
        )
        selectables["__selection__"] = selectables["__selection__"].join(related_model, join_expression, isouter=True)
        return join_expression


async def _apply_nested(
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    path: str,
    input_: Any,
    op: Callable,
    attribute: str,
    selectables: SelectablesType,
    eager_options: Any = None,
    **kwargs,
):
    """
    Recursively call an operation whilst updating the selectables.

    :param model: model used for operation
    :param path: current path in operation
    :param input_: the input
    :param op: operation to execute
    :param attribute: attribute which is used on the model to retrieve the relationship property
    :param selectables: selectables which will be modified and used
    :param eager_options: eager options for select statement
    :return: what op returns
    """
    nested_path = f"{path}.{attribute}"
    select_from = selectables[path]
    attr_getter: Callable[[str], RelationshipProperty] = (
        partial(getattr, select_from)
        if (isinstance(select_from, (AliasedClass, SQLAlchemyModel)))
        else partial(getattr, select_from.c)
    )
    prop = attr_getter(attribute)
    if nested_path not in selectables:
        related_type_name = strip_defer_typename(model.get_attribute_type(attribute))
        related_model_raw = model.get_schema_manager().get_model_for_name(related_type_name)
        related_model = with_polymorphic(related_model_raw, "*", aliased=True)
        selectables[nested_path] = related_model
        _create_join(selectables, related_model, prop, nested_path, select_from)
    eager_options = (
        contains_eager(prop.of_type(selectables[nested_path]))
        if eager_options is None
        else eager_options.contains_eager(prop.of_type(selectables[nested_path]))
    )
    if iscoroutinefunction(op):
        return await op(selectables[nested_path], nested_path, input_, selectables, eager_options, **kwargs)
    return op(selectables[nested_path], nested_path, input_, selectables, eager_options, **kwargs)


async def create_(
    session: AsyncSession,
    model: Type[Union[SQLAlchemyModel, IEntityModel]],
    data: List[Any],
    selection: Dict[str, Dict],
):
    """
    Resolve the create-many operation.

    :param session: sqlalchemy session
    :param model: which model to use
    :param data: graphql input
    :param selection: selected fields
    :return: list of created models
    """
    # TODO: create related models as well maybe?
    models = []
    for create_type in data:
        instance = model()
        await _set_instance_attrs(model, instance, create_type, session)
        models.append(instance)
    session.add_all(models)
    await session.flush(models)
    primary_keys = [{key: getattr(instance, key) for key in model.get_primary_key()} for instance in models]
    await session.commit()

    data = [_create_pk_class(instance) for instance in primary_keys]
    polymorphic_model = with_polymorphic(model, "*", aliased=True)
    model_query = select(polymorphic_model)
    selectables: SelectablesType = {"": polymorphic_model, "__selection__": model_query}
    pk_filter = _build_multiple_pk_query(model, polymorphic_model, data)

    eager_options = await create_selection_joins(model, "", selection, selectables)
    ordering = await create_ordering(model, "", add_default_ordering(model, []), selectables)

    expression = cast(Type[SQLAlchemyModel], selectables["__selection__"]).filter(pk_filter).order_by(*ordering)
    if eager_options != (None,):
        expression = expression.options(*eager_options)
    return (await session.execute(expression)).unique().scalars().all()


async def update_(
    session: AsyncSession,
    model: Type[Union[SQLAlchemyModel, IEntityModel]],
    data: List[Any],
    selection: Dict[str, Dict],
):
    """
    Resolve the update-many operation.

    :param session: sqlalchemy session
    :param model: which model to use
    :param data: graphql input
    :param selection: selected fields
    :return: list of update model instances
    """
    pk_filter = _build_multiple_pk_query(model, model, data)
    instances = (
        (
            await session.execute(
                select(model)
                .options(*[selectinload(a.key) for a in inspect(model).attrs if isinstance(a, RelationshipProperty)])
                .where(pk_filter)
            )
        )
        .scalars()
        .all()
    )
    entities = {_get_model_pk_values(model, en): en for en in instances}
    if len(entities) != len(data):
        return [None]
    for entry in data:
        model_instance = entities[_get_model_pk_values(model, entry.primary_key_)]
        await _set_instance_attrs(model, model_instance, entry, session)
    session.add_all(entities.values())
    await session.commit()

    polymorphic_model = with_polymorphic(model, "*", aliased=True)
    model_query = select(polymorphic_model)
    selectables: SelectablesType = {"": polymorphic_model, "__selection__": model_query}
    pk_filter = _build_multiple_pk_query(model, polymorphic_model, data)

    eager_options = await create_selection_joins(model, "", selection, selectables)
    ordering = await create_ordering(model, "", add_default_ordering(model, []), selectables)

    expression = cast(Type[SQLAlchemyModel], selectables["__selection__"]).filter(pk_filter).order_by(*ordering)
    if eager_options != (None,):
        expression = expression.options(*eager_options)
    return (await session.execute(expression)).unique().scalars().all()


async def delete_(
    session: AsyncSession,
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    data: List[Any],
):
    """
    Resolve the delete-many operation.

    :param session: sqlalchemy session
    :param model: which model to use
    :param data: graphql input
    :return: number of affected rows
    """
    pk_q = _build_multiple_pk_query(model, model, data)
    statement = delete(model).where(pk_q)
    result = await session.execute(statement)
    await session.commit()
    return DeleteResult(affected_rows=result.rowcount)


async def retrieve_(
    session: AsyncSession,
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    data: PrimaryKeyField,
    selection: Dict[str, Dict],
):
    """
    Resolve the query-one operation.

    :param session: sqlalchemy session
    :param model: which model to use
    :param data: graphql input
    :param selection: selected fields
    :return: model instance
    """
    polymorphic_model = with_polymorphic(model, "*", aliased=True)
    model_query = select(polymorphic_model)
    selectables: SelectablesType = {"": polymorphic_model, "__selection__": model_query}
    pk_filter = _build_pk_query(model, polymorphic_model, data.primary_key_)

    eager_options = await create_selection_joins(model, "", selection, selectables)

    expression = cast(Type[SQLAlchemyModel], selectables["__selection__"]).filter(pk_filter)
    if eager_options != (None,):
        expression = expression.options(*eager_options)
    return (await session.execute(expression)).unique().scalar()


def add_default_ordering(model: Type[Union[SQLAlchemyModel, IEntityModel]], ordering: List[Dict]):
    """
    Add a default ordering PRIMARY_KEY: DESC to ordering.

    :param model: model used for query
    :param ordering: ordering input
    :return: resulting ordering with default at the end
    """
    return ordering + [{k: OrderingDirection.DESC for k in model.get_primary_key()}]


def cleanup_ordering(ordering: List[Dict]):
    """
    Remove unset values from ordering input.

    :param ordering: ordering input
    :return: modified ordering without unset fields
    """
    result_ordering = []
    for ordering_entry in ordering:
        for field, value in ordering_entry.items():
            if isinstance(value, list):
                result_ordering.append({field: cleanup_ordering(value)})
            elif value is not UNSET:
                result_ordering.append({field: value})
    return result_ordering


async def create_selection_joins(
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    path: str,
    selection: Dict[Union[str, Type], Dict],
    selectables: SelectablesType,
    eager_options: Any = None,
) -> Tuple:
    """
    Create sqlalchemy joins for loading attributes based on graphql field selections.

    :param model: model used for query
    :param path: current path in ordering building
    :param selection: input from graphql field selections
    :param selectables: selectables used for creating ordering expressions
    :param eager_options: sqlalchemy eager options used for recursive calls
    :return: tuple of all sqlalchemy eager options when using select
    """
    eager_options_created = []
    for attr, sub_selection in selection.items():
        if isclass(attr) and issubclass(attr, SQLAlchemyModel):
            sub_path = f"{path}-{attr.__name__}"
            if not hasattr(model, attr.__name__):
                continue
            selectables[sub_path] = getattr(model, attr.__name__)
            eager_options_created.extend(
                await create_selection_joins(
                    getattr(model, attr.__name__),
                    sub_path,
                    sub_selection,
                    selectables,
                    eager_options,
                )
            )
        elif isinstance(attr, str):
            eager_options_created.extend(
                await _apply_nested(
                    model,
                    path,
                    sub_selection,
                    create_selection_joins,
                    attr,
                    selectables,
                    eager_options,
                )
            )
    return tuple(eager_options_created) if eager_options_created else (eager_options,)


async def create_ordering(
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    path: str,
    ordering: List[Dict],
    selectables: SelectablesType,
    *_,
) -> List[ColumnElement]:
    """
    Create sqlalchemy expressions for ordering.

    :param model: model used for query
    :param path: current path in ordering building
    :param ordering: input from graphql query
    :param selectables: selectables used for creating ordering expressions
    :param _:
    :return: list of column expressions, selectables are modified based on needs
    """
    result_ordering = []
    for entry in ordering:
        for attribute, value in entry.items():
            if value is UNSET:
                continue
            if isinstance(value, OrderingDirection):
                select_from = selectables[path]
                col = (
                    getattr(select_from, attribute)
                    if (isinstance(select_from, AliasedClass) or isinstance(select_from, SQLAlchemyModel))
                    else getattr(select_from.c, attribute)
                )
                result_ordering.append(nulls_last(desc(col) if value == OrderingDirection.DESC else col))
            elif isinstance(value, dict) and not any(isinstance(v, OrderingDirection) for v in value.values()):
                # Enum ordering by values
                select_from = selectables[path]
                col = (
                    getattr(select_from, attribute)
                    if (isinstance(select_from, AliasedClass) or isinstance(select_from, SQLAlchemyModel))
                    else getattr(select_from.c, attribute)
                )
                result_ordering.append(
                    nulls_last(case(value=col, whens={k: (v if v is not UNSET else 0) for k, v in value.items()}))
                )
            else:
                result_ordering.extend(
                    await _apply_nested(model, path, [value], create_ordering, attribute, selectables)
                )
    return result_ordering


FILTER_OPS = {
    "exact": ColOps.__eq__,
    "iexact": lambda c, v: ColOps.__eq__(func.lower(c), func.lower(v)),
    "contains": ColOps.contains,
    "icontains": lambda c, v: ColOps.contains(func.lower(c), func.lower(v)),
    "like": ColOps.like,
    "ilike": ColOps.ilike,
    "gt": ColOps.__gt__,
    "gte": ColOps.__ge__,
    "lt": ColOps.__lt__,
    "lte": ColOps.__le__,
    "in_": ColOps.in_,
}


def create_filter_op(column: Any, op_name: str, value: Any, negate: bool) -> ColOps:
    """
    Create a sqlalchemy filter operation.

    :param column: column to filter
    :param op_name: name of the operation from the graphql query
    :param value: value to use for filtering
    :param negate: negate the filter
    :return: Column operation
    """
    operation = FILTER_OPS[op_name](column, value)
    if negate:
        operation = not_(operation)
    return operation


def get_attr(selectables, path, attribute):
    """
    Get attribute from selectables given path and attribute name.

    :param selectables: selectables
    :param path: current path in resolution
    :param attribute: attribute name
    :return: attribute
    """
    select_from = selectables[path]
    return (
        getattr(select_from, attribute)
        if (isinstance(select_from, AliasedClass) or isinstance(select_from, SQLAlchemyModel))
        else getattr(select_from.c, attribute)
    )


async def create_object_filters(
    model: Union[Type[IEntityModel], Type[SQLAlchemyModel]],
    path: str,
    filters: List[Dict],
    selectables: SelectablesType,
    *_,
) -> List[ColOps]:
    """
    Create object filters for a model based on filters input.

    modifies selectables based on needs
    :param model: model which is used for filtering against
    :param path: current path in the filter building
    :param filters: filters input
    :param selectables: selectables used for attribute resolution
    :param _:
    :return: list of filtering operations
    """
    result_filters = []
    for filter_ in filters:
        for attribute, value in filter_.items():
            if value is UNSET:
                continue
            if attribute == "AND_":
                nested_filters = await create_object_filters(model, path, value, selectables)
                result_filters.append(and_(*nested_filters))
            elif attribute == "OR_":
                nested_filters = await create_object_filters(model, path, value, selectables)
                result_filters.append(or_(*nested_filters))
            elif isinstance(value, dict):
                if "AND_" in value:
                    # Nested filter
                    result_filters.extend(
                        await _apply_nested(
                            model,
                            path,
                            [value],
                            create_object_filters,
                            attribute,
                            selectables,
                        )
                    )
                    # attr = get_attr(selectables, path, attribute)
                    # result_filters.append(ColOps.__ne__(attr, None))
                else:
                    negate = value.pop("NOT_", False)
                    for operation, filter_value in value.items():
                        if filter_value is UNSET:
                            continue
                        else:
                            attr = get_attr(selectables, path, attribute)
                            result_filters.append(create_filter_op(attr, operation, filter_value, negate))
    return result_filters


async def list_(
    session: AsyncSession,
    model: Type[Union[SQLAlchemyModel, IEntityModel]],
    data: QueryMany,
    selection: Dict[str, Dict],
):
    """
    Resolve the query-many operation.

    :param session: sqlalchemy session
    :param model: which model to list
    :param data: graphql input
    :param selection: selected fields
    :return: QueryManyResult
    """
    polymorphic_model = with_polymorphic(model, "*", aliased=True)
    model_query = select(polymorphic_model, count().over().label("total_results_count"))  # type: ignore
    if data is not UNSET and data.page_size is not UNSET and data.page_size:
        model_query = model_query.limit(data.page_size)
        if data.page_number is not UNSET and data.page_number:
            model_query = model_query.offset((data.page_number - 1) * data.page_size)
    # TODO: implement limit+offset for nested selects
    selectables: SelectablesType = {"": polymorphic_model, "__selection__": model_query}

    eager_options = await create_selection_joins(model, "", selection, selectables)

    expression = cast(Type[SQLAlchemyModel], selectables["__selection__"])

    if eager_options != (None,):
        expression = expression.options(*eager_options)

    filters, ordering = None, None
    if data is not UNSET:
        if data.filters is not UNSET and data.filters:
            raw_filter = [dataclasses.asdict(f) for f in data.filters]
            filters = await create_object_filters(model, "", raw_filter, selectables)

        if data.ordering is not UNSET and data.ordering:
            raw_ordering = [dataclasses.asdict(o) for o in data.ordering]
            ordering = add_default_ordering(model, raw_ordering)
            ordering = cleanup_ordering(ordering)
            ordering = await create_ordering(model, "", ordering, selectables)
        else:
            ordering = await create_ordering(model, "", add_default_ordering(model, []), selectables)

        # Expression needs to be created again, selectables may have been modified in filters / ordering builder
        expression = cast(Type[SQLAlchemyModel], selectables["__selection__"])

        if eager_options != (None,):
            expression = expression.options(*eager_options)

        if filters:
            expression = expression.filter(*filters)

        expression = expression.order_by(*ordering)

    results_task = session.execute(expression)
    results = (await results_task).unique().all()
    total_results: int = results[0][1] if len(results) > 0 else 0  # TODO: this returns total rowcount, not object count
    return model.get_strawberry_type().query_many_output(
        results=[r[0] for r in results],
        page=data.page_number if (data is not UNSET and data.page_number) else 1,
        total_pages=ceil(total_results / data.page_size) if (data is not UNSET and data.page_size) else 1,
        total_results_count=total_results,
        results_count=len(results),
    )
