import enum
from dataclasses import dataclass
from typing import List, Optional as O, Callable, Optional, Type

import strawberry
from strawberry.arguments import UNSET
from strawberry.type import StrawberryType

ROOT_NS = 'strawberry_graphql_autoapi.core.types_generated'


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
    input_types: Optional[StrawberryModelInputTypes] = None
    query_one: Optional[Callable] = None
    query_many: Optional[Callable] = None
    create_one: Optional[Callable] = None
    create_many: Optional[Callable] = None
    update_one: Optional[Callable] = None
    update_many: Optional[Callable] = None
    delete_one: Optional[Callable] = None
    delete_many: Optional[Callable] = None


@dataclass
class ObjectFilter:
    AND_: Optional[List[Optional['ObjectFilter']]]
    OR_: Optional[List[Optional['ObjectFilter']]]


@dataclass
class ScalarFilter:
    pass


@strawberry.input
class IntegerFilter(ScalarFilter):
    exact: O[int] = UNSET
    lt: O[int] = UNSET
    lte: O[int] = UNSET
    gt: O[int] = UNSET
    gte: O[int] = UNSET


@strawberry.input
class FloatFilter(ScalarFilter):
    exact: O[float] = UNSET
    lt: O[float] = UNSET
    lte: O[float] = UNSET
    gt: O[float] = UNSET
    gte: O[float] = UNSET


@strawberry.input
class StringFilter(ScalarFilter):
    exact: O[str] = UNSET
    iexact: O[str] = UNSET
    contains: O[str] = UNSET
    icontains: O[str] = UNSET


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
    str: StringFilter
}
