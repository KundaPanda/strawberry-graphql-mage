"""All core python classes."""

import abc
import dataclasses
import enum
import sys
from functools import lru_cache
from typing import Any, Dict, Generic, Iterable, List, Optional, Protocol, Set, Tuple, Type, TypeVar, Union

from strawberry import Schema
from strawberry.annotation import StrawberryAnnotation
from strawberry.schema.types import ConcreteType
from strawberry.types import Info

from strawberry_mage.core.strawberry_types import ROOT_NS, StrawberryModelType


class ModuleBoundStrawberryAnnotation(StrawberryAnnotation):
    """A StrawberryAnnotation with lazily evaluated, fixed namespace module passed as an import string."""

    def __init__(self, annotation: Union[str, object], namespace: str = ROOT_NS):
        """
        Create a new annotation.

        :param annotation: the annotation
        :param namespace: import string to use when resolving the annotation
        """
        super().__init__(annotation)
        self._namespace = namespace

    @property
    def namespace(self):
        """
        Namespace used for annotation resolution.

        :return: resolved namespace as a dictionary
        """
        return vars(sys.modules[self._namespace])

    @namespace.setter
    def namespace(self, _):
        """
        Set the namespace used for the type resolution of the annotation.

        :return: None
        """
        return

    @staticmethod
    def from_annotation(other: StrawberryAnnotation):
        """
        Create from an existing StrawberryAnnotation.

        :param other: the original annotation
        :return: new annotation
        """
        return ModuleBoundStrawberryAnnotation(annotation=other.annotation)


class IsDataclass(Protocol):
    """Helper for type hinting dataclasses."""

    __dataclass_fields__: Dict


TEntity = TypeVar("TEntity", bound="IEntityModel")


class GraphQLOperation(enum.Enum):
    """Type of a GraphQL operation."""

    QUERY_ONE = 1
    QUERY_MANY = 2
    CREATE_ONE = 3
    CREATE_MANY = 4
    UPDATE_ONE = 5
    UPDATE_MANY = 6
    DELETE_ONE = 7
    DELETE_MANY = 8


class IDataBackend(abc.ABC, Generic[TEntity]):
    """A data backend for managing the data of associated entity models."""

    @abc.abstractmethod
    def get_strawberry_field_type(self, type_: StrawberryAnnotation) -> Union[Type, str]:
        """
        Resolve the type of a strawberry field annotation.

        :param type_: the annotation
        :return: resolved type
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_attributes(self, model: Type[TEntity], operation: Optional[GraphQLOperation] = None) -> List[str]:
        """
        Get a list of all attribute names of an entity model.

        :param model: model to inspect
        :param operation: optionally, an operation can be specified to limit the fields returned (i.e. for creation)
        :return: list of attribute names
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_attribute_types(self, model: Type[TEntity]) -> Dict[str, Type]:
        """
        Get map of [attribute name, attribute type] for the entity model.

        :param model: model to inspect
        :return: map of attributes and their types
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_attribute_type(self, model: Type[TEntity], attr: str) -> Type:
        """
        Get the type of an attribute.

        :param model: model to inspect
        :param attr: attribute name
        :return: type of the attribute
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_primary_key(self, model: Type[TEntity]) -> Tuple:
        """
        Get the primary key attributes.

        :param model: model to inspect
        :return: tuple of attribute names representing a primary key
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_parent_class_name(self, model: Type[TEntity]) -> Optional[str]:
        """
        Get the name of the parent entity model.

        :param model: model to inspect
        :return: name of the parent class, None if there is none
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_children_class_names(self, model: Type[TEntity]) -> Optional[Set[str]]:
        """
        Get names of all child classes of an entity including the entity itself.

        If there are no child classes, return None
        :param model: model to inspect
        :return: set of (sub)class names
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_operations(self, model: Type[TEntity]) -> Set[GraphQLOperation]:
        """
        All defined graphql operations for an entity model.

        :param model: the model
        :return: operations defined for that model
        """
        return {GraphQLOperation(i) for i in range(1, 9)}

    @abc.abstractmethod
    async def resolve(
        self, model: Type[TEntity], operation: GraphQLOperation, info: Info, data: Any, *args, **kwargs
    ) -> Any:
        """
        Call this to resolve a graphql operation.

        This method is called for every graphql request
        :param model: entity model to resolve on
        :param operation: type of the operation
        :param info: strawberry info
        :param data: incoming data from the query
        :param args: optional arguments
        :param kwargs: optional keyword arguments
        :return: data to return for the graphql field being resolved
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pre_setup(self, models: Iterable[Type[TEntity]]) -> None:
        """
        Do not call manually.

        Callback when all models are registered and initialized after being added.
        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def post_setup(self) -> None:
        """
        Do not call manually.

        Callback when all models are set up and schema is being created.
        :return: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_polymorphic_type(self, base_type: ConcreteType):
        """
        Get a strawberry entity type from a generated base_type.

        Used for resolving interface type from a generated base_type.
        :param base_type: generated type that is to be returned
        :return: the corresponding entity type to return as the type identifier of interface resolver
        """
        raise NotImplementedError


