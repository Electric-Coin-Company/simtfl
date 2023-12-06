"""
An implementation of adapted-Streamlet ([CS2020] as modified in [Crosslink]).

[CS2020] https://eprint.iacr.org/2020/088.pdf
[Crosslink] https://hackmd.io/JqENg--qSmyqRt_RqY7Whw?view
"""


from __future__ import annotations
from typing import Optional
from collections.abc import Sequence

from .. import PermissionedBFTBase, PermissionedBFTBlock, PermissionedBFTProposal, \
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
        assert epoch > parent.epoch
        self.epoch = epoch
        """The epoch of this proposal."""

    def __repr__(self) -> str:
        return "StreamletProposal(parent=%r, epoch=%r)" % (self.parent, self.epoch)


class StreamletGenesis(PermissionedBFTBase):
    """An adapted-Streamlet genesis block."""

    def __init__(self, n: int):
        """
        Constructs a genesis block for adapted-Streamlet with `n` nodes.
        """
        super().__init__(n, two_thirds_threshold(n))
        self.epoch = 0
        """The genesis block has epoch 0."""

    def __repr__(self) -> str:
        return "StreamletGenesis(n=%r)" % (self.n,)


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

    def last_final(self) -> StreamletBlock | StreamletGenesis:
        """
        Returns the last final block in this block's ancestor chain.
        In Streamlet this is the middle block of the last group of three
        that were proposed in consecutive epochs.
        """
        last = self
        if last.parent is None:
            return last
        middle = last.parent
        if middle.parent is None:
            return middle
        first = middle.parent
        while True:
            if first.parent is None:
                return first
            if (first.epoch + 1, middle.epoch + 1) == (middle.epoch, last.epoch):
                return middle
            (first, middle, last) = (first.parent, first, middle)

    def __repr__(self) -> str:
        return "StreamletBlock(proposal=%r)" % (self.proposal,)


import unittest
from itertools import count


class TestStreamlet(unittest.TestCase):
    def test_simple(self) -> None:
        """
        Very simple example.

        0 --- 1 --- 2 --- 3
        """
        self._test_last_final([0, 1, 2], [0, 0, 2])

    def test_figure_1(self) -> None:
        """
        Figure 1: Streamlet finalization example (without the invalid 'X' proposal).

        0 --- 2 --- 5 --- 6 --- 7
          \
           -- 1 --- 3

        0 - Genesis
        N - Notarized block

        This diagram implies the epoch 6 block is the last-final block in the
        context of the epoch 7 block, because it is in the middle of 3 blocks
        with consecutive epoch numbers, and 6 is the most recent such block.

        (We don't include the block/proposal with the red X because that's not
        what we're testing.)
        """
        self._test_last_final([0, 0, 1, None, 2, 5, 6], [0, 0, 0, 0, 0, 0, 6])

    def test_complex(self) -> None:
        """
        Safety Violation: due to three simultaneous properties:

        - 6 is `last_final` in the context of 7
        - 9 is `last_final` in the context of 10
        - 9 is not a descendant of 6

        0 --- 2 --- 5 --- 6 --- 7
          \
           -- 1 --- 3 --- 8 --- 9 --- 10
        """
        self._test_last_final([0, 0, 1, None, 2, 5, 6, 3, 8, 9], [0, 0, 0, 0, 0, 0, 6, 0, 0, 9])

    def _test_last_final(self, parent_map: Sequence[Optional[int]], final_map: Sequence[int]) -> None:
        """
        This test constructs a tree of proposals with structure determined by
        `parent_map`, and asserts `block.last_final()` matches the structure
        determined by `final_map`.

        parent_map: sequence of parent epoch numbers
        final_map: sequence of final epoch numbers
        """

        assert len(parent_map) == len(final_map)

        # Construct the genesis block.
        genesis = StreamletGenesis(3)
        current = genesis
        self.assertEqual(current.last_final(), genesis)
        blocks = [genesis]

        for (epoch, parent_epoch, final_epoch) in zip(count(1), parent_map, final_map):
            if parent_epoch is None:
                blocks.append(None)
                continue

            parent = blocks[parent_epoch]
            assert parent is not None
            proposal = StreamletProposal(parent, epoch)
            proposal.assert_valid()
            self.assertTrue(proposal.is_valid())
            self.assertFalse(proposal.is_notarized())

            # not enough signatures
            proposal.add_signature(0)
            self.assertFalse(proposal.is_notarized())

            # same index, so we still only have one signature
            proposal.add_signature(0)
            self.assertFalse(proposal.is_notarized())

            # different index, now we have two signatures as required
            proposal.add_signature(1)
            proposal.assert_notarized()
            self.assertTrue(proposal.is_notarized())

            current = StreamletBlock(proposal)
            blocks.append(current)
            self.assertEqual(current.last_final(), blocks[final_epoch])
