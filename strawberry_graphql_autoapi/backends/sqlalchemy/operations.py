import dataclasses
from functools import partial
from typing import List, Type, Any, Union

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.orm import DeclarativeMeta, Session

from strawberry_graphql_autoapi.core.strawberry_types import DeleteResult
from strawberry_graphql_autoapi.core.types import IEntityModel, GraphQLOperation


def _build_pk_query(model: Type[Union[DeclarativeMeta, IEntityModel]], data: Any):
    pk = model.get_primary_key()
    attribute_getter = partial(getattr, data)
    if isinstance(data, dict):
        attribute_getter = data.get
    return and_(*(getattr(model, key) == attribute_getter(key) for key in pk))


def create_(session: Session, model: Type[DeclarativeMeta], data: List[Any]):
    models = [model(**dataclasses.asdict(create_type)) for create_type in data]
    session.add_all(models)
    session.commit()
    [session.refresh(m) for m in models]
    return models


def update_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    input_values = model.get_attributes(GraphQLOperation.CREATE_ONE)
    entities = {en.id: en for en in
                session.execute(
                    select(model)
                        .where(model.id.in_((e._primary_key.id for e in data)))
                ).scalars()}
    for entry in data:
        for column in input_values:
            setattr(entities[entry._primary_key.id], column,
                    getattr(entry, column,
                            getattr(entities[entry._primary_key.id], column)))
    session.add_all(entities.values())
    session.commit()
    [session.refresh(e) for e in entities.values()]
    return entities.values()


def delete_(session: Session, model: Type[Union[DeclarativeMeta, IEntityModel]], data: List[Any]):
    pk_q = or_(
        _build_pk_query(model, {k: getattr(entry._primary_key, k) for k in model.get_primary_key()}) for entry in data)
    statement = delete(model).where(pk_q)
    r = session.execute(statement)
    session.commit()
    return DeleteResult(affected_rows=r.rowcount)


def retrieve_(session: Session, model: Type[DeclarativeMeta], data: Any):
    return session.query(model).get(data._primary_key.id)


def list_(session: Session, model: Type[DeclarativeMeta], data: Any):
    return session.execute(select(model)).scalars()
