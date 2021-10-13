from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.models import EntityModel


class PythonEntityModel(EntityModel):
    __backrefs__ = {}
    __backend__: 'PythonBackend'
    _sqla_model: _SQLAlchemyModel

    @property
    def sqla_model(self) -> _SQLAlchemyModel:
        return self._sqla_model

    @classmethod
    def post_setup(cls):
        super().post_setup()
        cls._sqla_model = cls.__backend__.converter.convert(cls)
        return cls
