from decimal import Decimal
from typing import Type, Dict, Union

from sqlalchemy import String, Integer, Float, Numeric
from sqlalchemy.sql.type_api import TypeEngine

from strawberry_mage.core.types import IEntityModel


class SQLAlchemyModelConverter:
    TYPE_MAP: Dict[Type, TypeEngine] = {
        str: String,
        int: Integer,
        float: Float,
        Decimal: Numeric
    }

    @classmethod
    def _get_sqla_type(cls, entity: Type[IEntityModel], attr: str) -> Union[str, TypeEngine]:
        python_type = entity.get_attribute_type(attr)
        if issubclass(python_type, IEntityModel):
            python_type = python_type.__name__
        if isinstance(python_type, str):
            return python_type
        mapped_type = cls.TYPE_MAP.get(python_type)
        if mapped_type is None:
            raise TypeError(f'Unknown type {python_type}, cannot find a suitable SQLAlchemy mapping.')
        return mapped_type

    @classmethod
    def convert(cls, entity: Type[IEntityModel]):
        for attr in entity.get_attributes():
            type_ = cls._get_sqla_type(entity, attr)

