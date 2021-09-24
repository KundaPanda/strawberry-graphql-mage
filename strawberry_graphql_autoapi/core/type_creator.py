import enum
import enum
import sys
from inspect import isclass
from typing import Type, ForwardRef, Any, List, Optional, Dict, Union

import strawberry
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import UNSET
from strawberry.field import StrawberryField
from strawberry.scalars import is_scalar, SCALAR_TYPES
from strawberry.utils.typing import is_optional

from strawberry_graphql_autoapi.core.strawberry_types import QueryOne, PrimaryKeyInput, ROOT_NS, EntityType, \
    StrawberryModelInputTypes, QueryMany, ObjectOrdering, ObjectFilter, SCALAR_FILTERS, \
    OrderingDirection
from strawberry_graphql_autoapi.core.types import IEntityModel, ModuleBoundStrawberryAnnotation, GraphQLOperation


class GeneratedType(enum.Enum):
    ENTITY = ''
    PRIMARY_KEY_INPUT = 'PrimaryKey'
    PRIMARY_KEY_FIELD = 'PrimaryKeyField'
    QUERY_ONE = 'QueryOne'
    QUERY_MANY = 'QueryMany'
    CREATE_ONE = 'CreateOne'
    CREATE_MANY = 'CreateMany'
    UPDATE_ONE = 'UpdateOne'
    UPDATE_MANY = 'UpdateMany'
    DELETE_ONE = 'DeleteOne'
    DELETE_MANY = 'DeleteMany'
    INPUTS = 'Inputs'
    FILTER = 'Filter'
    ORDERING = 'Ordering'

    def get_typename(self: 'GeneratedType', name: str):
        return name + self.value


def _create_fields(fields: Dict[str, Any], target_type: GeneratedType = GeneratedType.ENTITY) -> Dict[str, Any]:
    strawberry_fields = {
        f: StrawberryField(f, type_annotation=defer_annotation(a, target_type), default_factory=lambda: UNSET,
                           default=UNSET)
        for f, a in fields.items()}
    return {
        **strawberry_fields,
        '__annotations__': {
            f: a.type_annotation for f, a in strawberry_fields.items()
        }
    }


def strip_typename(type_: Union[str, Type]) -> Union[str, Type]:
    while hasattr(type_, '__args__'):
        type_ = type_.__args__[0]
    if isinstance(type_, str):
        return type_
    if isinstance(type_, ForwardRef):
        return type_.__forward_arg__
    if type_ in SCALAR_TYPES:
        return type_
    return type_.__name__


def _apply_type_rename(name: str, target_type: GeneratedType):
    if not any((t != GeneratedType.ENTITY and name.endswith(t.value) for t in GeneratedType)):
        return target_type.get_typename(name)
    return name


def defer_annotation(annotation, target_type: GeneratedType = GeneratedType.ENTITY) \
        -> Union[Type, ModuleBoundStrawberryAnnotation]:
    if annotation is type(None):
        return annotation
    if isinstance(annotation, ForwardRef):
        return defer_annotation(annotation.__forward_arg__, target_type)
    if isclass(annotation) and hasattr(annotation, '__annotations__'):
        return ModuleBoundStrawberryAnnotation(_apply_type_rename(annotation.__name__, target_type))
    if isinstance(annotation, str):
        return ModuleBoundStrawberryAnnotation(_apply_type_rename(annotation, target_type))
    if isinstance(annotation, ModuleBoundStrawberryAnnotation):
        return defer_annotation(annotation.annotation, target_type)
    if hasattr(annotation, '__args__'):
        deferred_args = [defer_annotation(arg, target_type) for arg in annotation.__args__]
        # TODO: UGLY
        new_annotation = ModuleBoundStrawberryAnnotation(annotation.__reduce__()[1][0][
                                                             (*(a.annotation
                                                                if isinstance(a, StrawberryAnnotation)
                                                                else a
                                                                for a in deferred_args),)
                                                         ])
        return new_annotation
    return annotation


