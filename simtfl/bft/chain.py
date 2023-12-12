"""
Abstractions for Byzantine Fault-Tolerant protocols.
"""


from __future__ import annotations


def two_thirds_threshold(n: int) -> int:
    """
    Calculate the notarization threshold used in most permissioned BFT protocols:
    `ceiling(n * 2/3)`.
    """
    return (n * 2 + 2) // 3


class PermissionedBFTBase:
    """
    This class is used for the genesis block in a permissioned BFT protocol
    (which is taken to be notarized, and therefore valid, by definition).

    It is also used as a base class for other BFT block and proposal classes.
    """
    def __init__(self, n: int, t: int):
        """
        Constructs a genesis block for a permissioned BFT protocol with
        `n` nodes, of which at least `t` must sign each proposal.
        """
        self.n = n
        self.t = t
        self.parent = None

    def last_final(self) -> PermissionedBFTBase:
        """
        Returns the last final block in this block's ancestor chain.
        For the genesis block, this is itself.
        """
        return self


class PermissionedBFTBlock(PermissionedBFTBase):
    """
    A block for a BFT protocol. Each non-genesis block is based on a
    notarized proposal, and in practice consists of the proposer's signature
    over the notarized proposal.

    Honest proposers must only ever sign at most one valid proposal for the
    given epoch in which they are a proposer.

    BFT blocks are taken to be notarized, and therefore valid, by definition.
    """

    def __init__(self, proposal: PermissionedBFTProposal):
        """Constructs a `PermissionedBFTBlock` for the given proposal."""
        super().__init__(proposal.n, proposal.t)

        proposal.assert_notarized()
        self.proposal = proposal
        self.parent = proposal.parent

    def last_final(self):
        """
        Returns the last final block in this block's ancestor chain.
        This should be overridden by subclasses; the default implementation
        will (inefficiently) just return the genesis block.
        """
        return self if self.parent is None else self.parent.last_final()


class PermissionedBFTProposal(PermissionedBFTBase):
    """A proposal for a BFT protocol."""

    def __init__(self, parent: PermissionedBFTBase):
        """
        Constructs a `PermissionedBFTProposal` with the given parent
        `PermissionedBFTBlock`. The parameters are determined by the parent
        block.
        """
        super().__init__(parent.n, parent.t)
        self.parent = parent
        self.signers = set()

    def assert_valid(self) -> None:
        """
        Assert that this proposal is valid. This does not assert that it is
        notarized. This should be overridden by subclasses.
        """
        pass

    def is_valid(self) -> bool:
        """Is this proposal valid?"""
        try:
            self.assert_valid()
            return True
        except AssertionError:
            return False

    def assert_notarized(self) -> None:
        """
        Assert that this proposal is notarized. A `PermissionedBFTProposal`
        is notarized iff it is valid and has at least the threshold number of
        signatures.
        """
        self.assert_valid()
        assert len(self.signers) >= self.t

    def is_notarized(self) -> bool:
        """Is this proposal notarized?"""
        try:
            self.assert_notarized()
            return True
        except AssertionError:
            return False

    def add_signature(self, index: int) -> None:
        """
        Record that the node with the given `index` has signed this proposal.
        If the same node signs more than once, the subsequent signatures are
        ignored.
        """
        self.signers.add(index)
        assert len(self.signers) <= self.n


__all__ = ['two_thirds_threshold', 'PermissionedBFTBase', 'PermissionedBFTBlock', 'PermissionedBFTProposal']

import unittest


class TestPermissionedBFT(unittest.TestCase):
    def test_basic(self) -> None:
        # Construct the genesis block.
        genesis = PermissionedBFTBase(5, 2)
        current = genesis
        self.assertEqual(current.last_final(), genesis)

        for _ in range(2):
            proposal = PermissionedBFTProposal(current)
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

            current = PermissionedBFTBlock(proposal)
            self.assertEqual(current.last_final(), genesis)

    def test_assertions(self) -> None:
        genesis = PermissionedBFTBase(5, 2)
        proposal = PermissionedBFTProposal(genesis)
        self.assertRaises(AssertionError, PermissionedBFTBlock, proposal)
        proposal.add_signature(0)
        self.assertRaises(AssertionError, PermissionedBFTBlock, proposal)
        proposal.add_signature(1)
        _ = PermissionedBFTBlock(proposal)