ManagedEntity = TypeVar("ManagedEntity", bound="IEntityModel")


class ISchemaManager(abc.ABC, Generic[ManagedEntity]):
    """Manager class for all entity models and for creating strawberry schema."""

    @property
    @abc.abstractmethod
    def backend(self) -> IDataBackend[ManagedEntity]:
        """
        Get the backend used for the entity models.

        :return: backend
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_schema(self) -> Schema:
        """
        Create a strawberry schema from the managed models.

        :return: Schema
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_models(self) -> List[Type[ManagedEntity]]:
        """
        Get all managed models.

        :return: list of models
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_model_for_name(self, name: str) -> Optional[Type[ManagedEntity]]:
        """
        Try to find a managed model with the given name.

        :param name: name of the model
        :return: model found or None
        """
        raise NotImplementedError


@dataclasses.dataclass
class IEntityModel(abc.ABC):
    """The basic class representing an entity modeled as a graphql object type and used as a resource."""

    __backend__: IDataBackend = dataclasses.field(init=False)
    __primary_key__: Any = dataclasses.field(init=False)
    _strawberry_type: StrawberryModelType = dataclasses.field(init=False)

    @classmethod
    @abc.abstractmethod
    def get_strawberry_type(cls) -> StrawberryModelType:
        """
        Get the strawberry type for a model.

        :return: strawberry type
        """
        raise NotImplementedError

    @classmethod
    @lru_cache
    @abc.abstractmethod
    def get_operations(cls) -> Set[GraphQLOperation]:
        """
        List all operations which are (should be) defined for the model.

        :return: set of operations
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_schema_manager(cls) -> ISchemaManager:
        """
        Get the SchemaManager class holding the entity model.

        :return: schema manager
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_attributes(cls, operation: Optional[GraphQLOperation] = None) -> List[str]:
        """
        Get a list of all attribute names of an entity model.

        :param operation: optionally, an operation can be specified to limit the fields returned (i.e. for creation)
        :return: list of attribute names
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_attribute_types(cls) -> Dict[str, Type]:
        """
        Get map of [attribute name, attribute type] for the entity model.

        :return: map of attributes and their types
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_attribute_type(cls, attr: str) -> Union[Type, str]:
        """
        Get the type of an attribute.

        :param attr: attribute name
        :return: type of the attribute
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_primary_key(cls) -> Tuple[str, ...]:
        """
        Get the primary key tuple.

        :return: tuple of attributes representing a primary key
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_parent_class_name(cls) -> Optional[str]:
        """
        Get the name of the parent entity model.

        :return: name of the parent class, None if there is none
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_children_class_names(cls) -> Optional[Set[str]]:
        """
        Get names of all child classes of an entity including the entity itself.

        If there are no child classes, return None
        :return: set of (sub)class names
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def resolve(cls, operation: GraphQLOperation, info: Info, data: Any, *args, **kwargs) -> Any:
        """
        Call this to resolve a graphql operation.

        This method is called for every graphql request
        :param operation: type of the operation
        :param info: strawberry info
        :param data: incoming data from the query
        :param args: optional arguments
        :param kwargs: optional keyword arguments
        :return: data to return for the graphql field being resolved
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def pre_setup(cls, manager: ISchemaManager) -> None:
        """
        Do not call this manually.

        Called when entity models are being registered in a SchemaManager.
        :return: None
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def post_setup(cls) -> None:
        """
        Do not call this manually.

        Called after all models have been initialized and schema creation is in progress.
        :return: None
        """
        raise NotImplementedError
