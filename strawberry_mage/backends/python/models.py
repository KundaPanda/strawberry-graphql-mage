from strawberry_mage.core.models import EntityModel


class PythonEntityModel(EntityModel):
    __backrefs__ = {}
    __backend__: 'PythonBackend'

    @classmethod
    def post_setup(cls):
        super().post_setup()
        cls._sqla_model = cls.__backend__.converter.convert(cls)
        return cls
