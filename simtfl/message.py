from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PayloadMessage:
    """
    A message with an arbitrary payload.
    """
    payload: Any
