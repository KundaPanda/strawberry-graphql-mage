import abc
import enum
import sys
from functools import lru_cache
from typing import Any, Type, Tuple, Set, Dict, List, Union

from strawberry.annotation import StrawberryAnnotation

from strawberry_graphql_autoapi.core.strawberry_types import StrawberryModelType, ROOT_NS


class ModuleBoundStrawberryAnnotation(StrawberryAnnotation):
    def __init__(self, annotation: Union[str, object]):
        super(ModuleBoundStrawberryAnnotation, self).__init__(annotation)

    @property
    def namespace(self):
        return vars(sys.modules[ROOT_NS])

    @namespace.setter
    def namespace(self, value):
        return

    @staticmethod
    def from_annotation(other: StrawberryAnnotation):
        return ModuleBoundStrawberryAnnotation(annotation=other.annotation)


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


class IDataBackend(abc.ABC):
    @abc.abstractmethod
    def register_model(self, model):
        raise NotImplemented

    @abc.abstractmethod
    def get_strawberry_field_type(self, type_: Any) -> Type:
        raise NotImplemented

    @abc.abstractmethod
    def get_all_attributes(self, model) -> List[str]:
        raise NotImplemented

    @abc.abstractmethod
    def get_attribute_types(self, model) -> Dict[str, Type]:
        raise NotImplemented

    @abc.abstractmethod
    def get_attribute_type(self, model, attr: str) -> Type:
        raise NotImplemented

    @abc.abstractmethod
    def get_primary_key(self, model) -> Tuple:
        raise NotImplemented

    @abc.abstractmethod
    def get_operations(self, model: Type['IEntityModel']) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    @abc.abstractmethod
    def resolve(self, model, operation: GraphQLOperation, data: Any) -> Any:
        raise NotImplemented


class IEntityModel(abc.ABC):
    __backend__: IDataBackend = None
    __primary_key__: Any = None
    _strawberry_type: StrawberryModelType

    @classmethod
    @abc.abstractmethod
    def get_strawberry_type(cls) -> StrawberryModelType:
        raise NotImplemented

    @classmethod
    @lru_cache
    @abc.abstractmethod
    def get_operations(cls) -> Set[GraphQLOperation]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def resolve(cls, operation: GraphQLOperation, data: Any) -> Any:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def setup(cls) -> None:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_all_attributes(cls) -> List[str]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_attribute_types(cls) -> Dict[str, Type]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_attribute_type(cls, attr: str) -> Type:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_primary_key(cls) -> Tuple:
        raise NotImplemented
