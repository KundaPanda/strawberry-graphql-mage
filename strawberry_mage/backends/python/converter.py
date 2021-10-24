"""Class for converting python entity models to SQLAlchemy models."""

import enum
import sys
from decimal import Decimal
from inspect import isclass
from typing import Dict, ForwardRef, Tuple, Type, Union

from inflection import underscore
from sqlalchemy import (
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    and_,
)
from sqlalchemy.engine import Engine
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from sqlalchemy.sql.type_api import TypeEngine
from strawberry.utils.typing import is_list, is_optional

from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.backends.sqlalchemy.models import SQLAlchemyModel, create_base_entity
from strawberry_mage.backends.sqlalchemy.utils import make_composite_fk
from strawberry_mage.core.types import IEntityModel

if sys.version_info >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)


class SQLAlchemyModelConverter:
    """Class for converting python entity models to SQLAlchemy models."""

    def __init__(self, engine: Engine):
        """
        Create a new converter instance.

        :param engine: engine to use for SQLAlchemy backend creation .
        """
        self.base = create_base_entity(engine)

    TYPE_MAP: Dict[Type, Type[TypeEngine]] = {
        str: String,
        int: Integer,
        float: Float,
        Decimal: Numeric,
    }

    def _get_sqla_type(
        self, entity: Type[IEntityModel], attr: str
    ) -> Tuple[Union[enum.Enum, str, TypeEngine], bool, bool]:
        python_type = entity.get_attribute_type(attr)
        optional = is_optional(python_type)
        if optional and len(getattr(python_type, "__args__")) == 2:
            (python_type,) = [a for a in getattr(python_type, "__args__") if a is not NoneType]
        list_ = is_list(python_type)
        if list_:
            python_type = getattr(python_type, "__args__")[0]
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
            raise TypeError(f"Unknown type {python_type}, cannot find a suitable SQLAlchemy mapping.")
        return mapped_type, optional, list_

    @staticmethod
    def _get_related_entity(entity: Type[PythonEntityModel], name: str) -> Type[PythonEntityModel]:
        return getattr(sys.modules[entity.__module__], name)

    def convert(self, entity: Type[PythonEntityModel]) -> Type[SQLAlchemyModel]:
        """
        Convert a python entity model to a SQLAlchemy entity model.

        :param entity: model to convert
        :return: converted model
        """
        attrs = {}
        parent_name = entity.get_parent_class_name()
        if parent_name == entity.__name__:
            parent_name = None
        parent = self._get_related_entity(entity, parent_name) if parent_name else None
        inherited_attrs = []
        for attr in entity.get_attributes():
            if parent and attr in parent.get_attributes() and attr not in entity.get_primary_key():
                continue
            type_, optional, list_ = self._get_sqla_type(entity, attr)
            if isinstance(type_, str):
                # noinspection PyTypeChecker
                resolved_type = self._get_related_entity(entity, type_)
                back_populates = entity.__backrefs__.get(attr)
                if list_:
                    joins = ",".join(
                        f"{entity.__name__}.{k} == {resolved_type.__name__}.{back_populates}_{k}"
                        for k in entity.get_primary_key()
                    )
                    rel = relationship(
                        type_,
                        back_populates=back_populates,
                        primaryjoin=f"and_({joins})",
                    )
                else:
                    fks, rel, constraint = make_composite_fk(
                        type_,
                        resolved_type.get_primary_key(),
                        entity.__name__,
                        attr,
                        optional,
                        back_populates,
                    )
                    for (name, fk) in fks:
                        attrs[f"{attr}_{name}"] = fk
                    if "__table_args__ " not in attrs:
                        attrs["__table_args__"] = (constraint,)
                    else:
                        attrs["__table_args__"] = tuple([*attrs["__table_args__"], constraint])
                attrs[attr] = rel
            elif isclass(type_) and issubclass(type_, enum.Enum):
                attrs[attr] = Column(attr, Enum(type_), nullable=optional)
            elif list_:
                attrs[attr] = Column(attr, MutableList.as_mutable(JSON), nullable=optional)
            else:
                if attr in entity.get_primary_key():
                    autoincrement = entity.__primary_key_autogenerated__
                    if parent_name:
                        if attr not in parent.get_primary_key():
                            raise AttributeError(
                                "Invalid primary key, a subclassed entity must have the same primary "
                                "key as the superclass."
                            )
                        type_ = ForeignKey(f"{underscore(parent_name)}.{attr}")
                        autoincrement = "auto"
                        inherited_attrs.append(attr)
                    attrs[attr] = Column(attr, type_, primary_key=True, autoincrement=autoincrement)
                else:
                    attrs[attr] = Column(attr, type_, nullable=optional)
        if parent_name:
            attrs["__mapper_args__"] = {
                "polymorphic_identity": underscore(entity.__name__),
                "inherit_condition": and_(*[attrs[a] == getattr(parent.get_sqla_model(), a) for a in inherited_attrs]),
            }
        elif entity.get_children_class_names():
            attrs["__mapper_args__"] = {
                "polymorphic_on": "entity_polymorphic_type_",
                "polymorphic_identity": underscore(entity.__name__),
            }
            attrs["entity_polymorphic_type_"] = Column(String)

        if parent:
            parent_model: Type[SQLAlchemyModel] = parent.get_sqla_model()  # type: ignore
            return type(entity.__name__, (parent_model,), attrs)
        return type(entity.__name__, (self.base,), attrs)
