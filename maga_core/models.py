from typing import Dict

from maga_core.types import GraphQLOperation, IModularBackend


class EntityModel:
    __backend__: IModularBackend = None

    def resolve(self, operation: GraphQLOperation, data: Dict):
        self.__backend__.resolve(self, operation, data)
