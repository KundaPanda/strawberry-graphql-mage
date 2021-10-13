from abc import ABC
from functools import lru_cache
from typing import Type, Iterable, Any, Tuple, Set, Dict, Optional, List

from inflection import underscore
from strawberry.annotation import StrawberryAnnotation
from strawberry.types import Info
from strawberry.types.nodes import InlineFragment

from strawberry_mage.core.models import EntityModel
from strawberry_mage.core.type_creator import defer_annotation
from strawberry_mage.core.types import GraphQLOperation, IDataBackend, IEntityModel
from strawberry_mage.core.utils import get_subclasses


class DataBackendBase(IDataBackend, ABC):
    def _build_selection(self, field, manager):
        selection = {}
        for subfield in field.selections:
            if subfield.selections:
                if isinstance(subfield, InlineFragment):
                    selection[manager.get_model_for_name(subfield.type_condition)] = \
                        self._build_selection(subfield, manager)
                    continue
                selection[underscore(subfield.name)] = self._build_selection(subfield, manager)
        return selection

    def register_model(self, model: Type[IEntityModel]):
        model.__backend__ = self

    def get_strawberry_field_type(self, type_: Any) -> Type:
        res = defer_annotation(type_)
        return res.annotation if isinstance(res, StrawberryAnnotation) else res


class DummyDataBackend(DataBackendBase):
    @lru_cache
    def _get_model_annotations(self, model: Type[IEntityModel]) -> Dict[str, Type]:
        current = model
        annotations = {}
        while hasattr(current, '__annotations__'):
            annotations.update(current.__annotations__)
            current = current.mro()[1]
        return {f: self.get_strawberry_field_type(a) for f, a in annotations.items() if not f.startswith('_')}

    def get_attributes(self, model: Type[IEntityModel], operation: Optional[GraphQLOperation] = None) -> Iterable[Any]:
        return [k for k, v in self._get_model_annotations(model).items() if not k.startswith('_')]

    def get_attribute_type(self, model: Type[IEntityModel], attr: str) -> Type:
        return self._get_model_annotations(model).get(attr)

    def get_attribute_types(self, model: Type[IEntityModel]) -> Dict[str, Type]:
        return self._get_model_annotations(model)

    def get_primary_key(self, model: Type[IEntityModel]) -> Tuple:
        return model.__primary_key__

    def get_parent_class_name(self, model: Type['IEntityModel']) -> Optional[str]:
        if model.mro()[1] != EntityModel:
            return model.mro()[1].__name__

    def get_children_class_names(self, model: Type['IEntityModel']) -> Optional[List[str]]:
        if model.__subclasses__():
            return get_subclasses(model)

    def get_operations(self, model: Type[IEntityModel]) -> Set[GraphQLOperation]:
        return {GraphQLOperation(i) for i in range(1, 9)}

    async def resolve(self, model: Type[IEntityModel], operation: GraphQLOperation, info: Info, data: Any) -> Any:
        if operation.value % 2 == 0:
            return []
        return None

    def pre_setup(self, models: Iterable[Type['IEntityModel']]) -> None:
        pass

    def post_setup(self) -> None:
        pass
