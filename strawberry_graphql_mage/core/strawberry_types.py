import enum
from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from functools import cached_property
from typing import List, Optional as O, Callable, Type
from uuid import UUID

import strawberry
from strawberry import ID
from strawberry.arguments import UNSET

ROOT_NS = 'strawberry_graphql_mage.core.types_generated'


@dataclass
class EntityType:
    pass


@strawberry.type
class DeleteResult:
    affected_rows: int


@dataclass
class PrimaryKeyInput:
    pass


@dataclass
class PrimaryKeyField:
    primary_key_: PrimaryKeyInput


@dataclass
class StrawberryModelInputTypes:
    primary_key_input: PrimaryKeyInput
    primary_key_field: PrimaryKeyField
    query_one_input: 'QueryOne'
    query_many_input: 'QueryMany'
    create_one_input: EntityType
    update_one_input: EntityType


@dataclass
class StrawberryModelType:
    entity: Type[EntityType]
    base_entity: Type[EntityType]
    filter: Type['ObjectFilter']
    ordering: Type['ObjectOrdering']
    input_types: O[StrawberryModelInputTypes] = None
    query_one: O[Callable] = None
    query_many: O[Callable] = None
    create_one: O[Callable] = None
    create_many: O[Callable] = None
    update_one: O[Callable] = None
    update_many: O[Callable] = None
    delete_one: O[Callable] = None
    delete_many: O[Callable] = None

    @cached_property
    def graphql_input_types(self):
        return self.input_types.__annotations__


@dataclass
class ObjectFilter:
    AND_: O[List[O['ObjectFilter']]]
    OR_: O[List[O['ObjectFilter']]]


@dataclass
class ScalarFilter:
    NOT_: O[bool] = False


@strawberry.input
class IntegerFilter(ScalarFilter):
    exact: O[int] = UNSET
    lt: O[int] = UNSET
    lte: O[int] = UNSET
    gt: O[int] = UNSET
    gte: O[int] = UNSET
    in_: O[List[int]] = UNSET


@strawberry.input
class FloatFilter(ScalarFilter):
    exact: O[float] = UNSET
    lt: O[float] = UNSET
    lte: O[float] = UNSET
    gt: O[float] = UNSET
    gte: O[float] = UNSET
    in_: O[List[float]] = UNSET


@strawberry.input
class NumericFilter(ScalarFilter):
    exact: O[Decimal] = UNSET
    lt: O[Decimal] = UNSET
    lte: O[Decimal] = UNSET
    gt: O[Decimal] = UNSET
    gte: O[Decimal] = UNSET
    in_: O[List[Decimal]] = UNSET


@strawberry.input
class BooleanFilter(ScalarFilter):
    exact: O[bool] = UNSET


@strawberry.input
class StringFilter(ScalarFilter):
    exact: O[str] = UNSET
    iexact: O[str] = UNSET
    contains: O[str] = UNSET
    icontains: O[str] = UNSET
    like: O[str] = UNSET
    ilike: O[str] = UNSET
    in_: O[List[str]] = UNSET


@strawberry.input
class BytesFilter(ScalarFilter):
    exact: O[bytes] = UNSET
    contains: O[bytes] = UNSET
    in_: O[List[bytes]] = UNSET


@strawberry.input
class DateTimeFilter(ScalarFilter):
    exact: O[datetime] = UNSET
    lt: O[datetime] = UNSET
    lte: O[datetime] = UNSET
    gt: O[datetime] = UNSET
    gte: O[datetime] = UNSET
    in_: O[List[datetime]] = UNSET


@strawberry.input
class DateFilter(ScalarFilter):
    exact: O[date] = UNSET
    lt: O[date] = UNSET
    lte: O[date] = UNSET
    gt: O[date] = UNSET
    gte: O[date] = UNSET
    in_: O[List[date]] = UNSET


@strawberry.input
class TimeFilter(ScalarFilter):
    exact: O[time] = UNSET
    lt: O[time] = UNSET
    lte: O[time] = UNSET
    gt: O[time] = UNSET
    gte: O[time] = UNSET
    in_: O[List[time]] = UNSET


@dataclass
class ObjectOrdering:
    pass


@strawberry.enum
class OrderingDirection(enum.Enum):
    ASC = 'ASC'
    DESC = 'DESC'


@strawberry.input
class ScalarOrdering:
    direction: OrderingDirection = OrderingDirection.ASC


@dataclass
class QueryOne:
    primary_key_: PrimaryKeyInput


@strawberry.input
class QueryMany:
    ordering: O[List[O[ObjectOrdering]]] = UNSET
    filters: O[List[O[ObjectFilter]]] = UNSET
    page_size: O[int] = 30
    page_number: O[int] = 1


SCALAR_FILTERS = {
    int: IntegerFilter,
    float: FloatFilter,
    Decimal: NumericFilter,
    str: StringFilter,
    bool: BooleanFilter,
    ID: StringFilter,
    UUID: StringFilter,
    datetime: DateTimeFilter,
    date: DateFilter,
    time: TimeFilter,
    bytes: BytesFilter
}
