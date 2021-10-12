from typing import Union, Tuple, Type

from inflection import underscore
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, DeclarativeMeta


def make_fk(remote: Union[str, Type[DeclarativeMeta]], remote_pk='id', optional=False, back_populates=None,
            foreign_kwargs=None, rel_kwargs=None) -> Tuple[Column, relationship]:
    if not isinstance(remote, str):
        remote = remote.__tablename__
    if foreign_kwargs is None:
        foreign_kwargs = {}
    if rel_kwargs is None:
        rel_kwargs = {}
    remote_table = underscore(remote)
    fk = Column(Integer, ForeignKey(f'{remote_table}.{remote_pk}'), nullable=optional, **foreign_kwargs)
    rel = relationship(remote, back_populates=back_populates, foreign_keys=[fk], **rel_kwargs)
    return fk, rel
