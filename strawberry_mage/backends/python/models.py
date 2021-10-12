from strawberry_mage.backends.python.converter import SQLAlchemyModelConverter
from strawberry_mage.core.models import EntityModel


class PythonEntityModel(EntityModel):

    @classmethod
    def setup(cls, manager):
        super().setup(manager)
        cls._sqla_model = SQLAlchemyModelConverter.convert(cls)
        return cls
