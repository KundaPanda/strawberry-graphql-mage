import abc
import enum
from typing import Dict


class Order(enum.Enum):
    ASC = 'ASC'
    DESC = 'DESC'


class GraphQLOperation(enum.Enum):
    QUERY_ONE = 1
    QUERY_MANY = 2
    CREATE_ONE = 3
    CREATE_MANY = 4
    UPDATE_ONE = 5
    UPDATE_MANY = 6
    DELETE_ONE = 7
    DELETE_MANY = 8


class IModularBackend(abc.ABC):
    def register_model(self, model):
        model.__backend__ = self

    def resolve(self, model, operation: GraphQLOperation, data: Dict):
        raise NotImplemented
