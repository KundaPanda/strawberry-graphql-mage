from sqlalchemy.orm import registry
from sqlalchemy.orm.decl_api import DeclarativeMeta


class SqlAlchemyModel(metaclass=DeclarativeMeta):
    """
    Helper for type hinting sqlalchemy models
    """
    __abstract__ = True
    __tablename__: str
    registry = registry()
