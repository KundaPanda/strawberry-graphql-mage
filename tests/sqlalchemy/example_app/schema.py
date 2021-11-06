import enum

from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Table
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import relationship

from strawberry_mage.backends.sqlalchemy.backend import SQLAlchemyBackend
from strawberry_mage.backends.sqlalchemy.models import create_base_entity
from strawberry_mage.backends.sqlalchemy.utils import make_fk
from strawberry_mage.core.schema import SchemaManager

Base = create_base_entity()

entity_title_m2m = Table(
    "entity_title_m2m",
    Base.metadata,
    Column("entity_id", Integer, ForeignKey("entity.id"), primary_key=True),
    Column("title_name", String, ForeignKey("title.name"), primary_key=True),
)


class Title(Base):
    name = Column(String, primary_key=True)
    entities = relationship("Entity", secondary=entity_title_m2m, back_populates="titles")


class Weapon(Base):
    id = Column(Integer, primary_key=True)
    owner_id, owner = make_fk("Entity", back_populates="weapons")
    damage = Column(Integer, nullable=False)
    name = Column(String(30), nullable=True)


class Entity(Base):
    id = Column(Integer, primary_key=True)
    weapons = relationship(Weapon, back_populates="owner")
    entity_class = Column(String, nullable=False)
    submits_to_id, submits_to = make_fk("King", back_populates="subjects")
    titles = relationship(Title, secondary=entity_title_m2m, back_populates="entities")

    __mapper_args__ = {"polymorphic_on": entity_class, "polymorphic_identity": "entity"}


class Mage(Entity):
    class MageTypeEnum(enum.Enum):
        FIRE = 1
        WATER = 2
        EARTH = 3
        AIR = 4

    id = Column(Integer, ForeignKey("entity.id"), primary_key=True)
    power_source = Column(Enum(MageTypeEnum), nullable=False)
    test = Column(Enum(MageTypeEnum))

    __mapper_args__ = {"polymorphic_identity": "mage"}


class Archer(Entity):
    id = Column(Integer, ForeignKey("entity.id"), primary_key=True)
    draw_strength = Column(Float, nullable=False)

    __mapper_args__ = {"polymorphic_identity": "archer"}


class King(Entity):
    id = Column(Integer, ForeignKey("entity.id"), primary_key=True)
    name = Column(String)
    subjects = relationship("Entity", back_populates="submits_to", foreign_keys="Entity.submits_to_id")

    __mapper_args__ = {
        "polymorphic_identity": "king",
        "inherit_condition": id == Entity.id,
    }


engine = create_async_engine("sqlite+aiosqlite:///", echo=True)
schema = SchemaManager(Weapon, Entity, Mage, Archer, King, Title, backend=SQLAlchemyBackend(engine)).get_schema()

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
