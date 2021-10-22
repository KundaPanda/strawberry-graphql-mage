from typing import Type, Set


def get_subclasses(cls: Type) -> Set[Type]:
    return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in get_subclasses(c)])
