import enum
from typing import Optional, List

from strawberry_mage.backends.python.backend import PythonBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.schema import SchemaManager


class Weapon(PythonEntityModel):
    id: int
    owner: Optional["Entity"]
    damage: int
    name: Optional[str]

    __primary_key__ = ("id",)
    __backrefs__ = {"owner": "weapons"}


class Entity(PythonEntityModel):
    id: int
    weapons: Optional[List[Weapon]]
    submits_to: Optional["King"]

    __primary_key__ = ("id",)
    __backrefs__ = {
        "weapons": "owner",
        "submits_to": "subjects",
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
        "weapons": "owner",
        "submits_to": "subjects",
        "subjects": "submits_to",
    }


schema_manager = SchemaManager(
    Weapon, Entity, Mage, Archer, King, backend=PythonBackend()
)
schema = schema_manager.get_schema()