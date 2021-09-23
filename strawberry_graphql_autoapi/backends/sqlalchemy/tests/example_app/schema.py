import enum
from abc import ABC
from typing import Union, Tuple, Type

from inflection import underscore
from sqlalchemy import Column, Integer, ForeignKey, String, Enum, Float, create_engine
from sqlalchemy.orm import declared_attr, relationship, as_declarative, sessionmaker

from strawberry_graphql_autoapi.backends.sqlalchemy.backend import SQLAlchemyBackend
from strawberry_graphql_autoapi.core.models import EntityModel
from strawberry_graphql_autoapi.core.schema import SchemaManager
from strawberry_graphql_autoapi.core.types import IEntityModel

engine = create_engine('sqlite:///', echo=True)
backend = SQLAlchemyBackend(session_maker=sessionmaker(bind=engine))


@as_declarative()
class Base:
    @declared_attr
    def __tablename__(self):
        return underscore(self.__name__)

    __backend__ = backend


class BaseMeta(type(IEntityModel), type(Base)):
    pass


class AbstractModel(Base, EntityModel, metaclass=BaseMeta):
    __abstract__ = True


def make_fk(remote: Union[str, Type[Base]], remote_pk='id', optional=False, back_populates=None) \
        -> Tuple[Column, relationship]:
    if not isinstance(remote, str):
        remote = remote.__tablename__
    remote_table = underscore(remote)
    fk = Column(Integer, ForeignKey(f'{remote_table}.{remote_pk}'), nullable=optional)
    rel = relationship(remote, back_populates=back_populates)
    return fk, rel


class Weapon(AbstractModel):
    id = Column(Integer, primary_key=True)
    owner_id, owner = make_fk('Entity', optional=True, back_populates='weapons')
    damage = Column(Integer, nullable=False)
    name = Column(String(30), nullable=True)


class Entity(AbstractModel):
    id = Column(Integer, primary_key=True)
    weapons = relationship(Weapon, back_populates='owner')
    entity_class = Column(String, nullable=False)

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


schema = SchemaManager(Weapon, Entity, Mage, Archer).get_schema()

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
