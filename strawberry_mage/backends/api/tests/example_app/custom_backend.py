from typing import Set, Type, Any, Iterable, Optional, Callable, Coroutine

from strawberry.types import Info

from strawberry_mage.backends.api.backend import APIBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.core.types import GraphQLOperation, IEntityModel


class CustomBackend(APIBackend):
    def __init__(self,
                 resolve: Callable[
                     [Type[PythonEntityModel], GraphQLOperation, Info, Any], Coroutine[Any, Any, Iterable[dict]]],
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.resolve_fn = resolve

    def add_dataset(self, dataset: Iterable[dict], model: Optional[Type[PythonEntityModel]] = None,
                    model_mapper: Callable[[dict], Type[PythonEntityModel]] = None):
        from strawberry_mage.backends.api.tests.example_app.schema import Entity, Weapon
        mapping = {
            'TestEntity': Entity,
            'TestWeapon': Weapon
        }

        def get_model(entry: dict):
            return mapping[entry['__typename']]

        return super().add_dataset(dataset, model_mapper=get_model)

    def get_operations(self, model: Type[IEntityModel]) -> Set[GraphQLOperation]:
        return {
            GraphQLOperation.QUERY_ONE,
            GraphQLOperation.QUERY_MANY,
            GraphQLOperation.CREATE_ONE,
            GraphQLOperation.UPDATE_ONE,
            GraphQLOperation.DELETE_ONE,
        }

    async def resolve(self, model: Type[PythonEntityModel], operation: GraphQLOperation, info: Info, data: Any,
                      dataset: Optional[Iterable[dict]] = None) -> Any:
        api_dataset = await self.resolve_fn(model, operation, info, data)
        return await super().resolve(model, operation, info, data, api_dataset)
