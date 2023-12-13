"""
Base classes for messages.
"""


from __future__ import annotations
from typing import Any
from dataclasses import dataclass


class Message:
    """
    Base class for messages.
    """
    pass


@dataclass(frozen=True)
class PayloadMessage(Message):
    """
    A message with an arbitrary payload.
    """
    payload: Any
    """The payload."""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.payload})"
