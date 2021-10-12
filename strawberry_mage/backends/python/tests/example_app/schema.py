import enum
from typing import Optional, List

from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.schema import SchemaManager


class Weapon(PythonEntityModel):
    id: int
    owner: Optional['Entity']
    damage: int
    name: Optional[str]

    __primary_key__ = ('id',)
    __backrefs__ = {
        'owner': 'weapons'
    }


class Entity(PythonEntityModel):
    id: int
    weapons: List[Weapon]
    submits_to: Optional['King']

    __primary_key__ = ('id',)
    __backrefs__ = {
        'weapons': 'owner',
        'submits_to': 'subjects',
    }


class Mage(PythonEntityModel):
    class MageTypeEnum(enum.Enum):
        FIRE = 1
        WATER = 2
        EARTH = 3
        AIR = 4

    id: int
    power_source: MageTypeEnum


class Archer(Entity):
    id: int
    draw_strength: float


class King(Entity):
    id: int
    name: Optional[str]
    subjects: List[Entity]

    __backrefs__ = {
        'subjects': 'submits_to',
    }


schema = SchemaManager(Weapon, Entity, Mage, Archer, King).get_schema()
