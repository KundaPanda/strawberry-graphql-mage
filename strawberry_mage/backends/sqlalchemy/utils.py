"""Utilities for creating sqlalchemy models."""
from typing import Optional, Tuple, Type, Union

from inflection import underscore
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql.type_api import TypeEngine

from strawberry_mage.backends.sqlalchemy.models import SQLAlchemyModel


def make_fk(
    remote: Union[str, Type[SQLAlchemyModel]],
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
    remote: Union[str, Type[SQLAlchemyModel]],
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
) -> Type:
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
    :return: class to be used as a mixin for the model
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

    def init_mixin_base(cls, *args):
        if hasattr(cls, rel_name):
            return
        cls.__table_args__ = getattr(cls, "__table_args__", tuple()) + (constraint,)
        for k, col in foreign_keys:
            setattr(cls, col.name, col)
        setattr(cls, rel_name, rel)

    mixin = type(f"{model_name}_{rel_name}_mixin", (), {"__init_subclass__": init_mixin_base})
    return mixin


def make_m2m(
    base_class: Type[SQLAlchemyModel],
    first: str,
    second: str,
    first_pk="id",
    second_pk="id",
    first_type: Type[TypeEngine] = Integer,
    second_type: Type[TypeEngine] = Integer,
) -> Table:
    """
    Create an M2M table for two models.

    :param base_class: The base class for sqlalchemy models
    :param first: Name of the first model
    :param second: Name of the second model
    :param first_pk: Column name in the first model to use in m2m relation
    :param second_pk: Column name in the second model to use in m2m relation
    :param first_type: Type of the first column, defaults to Integer
    :param second_type: Type of the second column, defaults to Integer
    :return: A table for the m2m relation
    """
    first_name = underscore(first)
    second_name = underscore(second)
    return Table(
        f"{first_name}_{second_name}_m2m",
        base_class.metadata,
        Column(f"{first_name}_{first_pk}", first_type, ForeignKey(f"{first_name}.{first_pk}"), primary_key=True),
        Column(
            f'{second_name + "2" if second_name == first_name else second_name}_{second_pk}',
            second_type,
            ForeignKey(f"{second_name}.{second_pk}"),
            primary_key=True,
        ),
    )
