from typing import Type, Dict

from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.models import EntityModel


class PyModelMeta(type(EntityModel), type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls._sqla_model = None

    @property
    def sqla_model(cls) -> Type[_SQLAlchemyModel]:
        return cls._sqla_model


class PythonEntityModel(EntityModel, metaclass=PyModelMeta):
    __backrefs__: Dict[str, str] = {}
    __backend__: 'PythonBackend'
    _sqla_model: Type[_SQLAlchemyModel]

    def __init__(self, **kwargs):
        super().__init__()
        model_attrs = set(self.get_attributes())
        for kw in kwargs:
            if kw in model_attrs:
                setattr(self, kw, kwargs[kw])

    @property
    def sqla_model(self) -> Type[_SQLAlchemyModel]:
        return self._sqla_model

    @classmethod
    def post_setup(cls):
        super().post_setup()
        cls._sqla_model = cls.__backend__.converter.convert(cls)
        return cls
