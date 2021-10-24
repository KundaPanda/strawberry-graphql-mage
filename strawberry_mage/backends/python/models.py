"""An entity model that represents a python object."""

from __future__ import annotations

from typing import Dict, TYPE_CHECKING, Type

from overrides import overrides

from strawberry_mage.backends.sqlalchemy.models import SQLAlchemyModel
from strawberry_mage.core.models import EntityModel

if TYPE_CHECKING:
    from strawberry_mage.backends.python.backend import PythonBackend


class PythonEntityModel(EntityModel):
    """An entity model that represents a python object."""

    __backrefs__: Dict[str, str] = {}
    __backend__: PythonBackend
    _sqla_model: Type[SQLAlchemyModel]

    def __init__(self, **kwargs):
        """Create a new Python EntityModel."""
        super().__init__()
        model_attrs = set(self.get_attributes())
        for arg_name, arg_value in kwargs.items():
            if arg_name in model_attrs:
                setattr(self, arg_name, arg_value)

    @property
    def sqla_model(self) -> Type[SQLAlchemyModel]:
        """Get the converted SQLAlchemy model."""
        return self._sqla_model

    @classmethod
    def get_sqla_model(cls) -> Type[SQLAlchemyModel]:
        """Get the converted SQLAlchemy model."""
        return cls._sqla_model

    @classmethod
    @overrides
    def post_setup(cls):
        super().post_setup()
        cls._sqla_model = cls.__backend__.converter.convert(cls)
        return cls
