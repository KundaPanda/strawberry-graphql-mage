"""Strawberry resolvers common functionality."""
import enum
from functools import cached_property
from typing import List, Optional, cast

from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.field import StrawberryField
from strawberry.types import Info
from strawberry.types.fields.resolver import StrawberryResolver

from strawberry_mage.core.types import (
    ModuleBoundStrawberryAnnotation,
)


class GeneratedType(enum.Enum):
    """Type of a generated entity."""

    ENTITY = ""
    PRIMARY_KEY_INPUT = "PrimaryKey"
    PRIMARY_KEY_FIELD = "PrimaryKeyField"
    QUERY_ONE = "QueryOne"
    QUERY_MANY = "QueryMany"
    QUERY_MANY_INPUT = "QueryManyInput"
    CREATE_ONE = "CreateOne"
    CREATE_MANY = "CreateMany"
    UPDATE_ONE = "UpdateOne"
    UPDATE_MANY = "UpdateMany"
    DELETE_ONE = "DeleteOne"
    DELETE_MANY = "DeleteMany"
    INPUTS = "Inputs"
    FILTER = "Filter"
    ORDERING = "Ordering"
    POLYMORPHIC_BASE = "_"

    def get_typename(self: "GeneratedType", name: str):
        """
        Convert a name to a GeneratedType name based on the enum value.

        :param name: name to convert
        :return: converted name
        """
        return name + self.value

    @staticmethod
    def get_original(name: str):
        """
        Attempt to get the original entity name from a GeneratedType name.

        :param name: a name
        :return: the original one or name if not matched
        """
        for type_ in GeneratedType:
            if type_ != GeneratedType.ENTITY and name.endswith(type_.value):
                return name.rstrip(type_.value)
        return name


class ModuleBoundStrawberryResolver(StrawberryResolver):
    """A StrawberryResolver with lazy evaluation of arguments."""

    @cached_property
    def arguments(self) -> List[StrawberryArgument]:
        """
        Get the arguments for a resolver.

        :return: list of StrawberryArguments
        """
        args: List[StrawberryArgument] = super().arguments  # type: ignore
        return [
            StrawberryArgument(
                a.python_name,
                a.graphql_name,
                ModuleBoundStrawberryAnnotation.from_annotation(a.type_annotation),
                a.is_subscription,
                a.description,
                a.default,
            )
            for a in args
        ]

    @property
    def type_annotation(self) -> Optional[StrawberryAnnotation]:
        """
        Get the type annotation for a resolver.

        :return: Lazily evaluated StrawberryAnnotation
        """
        return (
            ModuleBoundStrawberryAnnotation.from_annotation(cast(StrawberryAnnotation, super().type_annotation))
            if super().type_annotation is not None
            else None
        )


def resolver_nested_select(entity_type: str, field_name: str):
    """
    Create strawberry field resolver for retrieving one entity.

    :param entity_type: entity model name to use for the resolver
    :return: strawberry field resolver
    """
    return_type = List[GeneratedType.ENTITY.get_typename(entity_type)]  # type: ignore

    async def nested_select(
        self, info: Info, page_size: Optional[int] = 30, offset: Optional[int] = 0
    ) -> return_type:  # type: ignore
        return getattr(self, info.field_name)

    resolver = ModuleBoundStrawberryResolver(nested_select)
    return StrawberryField(
        base_resolver=resolver,
        python_name=field_name,
        graphql_name=field_name,
        type_annotation=resolver.type_annotation,
    )
