"""
A custom API used to proxy requests to
"""
# pylint: skip-file

from typing import List

import strawberry
from strawberry import Schema


@strawberry.type
class TestWeapon:
    id: int
    damage: int


@strawberry.type
class TestEntity:
    id: int
    weapons: List[TestWeapon]


@strawberry.type
class Query:
    @strawberry.field
    def retrieve(self, pk: int) -> TestEntity:
        return TestEntity(id=pk, weapons=[TestWeapon(id=1, damage=10)])

    @strawberry.field
    def list(self) -> List[TestEntity]:
        return [
            TestEntity(id=1, weapons=[TestWeapon(id=1, damage=10)]),
            TestEntity(id=2, weapons=[TestWeapon(id=2, damage=10)]),
            TestEntity(id=3, weapons=[TestWeapon(id=1102, damage=10)]),
        ]


create_ids = [100]


# noinspection Pylint
@strawberry.type
class Mutation:
    @strawberry.field
    def create(self, weapons: List[int]) -> TestEntity:
        create_ids.append(create_ids[-1] + 1)
        return TestEntity(
            id=create_ids[-1],
            weapons=[TestWeapon(id=id_, damage=10) for id_ in weapons],
        )

    @strawberry.field
    def update(self, pk: int, weapons: List[int]) -> TestEntity:
        return TestEntity(id=pk, weapons=[TestWeapon(id=id_, damage=10) for id_ in weapons])

    @strawberry.field
    def delete(self, pk: int) -> int:
        return 1


graphql_app = Schema(query=Query, mutation=Mutation)
