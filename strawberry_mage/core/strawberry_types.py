import dataclasses
import enum
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from typing import List, Optional as O, Callable, Type

import strawberry
from strawberry.arguments import UNSET
from strawberry.schema.config import StrawberryConfig
from strawberry.schema.schema_converter import GraphQLCoreConverter
from strawberry.schema.types.scalar import DEFAULT_SCALAR_REGISTRY

ROOT_NS = 'strawberry_mage.core.types_generated'


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
class StringFilter(ScalarFilter):
    exact: O[str] = UNSET
    iexact: O[str] = UNSET
    contains: O[str] = UNSET
    icontains: O[str] = UNSET
    like: O[str] = UNSET
    ilike: O[str] = UNSET
    in_: O[List[str]] = UNSET


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
    str: StringFilter
}
