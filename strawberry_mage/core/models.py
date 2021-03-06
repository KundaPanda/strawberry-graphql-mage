"""Basic entity model."""

import dataclasses
from collections.abc import Hashable
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from overrides import overrides
from strawberry.types import Info

from strawberry_mage.core.resolvers.resolvers import (
    resolver_create_many,
    resolver_create_one,
    resolver_delete_many,
    resolver_delete_one,
    resolver_query_many,
    resolver_query_one,
    resolver_update_many,
    resolver_update_one,
)
from strawberry_mage.core.strawberry_types import StrawberryModelType
from strawberry_mage.core.type_creator import (
    create_entity_type,
    create_filter_input,
    create_input_types,
    create_ordering_input,
    create_query_many_output,
)
from strawberry_mage.core.types import (
    GraphQLOperation,
    IDataBackend,
    IEntityModel,
    ISchemaManager,
)


@dataclasses.dataclass
class EntityModel(IEntityModel):
    """The basic entity model."""

    _strawberry_type: StrawberryModelType = dataclasses.field(init=False)
    _properties: List[str] = dataclasses.field(init=False, default_factory=lambda: [])
    _manager: ISchemaManager = dataclasses.field(init=False)
    __backend__: IDataBackend = dataclasses.field(init=False)
    __primary_key__: Any = dataclasses.field(init=False)
    __primary_key_autogenerated__: bool = dataclasses.field(init=False, default=True)

    def __hash__(self):
        """
        Hash to be used only when immutability is guaranteed.

        :return: hash
        """
        return hash(
            (
                self.__class__.__name__,
                *[
                    getattr(self, a, "") if isinstance(getattr(self, a, ""), Hashable) else dataclasses.MISSING
                    for a in self.get_attributes()
                ],
            )
        )

    @classmethod
    @overrides
    def get_strawberry_type(cls) -> StrawberryModelType:
        return cls._strawberry_type

    @classmethod
    @overrides
    def get_primary_key(cls) -> Tuple[str, ...]:
        return cls.__backend__.get_primary_key(cls)

    @classmethod
    @overrides
    def get_operations(cls) -> Set[GraphQLOperation]:
        return cls.__backend__.get_operations(cls)

    @classmethod
    @overrides
    def get_attributes(cls, operation: Optional[GraphQLOperation] = None) -> List[str]:
        return cls.__backend__.get_attributes(cls, operation)

    @classmethod
    @overrides
    def get_attribute_types(cls) -> Dict[str, Type]:
        return cls.__backend__.get_attribute_types(cls)

    @classmethod
    @overrides
    def get_attribute_type(cls, attr: str) -> Type:
        return cls.__backend__.get_attribute_type(cls, attr)

    @classmethod
    @overrides
    def get_schema_manager(cls) -> ISchemaManager:
        return cls._manager

    @classmethod
    @overrides
    def get_parent_class_name(cls) -> Optional[str]:
        return cls.__backend__.get_parent_class_name(cls)

    @classmethod
    @overrides
    def get_children_class_names(cls) -> Optional[Set[str]]:
        return cls.__backend__.get_children_class_names(cls)

    @classmethod
    @overrides
    async def resolve(cls, operation: GraphQLOperation, info: Info, data: Any, *args, **kwargs):
        return await cls.__backend__.resolve(cls, operation, info, data, *args, **kwargs)

    @classmethod
    @overrides
    def pre_setup(cls, manager):
        cls._manager = manager
        cls._properties = cls.__backend__.get_attributes(cls)
        base_entity, entity = create_entity_type(cls)
        cls._strawberry_type = StrawberryModelType(
            base_entity=base_entity,
            entity=entity,
            filter=create_filter_input(cls),
            ordering=create_ordering_input(cls),
            query_many_output=create_query_many_output(cls),
        )
        cls._strawberry_type.input_types = create_input_types(cls)
        cls._strawberry_type.query_one = resolver_query_one(cls)
        cls._strawberry_type.query_many = resolver_query_many(cls)
        cls._strawberry_type.create_one = resolver_create_one(cls)
        cls._strawberry_type.create_many = resolver_create_many(cls)
        cls._strawberry_type.update_one = resolver_update_one(cls)
        cls._strawberry_type.update_many = resolver_update_many(cls)
        cls._strawberry_type.delete_one = resolver_delete_one(cls)
        cls._strawberry_type.delete_many = resolver_delete_many(cls)
        return cls

    @classmethod
    @overrides
    def post_setup(cls) -> None:
        pass
