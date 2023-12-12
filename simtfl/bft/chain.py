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
        """The number of voters."""

        self.t = t
        """The threshold of votes required for notarization."""

        self.parent = None
        """The genesis block has no parent (represented as `None`)."""

        self.length = 1
        """The genesis chain length is 1."""

        self.last_final = self
        """The last final block for the genesis block is itself."""

    def preceq(self, other: PermissionedBFTBase):
        """Return True if this block is an ancestor of `other`."""
        if self.length > other.length:
            return False  # optimization
        return self == other or (other.parent is not None and self.preceq(other.parent))

    def __eq__(self, other) -> bool:
        return other.parent is None and (self.n, self.t) == (other.n, other.t)

    def __hash__(self) -> int:
        return hash((self.n, self.t))


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
        """The proposal for this block."""

        assert proposal.parent is not None
        self.parent = proposal.parent
        """The parent of this block."""

        self.length = proposal.length
        """The chain length of this block."""

        self.last_final = self.parent.last_final
        """The last final block for this block."""

    def __eq__(self, other) -> bool:
        return (isinstance(other, PermissionedBFTBlock) and
                (self.n, self.t, self.proposal) == (other.n, other.t, other.proposal))

    def __hash__(self) -> int:
        return hash((self.n, self.t, self.proposal))


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
        """The parent block of this proposal."""

        self.length = parent.length + 1
        """The chain length of this proposal is one greater than its parent block."""

        self.votes = set()
        """The set of voter indices that have voted for this proposal."""

    def __eq__(self, other):
        """Two proposals are equal iff they are the same object."""
        return self is other

    def __hash__(self) -> int:
        return id(self)

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
        assert len(self.votes) >= self.t

    def is_notarized(self) -> bool:
        """Is this proposal notarized?"""
        try:
            self.assert_notarized()
            return True
        except AssertionError:
            return False

    def add_vote(self, index: int) -> None:
        """
        Record that the node with the given `index` has voted for this proposal.
        Calls that add the same vote more than once are ignored.
        """
        self.votes.add(index)
        assert len(self.votes) <= self.n


__all__ = ['two_thirds_threshold', 'PermissionedBFTBase', 'PermissionedBFTBlock', 'PermissionedBFTProposal']

import unittest


class TestPermissionedBFT(unittest.TestCase):
    def test_basic(self) -> None:
        # Construct the genesis block.
        genesis = PermissionedBFTBase(5, 2)
        current = genesis
        self.assertEqual(current.last_final, genesis)

        for _ in range(2):
            parent = current
            proposal = PermissionedBFTProposal(parent)
            proposal.assert_valid()
            self.assertTrue(proposal.is_valid())
            self.assertFalse(proposal.is_notarized())

            # not enough votes
            proposal.add_vote(0)
            self.assertFalse(proposal.is_notarized())

            # same index, so we still only have one vote
            proposal.add_vote(0)
            self.assertFalse(proposal.is_notarized())

            # different index, now we have two votes as required
            proposal.add_vote(1)
            proposal.assert_notarized()
            self.assertTrue(proposal.is_notarized())

            current = PermissionedBFTBlock(proposal)
            self.assertTrue(parent.preceq(current))
            self.assertFalse(current.preceq(parent))
            self.assertNotEqual(current, parent)
            self.assertEqual(current.last_final, genesis)

    def test_assertions(self) -> None:
        genesis = PermissionedBFTBase(5, 2)
        proposal = PermissionedBFTProposal(genesis)
        self.assertRaises(AssertionError, PermissionedBFTBlock, proposal)
        proposal.add_vote(0)
        self.assertRaises(AssertionError, PermissionedBFTBlock, proposal)
        proposal.add_vote(1)
        _ = PermissionedBFTBlock(proposal)
