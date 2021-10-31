"""A basic data backend with some functionality based on dataclasses."""

from functools import lru_cache
from typing import Any, Dict, Generic, Iterable, List, Optional, Set, Tuple, Type, TypeVar, Union

from inflection import underscore
from overrides import overrides
from strawberry.annotation import StrawberryAnnotation
from strawberry.schema.types import ConcreteType
from strawberry.types import Info
from strawberry.types.nodes import InlineFragment

from strawberry_mage.core.type_creator import GeneratedType, defer_annotation
from strawberry_mage.core.types import GraphQLOperation, IDataBackend, IEntityModel
from strawberry_mage.core.utils import get_subclasses

TEntity = TypeVar("TEntity", bound=IEntityModel)


class DataBackendBase(Generic[TEntity], IDataBackend[TEntity]):
    """A basic data backend with some functionality based on dataclasses."""

    def _build_selection(self, field, manager, operation, level=0):
        selection = {}
        for subfield in field.selections:
            if level == 0 and operation == GraphQLOperation.QUERY_MANY:
                return self._build_selection(
                    [f for f in field.selections if f.name == "results"][0], manager, operation, level + 1
                )
            if subfield.selections:
                if isinstance(subfield, InlineFragment):
                    model = manager.get_model_for_name(GeneratedType.get_original(subfield.type_condition))
                    selection[model] = self._build_selection(subfield, manager, operation, level)
                    continue
                selection[underscore(subfield.name)] = self._build_selection(subfield, manager, operation, level + 1)
        return selection

    @overrides
    def get_strawberry_field_type(self, type_: StrawberryAnnotation) -> Union[Type, str]:
        res = defer_annotation(type_)
        return res.annotation if isinstance(res, StrawberryAnnotation) else res

    @lru_cache
    def _get_model_annotations(self, model: Type[TEntity]) -> Dict[str, Type]:
        current = model
        annotations = {}
        while hasattr(current, "__annotations__"):
            annotations.update(current.__annotations__)
            current = current.__mro__[1]
        return {f: self.get_strawberry_field_type(a) for f, a in annotations.items() if not f.startswith("_")}

    @overrides
    def get_attributes(self, model: Type[TEntity], operation: Optional[GraphQLOperation] = None) -> List[str]:
        return [k for k, v in self._get_model_annotations(model).items() if not k.startswith("_")]

    @overrides
    def get_attribute_type(self, model: Type[TEntity], attr: str) -> Type:
        return self._get_model_annotations(model).get(attr)

    @overrides
    def get_attribute_types(self, model: Type[TEntity]) -> Dict[str, Type]:
        return self._get_model_annotations(model)

    @overrides
    def get_primary_key(self, model: Type[TEntity]) -> Tuple:
        return model.__primary_key__

    @overrides
    def get_parent_class_name(self, model: Type[TEntity]) -> Optional[str]:
        if model.mro()[1] != TEntity:
            return model.mro()[1].__name__

    @overrides
    def get_children_class_names(self, model: Type[TEntity]) -> Optional[Set[str]]:
        if model.__subclasses__():
            return set(m.__name__ for m in get_subclasses(model)).union({model.__name__})
        return None

    @overrides
    def get_operations(self, model: Type[TEntity]) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    @overrides
    def get_polymorphic_type(self, base_type: ConcreteType):
        return base_type.implementation

    @overrides
    async def resolve(
        self,
        model: Type[TEntity],
        operation: GraphQLOperation,
        info: Info,
        data: Any,
        *args,
        dataset: Optional[Iterable[TEntity]],
        **kwargs
    ) -> Any:
        if operation.value % 2 == 0:
            return []
        return None

    @overrides
    def pre_setup(self, models: Iterable[Type[TEntity]]) -> None:
        pass

    @overrides
    def post_setup(self) -> None:
        pass
