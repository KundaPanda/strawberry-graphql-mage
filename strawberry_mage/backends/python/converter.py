import enum
from decimal import Decimal
from inspect import isclass
from typing import Type, Dict, Union, ForwardRef, Tuple

from sqlalchemy import String, Integer, Float, Numeric, Column, JSON, Enum
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql.type_api import TypeEngine
from strawberry.utils.typing import is_optional, is_list

from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.backends.sqlalchemy.models import create_base_entity
from strawberry_mage.backends.sqlalchemy.utils import make_fk
from strawberry_mage.core.types import IEntityModel, ModuleBoundStrawberryAnnotation


class SQLAlchemyModelConverter:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        self.base = create_base_entity(session_factory)

    TYPE_MAP: Dict[Type, TypeEngine] = {
        str: String,
        int: Integer,
        float: Float,
        Decimal: Numeric
    }

    def _get_sqla_type(self, entity: Type[IEntityModel], attr: str) -> Tuple[Union[str, TypeEngine], bool, bool]:
        python_type = entity.get_attribute_type(attr)
        optional = is_optional(python_type)
        if optional and len(python_type.__args__) == 2:
            python_type, = [a for a in python_type.__args__ if a != None.__class__]
        list_ = is_list(python_type)
        if list_:
            python_type = python_type.__args__[0]
        if isinstance(python_type, ForwardRef):
            python_type = python_type.__forward_arg__
        elif isclass(python_type):
            if issubclass(python_type, enum.Enum):
                return python_type, optional, list_
            if issubclass(python_type, IEntityModel):
                python_type = python_type.__name__
        if isinstance(python_type, str):
            return python_type, optional, list_
        mapped_type = self.TYPE_MAP.get(python_type)
        if mapped_type is None:
            raise TypeError(f'Unknown type {python_type}, cannot find a suitable SQLAlchemy mapping.')
        return mapped_type, optional, list_

    def convert(self, entity: Type[PythonEntityModel]):
        props = {}
        for attr in entity.get_attributes():
            type_, optional, list_ = self._get_sqla_type(entity, attr)
            if isinstance(type_, str):
                # noinspection PyTypeChecker
                resolved_type: Type[IEntityModel] = ModuleBoundStrawberryAnnotation(type_).resolve()
                back_populates = entity.__backrefs__.get(attr)
                if list:
                    rel = relationship(type_, back_populates=back_populates)
                else:
                    fk, rel = make_fk(type_, resolved_type.get_primary_key(), optional, back_populates)
                    props[f'{attr}_{"_".join(resolved_type.get_primary_key())}'] = rel
                props[attr] = rel
            elif isclass(type_) and issubclass(type_, enum.Enum):
                props[attr] = Column(attr, Enum(type_), nullable=optional)
            elif list_:
                props[attr] = Column(attr, MutableList.as_mutable(JSON), nullable=optional)
            else:
                props[attr] = Column(attr, type_, nullable=optional, primary_key=attr in entity.get_primary_key())
        return type(entity.__name__, (self.base,), props)