def create_enum_type(attr: enum.EnumMeta):
    enum_type = strawberry.enum(attr)
    enum_filter_type = strawberry.input(type(GeneratedType.FILTER.get_typename(attr.__name__), (),
                                             _create_fields({'exact': enum_type, })))
    values = [e.name for e in attr]
    enum_ordering_type = strawberry.input(type(GeneratedType.ORDERING.get_typename(attr.__name__), (),
                                               _create_fields({k: OrderingDirection for k in values})))

    setattr(sys.modules[ROOT_NS], enum_type.__name__, enum_type)
    enum_type.__module__ = ROOT_NS

    setattr(sys.modules[ROOT_NS], enum_filter_type.__name__, enum_filter_type)
    enum_filter_type.__module__ = ROOT_NS

    setattr(sys.modules[ROOT_NS], enum_ordering_type.__name__, enum_ordering_type)
    enum_ordering_type.__module__ = ROOT_NS

    return enum_type, enum_filter_type, enum_ordering_type


def create_entity_type(model: Type[IEntityModel]) -> Type[EntityType]:
    attrs = model.get_attribute_types()

    for name in attrs.keys():
        attr = attrs[name]
        if isclass(attr) and isinstance(attr, enum.EnumMeta):
            enum_type, _, _ = create_enum_type(attr)
            attrs[name] = enum_type

    type_object = type(model.__name__, (EntityType,), _create_fields(attrs))
    type_ = strawberry.type(type_object)

    setattr(sys.modules[ROOT_NS], model.__name__, type_)
    type_.__module__ = ROOT_NS

    return type_


def create_input_types(model: Type[IEntityModel]) -> StrawberryModelInputTypes:
    input_types = strawberry.input(
        type(GeneratedType.INPUTS.get_typename(model.__name__), (StrawberryModelInputTypes,), _create_fields({
            'primary_key_field': create_primary_key_field(model),
            'query_one_input': create_query_one_input(model),
            'query_many_input': create_query_many_input(model),
            'create_one_input': create_create_one_input(model),
            'update_one_input': create_update_one_input(model),
        }))
    )
    setattr(sys.modules[ROOT_NS], input_types.__name__, input_types)
    input_types.__module__ = ROOT_NS

    return input_types


def create_ordering_input(model: Type[IEntityModel]) -> Type[ObjectOrdering]:
    ordering = strawberry.input(type(GeneratedType.ORDERING.get_typename(model.__name__), (ObjectOrdering,),
                                     _create_fields({
                                         k: get_ordering_type(Optional[model.get_attribute_type(k)])
                                         for k in model.get_attributes(GraphQLOperation.QUERY_MANY)
                                     })))

    setattr(sys.modules[ROOT_NS], ordering.__name__, ordering)
    ordering.__module__ = ROOT_NS

    return ordering


def create_filter_input(model: Type[IEntityModel]) -> Type[ObjectFilter]:
    filter_ = strawberry.input(type(GeneratedType.FILTER.get_typename(model.__name__), (ObjectFilter,),
                                    _create_fields({
                                        'AND_': Optional[
                                            List[Optional[GeneratedType.FILTER.get_typename(model.__name__)]]],
                                        'OR_': Optional[
                                            List[Optional[GeneratedType.FILTER.get_typename(model.__name__)]]],
                                        **{k: get_filter_type(Optional[model.get_attribute_type(k)]) for k in
                                           model.get_attributes(GraphQLOperation.QUERY_MANY)}
                                    })))

    setattr(sys.modules[ROOT_NS], filter_.__name__, filter_)
    filter_.__module__ = ROOT_NS

    return filter_


def create_primary_key_input(model: Type[IEntityModel]) -> Type[PrimaryKeyInput]:
    input_type = strawberry.input(type(GeneratedType.PRIMARY_KEY_INPUT.get_typename(model.__name__), (PrimaryKeyInput,),
                                       _create_fields({
                                           k: model.get_attribute_type(k) for k in model.get_primary_key()
                                       })))
    setattr(sys.modules[ROOT_NS], input_type.__name__, input_type)
    input_type.__module__ = ROOT_NS

    return input_type


