import enum
from typing import Union, Tuple, Type

from inflection import underscore
from sqlalchemy import Column, Integer, ForeignKey, String, Enum, Float, create_engine
from sqlalchemy.orm import relationship, sessionmaker

from strawberry_mage.backends.sqlalchemy.models import create_base_entity
from strawberry_mage.core.schema import SchemaManager

engine = create_engine('sqlite:///', echo=True)

Base = create_base_entity(sessionmaker(bind=engine))


def make_fk(remote: Union[str, Type[Base]], remote_pk='id', optional=False, back_populates=None,
            foreign_kwargs=None, rel_kwargs=None) -> Tuple[Column, relationship]:
    if not isinstance(remote, str):
        remote = remote.__tablename__
    if foreign_kwargs is None:
        foreign_kwargs = {}
    if rel_kwargs is None:
        rel_kwargs = {}
    remote_table = underscore(remote)
    fk = Column(Integer, ForeignKey(f'{remote_table}.{remote_pk}'), nullable=optional, **foreign_kwargs)
    rel = relationship(remote, back_populates=back_populates, foreign_keys=[fk], **rel_kwargs)
    return fk, rel


class Weapon(Base):
    id = Column(Integer, primary_key=True)
    owner_id, owner = make_fk('Entity', optional=True, back_populates='weapons')
    damage = Column(Integer, nullable=False)
    name = Column(String(30), nullable=True)


class Entity(Base):
    id = Column(Integer, primary_key=True)
    weapons = relationship(Weapon, back_populates='owner')
    entity_class = Column(String, nullable=False)
    submits_to_id, submits_to = make_fk('King', optional=True, back_populates='subjects')

    __mapper_args__ = {
        'polymorphic_on': entity_class,
        'polymorphic_identity': 'entity'
    }


class Mage(Entity):
    class MageTypeEnum(enum.Enum):
        FIRE = 1
        WATER = 2
        EARTH = 3
        AIR = 4

    id = Column(Integer, ForeignKey('entity.id'), primary_key=True)
    power_source = Column(Enum(MageTypeEnum), nullable=False)
    test = Column(Enum(MageTypeEnum))

    __mapper_args__ = {
        'polymorphic_identity': 'mage'
    }


class Archer(Entity):
    id = Column(Integer, ForeignKey('entity.id'), primary_key=True)
    draw_strength = Column(Float, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'archer'
    }


class King(Entity):
    id = Column(Integer, ForeignKey('entity.id'), primary_key=True)
    name = Column(String)
    subjects = relationship('Entity', back_populates='submits_to', foreign_keys='Entity.submits_to_id')

    __mapper_args__ = {
        'polymorphic_identity': 'king',
        'inherit_condition': id == Entity.id
    }


schema = SchemaManager(Weapon, Entity, Mage, Archer, King).get_schema()

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
