"""
Utilities.
"""


def skip():
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
    def __eq__(self, other):
        return self == other

    def __hash__(self):
        return id(self)