def create_primary_key_field(model: Type[IEntityModel]) -> Type:
    pk_field = strawberry.input(type(GeneratedType.PRIMARY_KEY_FIELD.get_typename(model.__name__), (EntityType,),
                                     _create_fields({
                                         'primary_key_': create_primary_key_input(model),
                                     }, GeneratedType.PRIMARY_KEY_FIELD)))

    setattr(sys.modules[ROOT_NS], pk_field.__name__, pk_field)
    pk_field.__module__ = ROOT_NS

    return pk_field


def create_query_one_input(model: Type[IEntityModel]) -> Type[QueryOne]:
    query_one = strawberry.input(type(GeneratedType.QUERY_ONE.get_typename(model.__name__), (QueryOne,),
                                      _create_fields(
                                          {
                                              'primary_key_': GeneratedType.PRIMARY_KEY_INPUT.get_typename(
                                                  model.__name__)
                                          })))

    setattr(sys.modules[ROOT_NS], query_one.__name__, query_one)
    query_one.__module__ = ROOT_NS

    return query_one


def create_query_many_input(model: Type[IEntityModel]) -> Type[QueryMany]:
    query_many = strawberry.input(type(GeneratedType.QUERY_MANY.get_typename(model.__name__), (QueryMany,),
                                       _create_fields({
                                           'ordering': Optional[
                                               List[Optional[GeneratedType.ORDERING.get_typename(model.__name__)]]],
                                           'filters': Optional[
                                               List[Optional[GeneratedType.FILTER.get_typename(model.__name__)]]],
                                       })))

    setattr(sys.modules[ROOT_NS], query_many.__name__, query_many)
    query_many.__module__ = ROOT_NS

    return query_many


def create_create_one_input(model: Type[IEntityModel]) -> Type[EntityType]:
    fields = {
        f: model.get_attribute_type(f)
        for f in model.get_attributes(GraphQLOperation.CREATE_ONE)
    }
    create_one = strawberry.input(type(GeneratedType.CREATE_ONE.get_typename(model.__name__), (EntityType,),
                                       _create_fields(fields, GeneratedType.PRIMARY_KEY_FIELD)))

    setattr(sys.modules[ROOT_NS], create_one.__name__, create_one)
    create_one.__module__ = ROOT_NS

    return create_one


def create_update_one_input(model: Type[IEntityModel]) -> Type[EntityType]:
    update_one = strawberry.input(type(GeneratedType.UPDATE_ONE.get_typename(model.__name__), (EntityType,),
                                       _create_fields({
                                           'primary_key_': GeneratedType.PRIMARY_KEY_INPUT.get_typename(
                                               model.__name__),
                                           **{f: Optional[model.get_attribute_type(f)]
                                              for f in model.get_attributes(GraphQLOperation.UPDATE_ONE)}
                                       }, GeneratedType.PRIMARY_KEY_FIELD)))

    setattr(sys.modules[ROOT_NS], update_one.__name__, update_one)
    update_one.__module__ = ROOT_NS

    return update_one


def get_ordering_type(type_: Any):
    if type_ is type(None):
        raise AttributeError('Should not be NoneType')
    if is_scalar(type_):
        return OrderingDirection
    if is_optional(type_):
        order_type = get_ordering_type(type_.__args__[0])
        if isinstance(order_type, StrawberryAnnotation):
            order_type.annotation = Optional[order_type.annotation]
            return order_type
        return Optional[order_type]
    return defer_annotation(type_, GeneratedType.ORDERING)


def get_filter_type(type_: Any):
    if type_ is type(None):
        return type_
    if is_scalar(type_):
        return SCALAR_FILTERS[type_]
    if is_optional(type_):
        filter_type = get_filter_type(type_.__args__[0])
        if isinstance(filter_type, StrawberryAnnotation):
            filter_type.annotation = Optional[filter_type.annotation]
            return filter_type
        return Optional[filter_type]
    return defer_annotation(type_, GeneratedType.FILTER)
