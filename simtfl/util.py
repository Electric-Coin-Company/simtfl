"""
Utilities.
"""


from __future__ import annotations
from typing import Generator, TypeAlias

from simpy import Event


ProcessEffect: TypeAlias = Generator[Event, None, None]

def skip() -> ProcessEffect:
    """
    (process) Does nothing.
    """
    # Make this a generator.
    yield from []


class Unique:
    """
    Represents a unique value.

    Instances of this class are hashable. When subclassing as a dataclass, use
    `@dataclass(eq=False)` to preserve hashability.
    """
    def __eq__(self, other: Unique):
        return self == other

    def __hash__(self) -> int:
        return id(self)
