"""SQLAlchemy model type."""

from sqlalchemy.orm import registry
from sqlalchemy.orm.decl_api import DeclarativeMeta


class _SqlAlchemyModelMeta(DeclarativeMeta):
    __name__: str


class SqlAlchemyModel(metaclass=_SqlAlchemyModelMeta):
    """Helper for type hinting sqlalchemy models."""

    __abstract__ = True
    __tablename__: str
    registry = registry()
