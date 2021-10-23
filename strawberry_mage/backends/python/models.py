from __future__ import annotations

from typing import Dict, TYPE_CHECKING, Type

from strawberry_mage.backends.sqlalchemy.models import SQLAlchemyModel
from strawberry_mage.core.models import EntityModel

if TYPE_CHECKING:
    from strawberry_mage.backends.python.backend import PythonBackend


class PythonEntityModel(EntityModel):
    __backrefs__: Dict[str, str] = {}
    __backend__: PythonBackend
    _sqla_model: Type[SQLAlchemyModel]

    def __init__(self, **kwargs):
        super().__init__()
        model_attrs = set(self.get_attributes())
        for kw in kwargs:
            if kw in model_attrs:
                setattr(self, kw, kwargs[kw])

    @property
    def sqla_model(self) -> Type[SQLAlchemyModel]:
        return self._sqla_model

    @classmethod
    def get_sqla_model(cls) -> Type[SQLAlchemyModel]:
        return cls._sqla_model

    @classmethod
    def post_setup(cls):
        super().post_setup()
        cls._sqla_model = cls.__backend__.converter.convert(cls)
        return cls
