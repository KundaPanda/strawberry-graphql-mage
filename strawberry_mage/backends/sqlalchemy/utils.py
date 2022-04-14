"""Utilities for creating sqlalchemy models."""

from typing import List, Optional, Tuple, Type, Union

from inflection import underscore
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql.type_api import TypeEngine

from strawberry_mage.backends.sqlalchemy.types import SqlAlchemyModel


def make_fk(
        remote: Union[str, Type[SqlAlchemyModel]],
        foreign_key_type: Type[TypeEngine] = Integer,
        remote_pk="id",
        nullable=True,
        back_populates=None,
        backref=None,
        foreign_kwargs=None,
        rel_kwargs=None,
        use_alter=False,
) -> Tuple[Column, relationship]:
    """
    Create a foreign key for remote model on one column.

    :param remote: the model which the foreign key points to
    :param foreign_key_type: type of the foreign key column, defaults to Integer
    :param remote_pk: the name of the remote attribute used for foreign key
    :param nullable: is nullable
    :param back_populates: relationship backpopulates argument
    :param backref: relationship backref argument
    :param foreign_kwargs: kwargs passed to ForeignKey
    :param rel_kwargs: kwargs passed to relationship
    :param use_alter: use_alter from sqlalchemy
    :return: tuple [created foreign key, relationship]
    """
    if not isinstance(remote, str):
        remote = remote.__name__
    if foreign_kwargs is None:
        foreign_kwargs = {}
    if rel_kwargs is None:
        rel_kwargs = {}
    remote_table = underscore(remote)
    foreign_key = Column(
        foreign_key_type,
        ForeignKey(f"{remote_table}.{remote_pk}", use_alter=use_alter),
        nullable=nullable,
        **foreign_kwargs,
    )
    rel = relationship(remote, back_populates=back_populates, backref=backref, foreign_keys=[foreign_key], **rel_kwargs)
    return foreign_key, rel


def make_composite_fk(
        remote: Union[str, Type[SqlAlchemyModel]],
        remote_keys: Tuple[str, ...],
        model_name: str,
        rel_name: str,
        remote_key_types: Optional[Tuple[Type[TypeEngine], ...]] = None,
        nullable=True,
        back_populates=None,
        backref=None,
        foreign_kwargs=None,
        rel_kwargs=None,
        use_alter=False,
) -> Tuple[List[Tuple[str, Column]], relationship, ForeignKeyConstraint]:
    """
    Create a composite foreign key for remote model.

    :param remote: the model which the foreign keys point to
    :param remote_keys: tuple of remote attributes used as foreign keys
    :param model_name: name of the model which will hold the foreign keys
    :param rel_name: name of the relation on the model
    :param remote_key_types: types of foreign key columns, defaults to integers
    :param nullable: is nullable
    :param back_populates: relationship backpopulates argument
    :param backref: relationship backref argument
    :param foreign_kwargs: kwargs passed to ForeignKey
    :param rel_kwargs: kwargs passed to relationship
    :param use_alter: use_alter from sqlalchemy
    :return: tuple [created foreign keys, relationship, foreign key constraint]
    """
    if remote_key_types is None:
        remote_key_types = tuple(Integer for _ in range(len(remote_keys)))
    if not isinstance(remote, str):
        remote = remote.__name__
    if foreign_kwargs is None:
        foreign_kwargs = {}
    if rel_kwargs is None:
        rel_kwargs = {}
    if len(remote_key_types) != len(remote_keys):
        raise AttributeError("Length of remote key types and remote keys must match!")
    remote_table = underscore(remote)
    foreign_keys = []
    for i, key in enumerate(remote_keys):
        foreign_keys.append(
            (
                key,
                Column(f"{rel_name}_{key}", remote_key_types[i], nullable=nullable, **foreign_kwargs),
            )
        )
    rel = relationship(
        remote,
        back_populates=back_populates,
        backref=backref,
        foreign_keys=[f[1] for f in foreign_keys],
        primaryjoin=f'and_({",".join(f"{model_name}.{f[1]} == {remote}.{f[0]}" for f in foreign_keys)})',
        **rel_kwargs,
    )
    constraint = ForeignKeyConstraint(
        tuple(f"{rel_name}_{f[0]}" for f in foreign_keys),
        [f"{remote_table}.{f[0]}" for f in foreign_keys],
        use_alter=use_alter,
    )
    return foreign_keys, rel, constraint
