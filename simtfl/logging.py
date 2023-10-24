"""
Utility classes for logging.
"""

import sys


class NullLogger:
    """A logger that does nothing."""

    def header(self):
        """Do not print a header."""
        pass

    def log(self, now, ident, event, detail):
        """Do not log."""
        pass


class PrintLogger:
    """A logger that prints to a stream."""
    def __init__(self, out=None):
        """
        Constructs a `PrintLogger` that prints to `out` (by default `sys.stdout`).
        """
        if out is None:
            out = sys.stdout
        self.out = out

    def header(self):
        """Print a table header."""
        print()
        print(" Time | Node | Event      | Detail", file=self.out)

    def log(self, now, ident, event, detail):
        """Print a log line."""
        print(f"{now:5d} | {ident:4d} | {event:10} | {detail}", file=self.out)
