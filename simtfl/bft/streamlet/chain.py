"""
Adapted-Streamlet chain classes.
"""


from __future__ import annotations
from typing import Optional

from ..chain import PermissionedBFTBase, PermissionedBFTBlock, PermissionedBFTProposal, \
    two_thirds_threshold


class StreamletProposal(PermissionedBFTProposal):
    """An adapted-Streamlet proposal."""

    def __init__(self, parent: StreamletBlock | StreamletGenesis, epoch: int):
        """
        Constructs a `StreamletProposal` with the given parent `StreamletBlock`,
        for the given `epoch`. The parameters are determined by the parent block.
        A proposal must be for an epoch after its parent's epoch.
        """
        super().__init__(parent)
        self.parent: StreamletBlock | StreamletGenesis = parent

        assert epoch > parent.epoch
        self.epoch = epoch
        """The epoch of this proposal."""

    def __str__(self) -> str:
        return "StreamletProposal(parent=%s, epoch=%s)" % (self.parent, self.epoch)


class StreamletGenesis(PermissionedBFTBase):
    """An adapted-Streamlet genesis block."""

    def __init__(self, n: int):
        """
        Constructs a genesis block for adapted-Streamlet with `n` nodes.
        """
        super().__init__(n, two_thirds_threshold(n))

        self.parent: Optional[StreamletBlock | StreamletGenesis] = None
        """The genesis block has no parent (represented as `None`)."""

        self.epoch = 0
        """The epoch of the genesis block is 0."""

        self.last_final = self
        """The last final block of the genesis block is itself."""

    def __str__(self) -> str:
        return "StreamletGenesis(n=%s)" % (self.n,)

    def proposer_for_epoch(self, epoch: int):
        assert epoch > 0
        return (epoch - 1) % self.n


class StreamletBlock(PermissionedBFTBlock):
    """
    An adapted-Streamlet block. Each non-genesis Streamlet block is
    based on a notarized `StreamletProposal`.

    `StreamletBlock`s are taken to be notarized by definition.
    All validity conditions are enforced in the contructor.
    """

    def __init__(self, proposal: StreamletProposal):
        """Constructs a `StreamletBlock` for the given proposal."""
        super().__init__(proposal)

        self.epoch = proposal.epoch
        """The epoch of this proposal."""

        self.parent: StreamletBlock | StreamletGenesis = proposal.parent

        self.last_final = self._compute_last_final()
        """
        The last final block in this block's ancestor chain.
        In Streamlet this is the middle block of the last group of three
        that were proposed in consecutive epochs.
        """

    def _compute_last_final(self) -> StreamletBlock | StreamletGenesis:
        last: StreamletBlock | StreamletGenesis = self
        if last.parent is None:
            return last
        middle: StreamletBlock | StreamletGenesis = last.parent
        if middle.parent is None:
            return middle
        first: StreamletBlock | StreamletGenesis = middle.parent
        while True:
            if first.parent is None:
                return first
            if (first.epoch + 1, middle.epoch + 1) == (middle.epoch, last.epoch):
                return middle
            (first, middle, last) = (first.parent, first, middle)

    def __str__(self) -> str:
        return "StreamletBlock(proposal=%s)" % (self.proposal,)
