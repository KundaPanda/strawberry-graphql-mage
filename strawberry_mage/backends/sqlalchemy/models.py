from inflection import underscore
from sqlalchemy.orm import sessionmaker, as_declarative, declared_attr

from strawberry_mage.core.models import EntityModel
from strawberry_mage.core.types import IEntityModel


@as_declarative()
class _Base:
    @declared_attr
    def __tablename__(self):
        return underscore(self.__name__)


class _BaseMeta(type(IEntityModel), type(_Base)):
    pass


class _SQLAlchemyModel(_Base, EntityModel, metaclass=_BaseMeta):
    __abstract__ = True


def create_base_entity(session_factory: sessionmaker):
    from strawberry_mage.backends.sqlalchemy.backend import SQLAlchemyBackend
    return type('SQLAlchemyModel', (_SQLAlchemyModel,), {
        '__backend__': SQLAlchemyBackend(session_factory),
        '__abstract__': True
    })
