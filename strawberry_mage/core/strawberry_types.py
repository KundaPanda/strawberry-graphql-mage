import enum
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from functools import cached_property
from typing import Callable, List, Optional, Type
from uuid import UUID

import strawberry
from strawberry import ID
from strawberry.arguments import UNSET

ROOT_NS = "strawberry_mage.core.types_generated"


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
    query_one_input: "QueryOne"
    query_many_input: "QueryMany"
    create_one_input: EntityType
    update_one_input: EntityType


@dataclass
class StrawberryModelType:
    entity: Type[EntityType]
    base_entity: Type[EntityType]
    filter: Type["ObjectFilter"]
    ordering: Type["ObjectOrdering"]
    input_types: Optional[StrawberryModelInputTypes] = None
    query_one: Optional[Callable] = None
    query_many: Optional[Callable] = None
    create_one: Optional[Callable] = None
    create_many: Optional[Callable] = None
    update_one: Optional[Callable] = None
    update_many: Optional[Callable] = None
    delete_one: Optional[Callable] = None
    delete_many: Optional[Callable] = None

    @cached_property
    def graphql_input_types(self):
        return self.input_types.__annotations__


@dataclass
class ObjectFilter:
    AND_: Optional[List[Optional["ObjectFilter"]]]
    OR_: Optional[List[Optional["ObjectFilter"]]]


@dataclass
class ScalarFilter:
    NOT_: Optional[bool] = False


@strawberry.input
class IntegerFilter(ScalarFilter):
    exact: Optional[int] = UNSET
    lt: Optional[int] = UNSET
    lte: Optional[int] = UNSET
    gt: Optional[int] = UNSET
    gte: Optional[int] = UNSET
    in_: Optional[List[int]] = UNSET


@strawberry.input
class FloatFilter(ScalarFilter):
    exact: Optional[float] = UNSET
    lt: Optional[float] = UNSET
    lte: Optional[float] = UNSET
    gt: Optional[float] = UNSET
    gte: Optional[float] = UNSET
    in_: Optional[List[float]] = UNSET


@strawberry.input
class NumericFilter(ScalarFilter):
    exact: Optional[Decimal] = UNSET
    lt: Optional[Decimal] = UNSET
    lte: Optional[Decimal] = UNSET
    gt: Optional[Decimal] = UNSET
    gte: Optional[Decimal] = UNSET
    in_: Optional[List[Decimal]] = UNSET


@strawberry.input
class BooleanFilter(ScalarFilter):
    exact: Optional[bool] = UNSET


@strawberry.input
class StringFilter(ScalarFilter):
    exact: Optional[str] = UNSET
    iexact: Optional[str] = UNSET
    contains: Optional[str] = UNSET
    icontains: Optional[str] = UNSET
    like: Optional[str] = UNSET
    ilike: Optional[str] = UNSET
    in_: Optional[List[str]] = UNSET


@strawberry.input
class BytesFilter(ScalarFilter):
    exact: Optional[bytes] = UNSET
    contains: Optional[bytes] = UNSET
    in_: Optional[List[bytes]] = UNSET


@strawberry.input
class DateTimeFilter(ScalarFilter):
    exact: Optional[datetime] = UNSET
    lt: Optional[datetime] = UNSET
    lte: Optional[datetime] = UNSET
    gt: Optional[datetime] = UNSET
    gte: Optional[datetime] = UNSET
    in_: Optional[List[datetime]] = UNSET


@strawberry.input
class DateFilter(ScalarFilter):
    exact: Optional[date] = UNSET
    lt: Optional[date] = UNSET
    lte: Optional[date] = UNSET
    gt: Optional[date] = UNSET
    gte: Optional[date] = UNSET
    in_: Optional[List[date]] = UNSET


@strawberry.input
class TimeFilter(ScalarFilter):
    exact: Optional[time] = UNSET
    lt: Optional[time] = UNSET
    lte: Optional[time] = UNSET
    gt: Optional[time] = UNSET
    gte: Optional[time] = UNSET
    in_: Optional[List[time]] = UNSET


@dataclass
class ObjectOrdering:
    pass


@strawberry.enum
class OrderingDirection(enum.Enum):
    ASC = "ASC"
    DESC = "DESC"


@strawberry.input
class ScalarOrdering:
    direction: OrderingDirection = OrderingDirection.ASC


@dataclass
class QueryOne:
    primary_key_: PrimaryKeyInput


@strawberry.input
class QueryMany:
    ordering: Optional[List[Optional[ObjectOrdering]]] = UNSET
    filters: Optional[List[Optional[ObjectFilter]]] = UNSET
    page_size: Optional[int] = 30
    page_number: Optional[int] = 1


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
    bytes: BytesFilter,
}