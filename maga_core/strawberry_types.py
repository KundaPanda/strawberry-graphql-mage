from dataclasses import dataclass
from typing import List, Optional as O

from strawberry.arguments import UNSET


@dataclass
class ObjectFilter:
    pass


@dataclass
class ScalarFilter:
    pass


@dataclass
class IntegerFilter(ScalarFilter):
    exact: O[int] = UNSET
    lt: O[int] = UNSET
    lte: O[int] = UNSET
    gt: O[int] = UNSET
    gte: O[int] = UNSET


@dataclass
class ObjectOrdering:
    pass


@dataclass
class ScalarOrdering:
    pass


@dataclass
class Ordered:
    order: O[List[ObjectOrdering]] = UNSET


@dataclass
class Paginated:
    page_size: O[int] = 30
    page_number: O[int] = 1


@dataclass
class QueryOne(Paginated, Ordered):
    pass


@dataclass
class QueryMany(Paginated, Ordered):
    filters: O[List[ObjectFilter]] = UNSET
