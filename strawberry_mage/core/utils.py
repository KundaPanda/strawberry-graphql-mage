"""Utilities :)."""

from typing import Set, Type


def get_subclasses(cls: Type) -> Set[Type]:
    """
    Get all (recursive) subclasses of a class.

    :param cls: class to inspect
    :return: list of subclasses
    """
    return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in get_subclasses(c)])
