"""
Utility classes for logging.
"""


from __future__ import annotations
from typing import Optional, TextIO
from numbers import Number

import sys


class Logger:
    """
    A logger that does nothing. This class can be used directly or as a base
    for other logger classes.
    """

    def header(self) -> None:
        """Do not print a header."""
        pass

    def log(self, now: Number, ident: int, event: str, detail: str) -> None:
        """Do not log."""
        pass


class PrintLogger(Logger):
    """A logger that prints to a stream."""

    def __init__(self, out: Optional[TextIO]=None):
        """
        Constructs a `PrintLogger` that prints to `out` (by default `sys.stdout`).
        """
        if out is None:
            out = sys.stdout
        self.out = out

    def header(self) -> None:
        """Print a table header."""
        print()
        print(" Time | Node | Event      | Detail", file=self.out)

    def log(self, now: Number, ident: int, event: str, detail: str) -> None:
        """Print a log line."""
        print(f"{now:5d} | {ident:4d} | {event:10} | {detail}", file=self.out)
