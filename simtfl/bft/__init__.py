"""
Abstractions for Byzantine Fault-Tolerant protocols.

The model of a BFT protocol assumed here was written for the purpose
of Crosslink, based on the example of adapted-Streamlet ([CS2020] as
modified in [Crosslink]). It might not be sufficient for other BFT
protocols — but that's okay; it's a prototype.

[CS2020] https://eprint.iacr.org/2020/088.pdf
[Crosslink] https://hackmd.io/JqENg--qSmyqRt_RqY7Whw?view
"""


def two_thirds_threshold(n):
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
    def __init__(self, n, t):
        """
        Constructs a genesis block for a permissioned BFT protocol with
        `n` nodes, of which at least `t` must sign each proposal.
        """
        self.n = n
        self.t = t
        self.parent = None


class PermissionedBFTBlock(PermissionedBFTBase):
    """
    A block for a BFT protocol. Each non-genesis block is based on a
    notarized proposal.

    BFT blocks are taken to be notarized, and therefore valid, by definition.
    """

    def __init__(self, proposal):
        super().__init__(proposal.n, proposal.t)

        proposal.assert_notarized()
        self.proposal = proposal


class PermissionedBFTProposal(PermissionedBFTBase):
    """A proposal for a BFT protocol."""

    def __init__(self, parent):
        """
        Constructs a `PermissionedBFTProposal` with the given parent
        `PermissionedBFTBlock`. The parameters are determined by the parent
        block.
        """
        super().__init__(parent.n, parent.t)
        self.parent = parent
        self.signers = set()

    def assert_valid(self):
        """
        Assert that this proposal is valid. This does not assert that it is
        notarized. This should be overridden by subclasses.
        """
        pass

    def is_valid(self):
        """Is this proposal valid?"""
        try:
            self.assert_valid()
            return True
        except AssertionError:
            return False

    def assert_notarized(self):
        """
        Assert that this proposal is notarized. A `PermissionedBFTProposal`
        is notarized iff it is valid and has at least the threshold number of
        signatures.
        """
        self.assert_valid()
        assert len(self.signers) >= self.t

    def is_notarized(self):
        """Is this proposal notarized?"""
        try:
            self.assert_notarized()
            return True
        except AssertionError:
            return False

    def add_signature(self, index):
        """
        Record that the node with the given `index` has signed this proposal.
        If the same node signs more than once, the subsequent signatures are
        ignored.
        """
        self.signers.add(index)
        assert len(self.signers) <= self.n


import unittest


class TestPermissionedBFT(unittest.TestCase):
    def test_basic(self):
        # Construct the genesis block.
        current = PermissionedBFTBase(5, 2)

        for i in range(2):
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

    def test_assertions(self):
        genesis = PermissionedBFTBase(5, 2)
        proposal = PermissionedBFTProposal(genesis)
        self.assertRaises(AssertionError, PermissionedBFTBlock, proposal)
        proposal.add_signature(0)
        self.assertRaises(AssertionError, PermissionedBFTBlock, proposal)
        proposal.add_signature(1)
        _ = PermissionedBFTBlock(proposal)
