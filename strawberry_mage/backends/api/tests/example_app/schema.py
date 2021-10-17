import dataclasses
import enum
from typing import Optional, List, Any, Type

from strawberry.types import Info

from strawberry_mage.backends.api.tests.api import graphql_app
from strawberry_mage.backends.api.tests.example_app.custom_backend import CustomBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.schema import SchemaManager
from strawberry_mage.core.types import GraphQLOperation


class Weapon(PythonEntityModel):
    id: int
    owner: Optional['Entity']
    damage: int
    name: Optional[str]

    __primary_key__ = ('id',)
    __primary_key_autogenerated__ = False
    __backrefs__ = {
        'owner': 'weapons'
    }


class Entity(PythonEntityModel):
    id: int
    weapons: Optional[List[Weapon]]
    submits_to: Optional['King']

    __primary_key__ = ('id',)
    __primary_key_autogenerated__ = False
    __backrefs__ = {
        'weapons': 'owner',
        'submits_to': 'subjects',
    }


class Mage(Entity):
    class MageTypeEnum(enum.Enum):
        FIRE = 1
        WATER = 2
        EARTH = 3
        AIR = 4

    power_source: MageTypeEnum


class Archer(Entity):
    draw_strength: float


class King(Entity):
    name: Optional[str]
    subjects: Optional[List[Entity]]

    __backrefs__ = {
        'weapons': 'owner',
        'submits_to': 'subjects',
        'subjects': 'submits_to',
    }


async def resolve(model: Type[PythonEntityModel], operation: GraphQLOperation, info: Info, data: Any):
    op = {
        GraphQLOperation.QUERY_ONE: 'retrieve',
        GraphQLOperation.QUERY_MANY: 'list',
        GraphQLOperation.CREATE_ONE: 'create',
        GraphQLOperation.UPDATE_ONE: 'update',
        GraphQLOperation.DELETE_ONE: 'delete',
    }.get(operation)
    root = 'query' if operation in {GraphQLOperation.QUERY_ONE, GraphQLOperation.QUERY_MANY} else 'mutation'
    result = await graphql_app.execute(f'{root} {{ {op}{{ id __typename weapons {{ id __typename damage }} }} }}')
    return result.data[op]


backend = CustomBackend(resolve=resolve)
schema_manager = SchemaManager(Weapon, Entity, Mage, Archer, King, backend=backend)
schema = schema_manager.get_schema()
