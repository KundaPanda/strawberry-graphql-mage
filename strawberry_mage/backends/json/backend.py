import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Type

from strawberry.types import Info

from strawberry_mage.backends.python.backend import PythonBackend
from strawberry_mage.backends.python.models import PythonEntityModel
from strawberry_mage.backends.sqlalchemy.models import _SQLAlchemyModel
from strawberry_mage.core.types import GraphQLOperation


class JSONBackend(PythonBackend):
    dataset: List[_SQLAlchemyModel] = []
    _model: Type[PythonEntityModel] = None
    _model_mapper: Callable[[dict], Type[PythonEntityModel]] = None

    def __create_entity(self, mappings: Dict[str, _SQLAlchemyModel], original: dict):
        data = self.__extract_attributes(mappings, original)
        model = self._model if self._model else self._model_mapper(original)
        attrs = set(model.get_attributes())
        return model.get_sqla_model()(
            **{k: data[k] for k in set(data.keys()).intersection(attrs)}
        )

    def __extract_attributes(self, mappings: Dict[str, _SQLAlchemyModel], entry: dict):
        results: Dict[str, Any] = {}
        for a, attr in entry.items():
            if attr and isinstance(attr, dict):
                key = self._get_entry_key(attr)
                if key not in mappings:
                    mappings[key] = self.__create_entity(mappings, attr)
                results[a] = mappings[key]
            elif isinstance(attr, list):
                converted = []
                for e in attr:
                    if isinstance(e, dict):
                        key = self._get_entry_key(e)
                        if key not in mappings:
                            mappings[key] = self.__create_entity(mappings, e)
                        converted.append(mappings[key])
                    else:
                        converted.append(e)
                results[a] = converted
            else:
                results[a] = attr
        return results

    def _get_entry_key(self, entry: dict):
        model = self._model if self._model else self._model_mapper(entry)
        return json.dumps(
            {
                "__model__": model.__name__,
                **{k: entry.get(k, None) for k in model.get_primary_key()},
            }
        )

    def __build_dataset(self, dataset: Iterable[dict]):
        mappings: Dict[str, _SQLAlchemyModel] = {}
        for entry in dataset:
            key = self._get_entry_key(entry)
            entity = self.__create_entity(mappings, entry)
            mappings[key] = entity
        return mappings

    def add_dataset(
        self,
        dataset: Iterable[dict],
        model: Optional[Type[PythonEntityModel]] = None,
        model_mapper: Callable[[dict], Type[PythonEntityModel]] = None,
    ):
        if not model and not model_mapper:
            raise Exception(
                'Either "model" or "model_mapper" need to be specified when using JSONBackend'
            )
        self._model = model
        self._model_mapper = model_mapper
        self.dataset = list(self.__build_dataset(dataset).values())

    def _remove_pks(self, model, attrs):
        return [a for a in attrs if a not in self.get_primary_key(model)]

    async def resolve(
        self,
        model: Type[PythonEntityModel],
        operation: GraphQLOperation,
        info: Info,
        data: Any,
        *args,
        dataset: Optional[Iterable] = None,
        **kwargs
    ) -> Any:
        return await super().resolve(model, operation, info, data, dataset)
