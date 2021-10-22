import abc
import dataclasses
import enum
import sys
from functools import lru_cache
from typing import Any, Dict, Generic, Iterable, List, Optional, Protocol, Set, Tuple, Type, TypeVar, Union

from sqlalchemy.orm import registry
from sqlalchemy.orm.decl_api import DeclarativeMeta
from strawberry import Schema
from strawberry.annotation import StrawberryAnnotation
from strawberry.schema.types import ConcreteType
from strawberry.types import Info

from strawberry_mage.core.strawberry_types import ROOT_NS, StrawberryModelType


class ModuleBoundStrawberryAnnotation(StrawberryAnnotation):
    def __init__(self, annotation: Union[str, object], namespace: str = ROOT_NS):
        super(ModuleBoundStrawberryAnnotation, self).__init__(annotation)
        self._namespace = namespace

    @property
    def namespace(self):
        return vars(sys.modules[self._namespace])

    @namespace.setter
    def namespace(self, value):
        return

    @staticmethod
    def from_annotation(other: StrawberryAnnotation):
        return ModuleBoundStrawberryAnnotation(annotation=other.annotation)


class SqlAlchemyModel(metaclass=DeclarativeMeta):
    __abstract__ = True
    __tablename__: str
    registry = registry()


class IsDataclass(Protocol):
    # Dataclass argument type hint
    __dataclass_fields__: Dict


class Order(enum.Enum):
    ASC = "ASC"
    DESC = "DESC"


TEntity = TypeVar("TEntity", bound="IEntityModel")


class GraphQLOperation(enum.Enum):
    QUERY_ONE = 1
    QUERY_MANY = 2
    CREATE_ONE = 3
    CREATE_MANY = 4
    UPDATE_ONE = 5
    UPDATE_MANY = 6
    DELETE_ONE = 7
    DELETE_MANY = 8


class IDataBackend(abc.ABC, Generic[TEntity]):
    @abc.abstractmethod
    def register_model(self, model: Type[TEntity]):
        raise NotImplementedError

    @abc.abstractmethod
    def get_strawberry_field_type(self, type_: Any) -> Type:
        raise NotImplementedError

    @abc.abstractmethod
    def get_attributes(self, model: Type[TEntity], operation: Optional[GraphQLOperation] = None) -> List[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_attribute_types(self, model: Type[TEntity]) -> Dict[str, Type]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_attribute_type(self, model: Type[TEntity], attr: str) -> Type:
        raise NotImplementedError

    @abc.abstractmethod
    def get_primary_key(self, model: Type[TEntity]) -> Tuple:
        raise NotImplementedError

    @abc.abstractmethod
    def get_parent_class_name(self, model: Type[TEntity]) -> Optional[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_children_class_names(self, model: Type[TEntity]) -> Optional[List[str]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_operations(self, model: Type[TEntity]) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    @abc.abstractmethod
    async def resolve(
        self,
        model: Type[TEntity],
        operation: GraphQLOperation,
        info: Info,
        data: Any,
        *args,
        dataset: Optional[Iterable[Any]] = None,
        **kwargs
    ) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    def pre_setup(self, models: Iterable[Type[TEntity]]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def post_setup(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_polymorphic_type(self, base_type: ConcreteType):
        raise NotImplementedError


class ISchemaManager(abc.ABC):
    @property
    @abc.abstractmethod
    def backend(self) -> IDataBackend:
        raise NotImplementedError

    @abc.abstractmethod
    def get_schema(self) -> Schema:
        raise NotImplementedError

    @abc.abstractmethod
    def get_models(self) -> List["IEntityModel"]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_model_for_name(self, name: str) -> Optional[Type["IEntityModel"]]:
        raise NotImplementedError


@dataclasses.dataclass
class IEntityModel(abc.ABC):
    __backend__: IDataBackend = dataclasses.field(init=False)
    __primary_key__: Any = dataclasses.field(init=False)
    _strawberry_type: StrawberryModelType = dataclasses.field(init=False)

    @classmethod
    @abc.abstractmethod
    def get_strawberry_type(cls) -> StrawberryModelType:
        raise NotImplementedError

    @classmethod
    @lru_cache
    @abc.abstractmethod
    def get_operations(cls) -> Set[GraphQLOperation]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_schema_manager(cls) -> ISchemaManager:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_attributes(cls, operation: Optional[GraphQLOperation] = None) -> List[str]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_attribute_types(cls) -> Dict[str, Type]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_attribute_type(cls, attr: str) -> Union[Type, str]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_primary_key(cls) -> Tuple:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_parent_class_name(cls) -> Optional[str]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_children_class_names(cls) -> Optional[List[str]]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def resolve(cls, operation: GraphQLOperation, info: Info, data: Any) -> Any:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def pre_setup(cls, manager: ISchemaManager) -> None:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def post_setup(cls) -> None:
        raise NotImplementedError
