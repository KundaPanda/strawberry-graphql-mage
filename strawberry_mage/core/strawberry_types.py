"""Strawberry object types."""

import enum
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from functools import cached_property
from typing import List, Optional, Type
from uuid import UUID

import strawberry
from strawberry import ID
from strawberry.arguments import UNSET
from strawberry.field import StrawberryField

ROOT_NS = "strawberry_mage.core.types_generated"


@dataclass
class EntityType:
    """An Entity."""


@strawberry.type
class DeleteResult:
    """Result of the delete operation."""

    affected_rows: int


@dataclass
class PrimaryKeyInput:
    """Data input of a primary key."""


@dataclass
class PrimaryKeyField:
    """Field for primary key input."""

    primary_key_: PrimaryKeyInput


@dataclass
class StrawberryModelInputTypes:
    """Collection of per-entity input types."""

    primary_key_input: PrimaryKeyInput
    primary_key_field: PrimaryKeyField
    query_one_input: "QueryOne"
    query_many_input: "QueryMany"
    create_one_input: EntityType
    update_one_input: EntityType


@dataclass
class StrawberryModelType:
    """All strawberry types for an EntityModel."""

    entity: Type[EntityType]
    base_entity: Type[EntityType]
    filter: Type["ObjectFilter"]
    ordering: Type["ObjectOrdering"]
    input_types: Optional[StrawberryField] = field(default=None)
    query_one: Optional[StrawberryField] = field(default=None)
    query_many: Optional[StrawberryField] = field(default=None)
    create_one: Optional[StrawberryField] = field(default=None)
    create_many: Optional[StrawberryField] = field(default=None)
    update_one: Optional[StrawberryField] = field(default=None)
    update_many: Optional[StrawberryField] = field(default=None)
    delete_one: Optional[StrawberryField] = field(default=None)
    delete_many: Optional[StrawberryField] = field(default=None)

    @cached_property
    def graphql_input_types(self):
        """
        Get input types as strawberry fields.

        :return: strawberry fields for input types
        """
        return self.input_types.__annotations__


@dataclass
class ObjectFilter:
    """Generic filter base for any object."""

    AND_: Optional[List[Optional["ObjectFilter"]]]  # pylint: disable=invalid-name
    OR_: Optional[List[Optional["ObjectFilter"]]]  # pylint: disable=invalid-name


@dataclass
class ScalarFilter:
    """Base filter for all strawberry scalar types."""

    NOT_: Optional[bool] = False  # pylint: disable=invalid-name


@strawberry.input
class IntegerFilter(ScalarFilter):
    """Filter for integer scalar fields."""

    exact: Optional[int] = UNSET
    lt: Optional[int] = UNSET
    lte: Optional[int] = UNSET
    gt: Optional[int] = UNSET
    gte: Optional[int] = UNSET
    in_: Optional[List[int]] = UNSET


@strawberry.input
class FloatFilter(ScalarFilter):
    """Filter for float scalar fields."""

    exact: Optional[float] = UNSET
    lt: Optional[float] = UNSET
    lte: Optional[float] = UNSET
    gt: Optional[float] = UNSET
    gte: Optional[float] = UNSET
    in_: Optional[List[float]] = UNSET


@strawberry.input
class NumericFilter(ScalarFilter):
    """Filter for decimal/numeric scalar fields."""

    exact: Optional[Decimal] = UNSET
    lt: Optional[Decimal] = UNSET
    lte: Optional[Decimal] = UNSET
    gt: Optional[Decimal] = UNSET
    gte: Optional[Decimal] = UNSET
    in_: Optional[List[Decimal]] = UNSET


@strawberry.input
class BooleanFilter(ScalarFilter):
    """Filter for boolean scalar fields."""

    exact: Optional[bool] = UNSET


@strawberry.input
class StringFilter(ScalarFilter):
    """Filter for string scalar fields."""

    exact: Optional[str] = UNSET
    iexact: Optional[str] = UNSET
    contains: Optional[str] = UNSET
    icontains: Optional[str] = UNSET
    like: Optional[str] = UNSET
    ilike: Optional[str] = UNSET
    in_: Optional[List[str]] = UNSET


@strawberry.input
class BytesFilter(ScalarFilter):
    """Filter for bytes scalar fields."""

    exact: Optional[bytes] = UNSET
    contains: Optional[bytes] = UNSET
    in_: Optional[List[bytes]] = UNSET


@strawberry.input
class DateTimeFilter(ScalarFilter):
    """Filter for datetime scalar fields."""

    exact: Optional[datetime] = UNSET
    lt: Optional[datetime] = UNSET
    lte: Optional[datetime] = UNSET
    gt: Optional[datetime] = UNSET
    gte: Optional[datetime] = UNSET
    in_: Optional[List[datetime]] = UNSET


@strawberry.input
class DateFilter(ScalarFilter):
    """Filter for date scalar fields."""

    exact: Optional[date] = UNSET
    lt: Optional[date] = UNSET
    lte: Optional[date] = UNSET
    gt: Optional[date] = UNSET
    gte: Optional[date] = UNSET
    in_: Optional[List[date]] = UNSET


@strawberry.input
class TimeFilter(ScalarFilter):
    """Filter for time scalar fields."""

    exact: Optional[time] = UNSET
    lt: Optional[time] = UNSET
    lte: Optional[time] = UNSET
    gt: Optional[time] = UNSET
    gte: Optional[time] = UNSET
    in_: Optional[List[time]] = UNSET


@dataclass
class ObjectOrdering:
    """Object ordering base input."""


class OrderingDirection(enum.Enum):
    """Ordering direction enum - ASC / DESC."""

    ASC = "ASC"
    DESC = "DESC"


OrderingDirectionEnum = strawberry.enum(OrderingDirection)  # type: ignore


@strawberry.input
class ScalarOrdering:
    """Ordering input for a scalar field."""

    direction: OrderingDirectionEnum = OrderingDirection.ASC  # type: ignore


@dataclass
class QueryOne:
    """Input type for querying one entity."""

    primary_key_: PrimaryKeyInput


@strawberry.input
class QueryMany:
    """Input type for querying multiple entities."""

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
