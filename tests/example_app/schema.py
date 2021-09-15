import enum
from typing import List, Optional

from strawberry_graphql_autoapi.core.backend import SQLAlchemyBackend
from strawberry_graphql_autoapi.core.models import EntityModel
from strawberry_graphql_autoapi.core.schema import SchemaManager


dummy = SQLAlchemyBackend()


class Weapon(EntityModel):
    id: int
    damage: int
    owner: Optional['Entity']
    name: Optional[str]

    _primary_key__ = ('id',)
    __backend__ = dummy


class Entity(EntityModel):
    id: int
    weapons: List[Weapon]

    _primary_key__ = ('id',)
    __backend__ = dummy


class Mage(Entity):
    class MageTypeEnum(enum.Enum):
        FIRE = 1
        WATER = 2
        EARTH = 3
        AIR = 4
    power_source: MageTypeEnum


class Archer(Entity):
    draw_strength: float


schema = SchemaManager(Weapon, Entity, Mage, Archer).get_schema()
