import abc
import dataclasses
import enum
import sys
from functools import lru_cache
from typing import Any, Type, Tuple, Set, Dict, List, Union, Optional, Iterable

from strawberry import Schema
from strawberry.annotation import StrawberryAnnotation
from strawberry.schema.types import ConcreteType
from strawberry.types import Info

from strawberry_graphql_mage.core.strawberry_types import StrawberryModelType, ROOT_NS


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
    def register_model(self, model: Type['IEntityModel']):
        raise NotImplemented

    @abc.abstractmethod
    def get_strawberry_field_type(self, type_: Any) -> Type:
        raise NotImplemented

    @abc.abstractmethod
    def get_attributes(self, model: Type['IEntityModel'], operation: Optional[GraphQLOperation] = None) \
            -> List[str]:
        raise NotImplemented

    @abc.abstractmethod
    def get_attribute_types(self, model: Type['IEntityModel']) -> Dict[str, Type]:
        raise NotImplemented

    @abc.abstractmethod
    def get_attribute_type(self, model: Type['IEntityModel'], attr: str) -> Type:
        raise NotImplemented

    @abc.abstractmethod
    def get_primary_key(self, model: Type['IEntityModel']) -> Tuple:
        raise NotImplemented

    @abc.abstractmethod
    def get_parent_class_name(self, model: Type['IEntityModel']) -> Optional[str]:
        raise NotImplemented

    @abc.abstractmethod
    def get_children_class_names(self, model: Type['IEntityModel']) -> Optional[List[str]]:
        raise NotImplemented

    @abc.abstractmethod
    def get_operations(self, model: Type['IEntityModel']) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    @abc.abstractmethod
    async def resolve(self, model: Type['IEntityModel'], operation: GraphQLOperation, info: Info, data: Any) -> Any:
        raise NotImplemented

    @abc.abstractmethod
    def pre_setup(self, models: Iterable[Type['IEntityModel']]) -> None:
        raise NotImplemented

    @abc.abstractmethod
    def post_setup(self) -> None:
        raise NotImplemented

    @abc.abstractmethod
    def get_polymorphic_type(self, base_type: ConcreteType):
        raise NotImplemented


class ISchemaManager(abc.ABC):

    @property
    @abc.abstractmethod
    def backend(self) -> IDataBackend:
        raise NotImplemented

    @abc.abstractmethod
    def get_schema(self) -> Schema:
        raise NotImplemented

    @abc.abstractmethod
    def get_models(self) -> List['IEntityModel']:
        raise NotImplemented

    @abc.abstractmethod
    def get_model_for_name(self, name: str) -> Optional[Type['IEntityModel']]:
        raise NotImplemented


@dataclasses.dataclass
class IEntityModel(abc.ABC):
    __backend__: IDataBackend
    __primary_key__: Any
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
    def get_schema_manager(cls) -> ISchemaManager:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_attributes(cls, operation: Optional[GraphQLOperation] = None) -> List[str]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_attribute_types(cls) -> Dict[str, Type]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_attribute_type(cls, attr: str) -> Union[Type, str]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_primary_key(cls) -> Tuple:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_parent_class_name(cls) -> Optional[str]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def get_children_class_names(cls) -> Optional[List[str]]:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    async def resolve(cls, operation: GraphQLOperation, info: Info, data: Any) -> Any:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def pre_setup(cls, manager: ISchemaManager) -> None:
        raise NotImplemented

    @classmethod
    @abc.abstractmethod
    def post_setup(cls) -> None:
        raise NotImplemented
