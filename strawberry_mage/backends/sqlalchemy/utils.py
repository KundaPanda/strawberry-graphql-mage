"""Utilities for creating sqlalchemy models."""

from typing import List, Tuple, Type, Union

from inflection import underscore
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer
from sqlalchemy.orm import relationship

from strawberry_mage.backends.sqlalchemy.types import SqlAlchemyModel


def make_fk(
    remote: Union[str, Type[SqlAlchemyModel]],
    remote_pk="id",
    optional=False,
    back_populates=None,
    foreign_kwargs=None,
    rel_kwargs=None,
) -> Tuple[Column, relationship]:
    """
    Create a foreign key for remote model on one column.

    :param remote: the model which the foreign key points to
    :param remote_pk: the name of the remote attribute used for foreign key
    :param optional: is optional
    :param back_populates: relationship backpopulates argument
    :param foreign_kwargs: kwargs passed to ForeignKey
    :param rel_kwargs: kwargs passed to relationship
    :return: tuple [created foreign key, relationship]
    """
    if not isinstance(remote, str):
        remote = str(remote.__tablename__)
    if foreign_kwargs is None:
        foreign_kwargs = {}
    if rel_kwargs is None:
        rel_kwargs = {}
    remote_table = underscore(remote)
    fk = Column(
        Integer,
        ForeignKey(f"{remote_table}.{remote_pk}", use_alter=True),
        nullable=optional,
        **foreign_kwargs,
    )
    rel = relationship(remote, back_populates=back_populates, foreign_keys=[fk], **rel_kwargs)
    return fk, rel


def make_composite_fk(
    remote: Union[str, Type[SqlAlchemyModel]],
    remote_keys: Tuple[str, ...],
    model_name: str,
    rel_name: str,
    optional=False,
    back_populates=None,
    foreign_kwargs=None,
    rel_kwargs=None,
) -> Tuple[List[Tuple[str, Column]], relationship, ForeignKeyConstraint]:
    """
    Create a composite foreign key for remote model.

    :param remote: the model which the foreign keys point to
    :param remote_keys: tuple of remote attributes used as foreign keys
    :param model_name: name of the model which will hold the foreign keys
    :param rel_name: name of the relation on the model
    :param optional: is optional
    :param back_populates: relationship backpopulates argument
    :param foreign_kwargs: kwargs passed to ForeignKey
    :param rel_kwargs: kwargs passed to relationship
    :return: tuple [created foreign keys, relationship, foreign key constraint]
    """
    if not isinstance(remote, str):
        remote = remote.__tablename__
    if foreign_kwargs is None:
        foreign_kwargs = {}
    if rel_kwargs is None:
        rel_kwargs = {}
    remote_table = underscore(remote)
    foreign_keys = []
    for key in remote_keys:
        foreign_keys.append(
            (
                key,
                Column(f"{rel_name}_{key}", Integer, nullable=optional, **foreign_kwargs),
            )
        )
    rel = relationship(
        remote,
        back_populates=back_populates,
        foreign_keys=[f[1] for f in foreign_keys],
        primaryjoin=f'and_({",".join(f"{model_name}.{f[1]} == {remote}.{f[0]}" for f in foreign_keys)})',
        **rel_kwargs,
    )
    constraint = ForeignKeyConstraint(
        tuple(f"{rel_name}_{f[0]}" for f in foreign_keys),
        [f"{remote_table}.{f[0]}" for f in foreign_keys],
        use_alter=True,
    )
    return foreign_keys, rel, constraint
