"""
Abstractions for best-chain transactions, contexts, and blocks.
"""


from __future__ import annotations
from typing import Iterable, Optional
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from collections import deque
from itertools import chain, islice
from sys import version_info

from ..util import Unique


class BlockHash(Unique):
    """Unique value representing a best-chain block hash."""
    pass


class BCTransaction:
    """A transaction for a best-chain protocol."""

    @dataclass(frozen=True)
    class _TXO:
        tx: BCTransaction
        index: int
        value: int

    @dataclass(eq=False)
    class _Note(Unique):
        """
        A shielded note. Unlike in the actual protocol, we conflate notes, note
        commitments, and nullifiers. This will be sufficient because we don't
        need to maintain any actual privacy.

        This is not a frozen dataclass; its identity is important, and models the
        fact that each note has a unique commitment and nullifier in the actual
        protocol.
        """
        value: int

    def __init__(self,
                 transparent_inputs: Sequence[BCTransaction._TXO],
                 transparent_output_values: Sequence[int],
                 shielded_inputs: Sequence[BCTransaction._Note],
                 shielded_output_values: Sequence[int],
                 fee: int,
                 anchor: Optional[BCContext]=None,
                 issuance: int=0):
        """
        Constructs a `BCTransaction` with the given transparent inputs, transparent
        output values, anchor, shielded inputs, shielded output values, fee, and
        (if it is a coinbase transaction) issuance.

        The elements of `transparent_inputs` are TXO objects obtained from the
        `transparent_output` method of another `BCTransaction`. The elements of
        `shielded_inputs` are Note objects obtained from the `shielded_output`
        method of another `BCTransaction`. The TXO and Note classes are private,
        and these objects should not be constructed directly.

        The anchor is modelled as a `BCContext` such that
        `anchor.can_spend(shielded_inputs)`. If there are no shielded inputs,
        `anchor` must be `None`. The anchor object must not be modified after
        passing it to this constructor (copy it if necessary).

        For a coinbase transaction, pass `[]` for `transparent_inputs` and
        `shielded_inputs`, and pass `fee` as a negative value of magnitude equal
        to the total amount of fees paid by other transactions in the block.
        """
        assert issuance >= 0
        coinbase = len(transparent_inputs) + len(shielded_inputs) == 0
        assert fee >= 0 or coinbase
        assert issuance == 0 or coinbase
        assert all((v >= 0 for v in chain(transparent_output_values, shielded_output_values)))
        assert (
            sum((txin.value for txin in transparent_inputs))
            + sum((note.value for note in shielded_inputs))
            + issuance ==
            sum(transparent_output_values)
            + sum(shielded_output_values)
            + fee
        )
        assert anchor is None if len(shielded_inputs) == 0 else (
            anchor is not None and anchor.can_spend(shielded_inputs))

        self.transparent_inputs = transparent_inputs
        self.transparent_outputs = [self._TXO(self, i, v)
                                    for (i, v) in enumerate(transparent_output_values)]
        self.shielded_inputs = shielded_inputs
        self.shielded_outputs = [self._Note(v) for v in shielded_output_values]
        self.fee = fee
        self.anchor = anchor
        self.issuance = issuance

    def transparent_input(self, index: int) -> BCTransaction._TXO:
        """Returns the transparent input TXO with the given index."""
        return self.transparent_inputs[index]

    def transparent_output(self, index: int) -> BCTransaction._TXO:
        """Returns the transparent output TXO with the given index."""
        return self.transparent_outputs[index]

    def shielded_input(self, index: int) -> BCTransaction._Note:
        """Returns the shielded input note with the given index."""
        return self.shielded_inputs[index]

    def shielded_output(self, index: int) -> BCTransaction._Note:
        """Returns the shielded output note with the given index."""
        return self.shielded_outputs[index]

    def is_coinbase(self) -> bool:
        """
        Returns `True` if this is a coinbase transaction (it has no inputs).
        """
        return len(self.transparent_inputs) + len(self.shielded_inputs) == 0


class Spentness(Enum):
    """The spentness status of a note."""
    Unspent = auto()
    """The note is unspent."""
    Spent = auto()
    """The note is spent."""


class BCContext:
    """
    A context that allows checking transactions for contextual validity in a
    best-chain protocol.
    """

    assert version_info >= (3, 7), "This code relies on insertion-ordered dicts."

    def __init__(self):
        """Constructs an empty `BCContext`."""
        self.transactions: deque[BCTransaction] = deque()
        self.utxo_set: set[BCTransaction._TXO] = set()

        # Since dicts are insertion-ordered, this models the sequence in which
        # notes are committed as well as their spentness.
        self.notes: dict[BCTransaction._Note, Spentness] = {}

        self.total_issuance = 0

    def committed_notes(self) -> list[(BCTransaction._Note, Spentness)]:
        """
        Returns a list of (`Note`, `Spentness`) for notes added to this context,
        preserving the commitment order.
        """
        return list(self.notes.items())

    def can_spend(self, tospend: Iterable[BCTransaction._Note]) -> bool:
        """Can all of the notes in `tospend` be spent in this context?"""
        return all((self.notes.get(note) == Spentness.Unspent for note in tospend))

    def _check(self, tx: BCTransaction) -> tuple[bool, set[BCTransaction._TXO]]:
        """
        Checks whether `tx` is valid. To avoid recomputation, this returns
        a pair of the validity, and the set of transparent inputs of `tx`.
        """
        txins = set(tx.transparent_inputs)
        valid = txins.issubset(self.utxo_set) and self.can_spend(tx.shielded_inputs)
        return (valid, txins)

    def is_valid(self, tx: BCTransaction) -> bool:
        """Is `tx` valid in this context?"""
        return self._check(tx)[0]

    def add_if_valid(self, tx: BCTransaction) -> bool:
        """
        If `tx` is valid in this context, add it to the context and return `True`.
        Otherwise leave the context unchanged and return `False`.
        """
        (valid, txins) = self._check(tx)
        if valid:
            self.utxo_set -= txins
            self.utxo_set |= set(tx.transparent_outputs)

            for note in tx.shielded_inputs:
                self.notes[note] = Spentness.Spent
            for note in tx.shielded_outputs:
                assert note not in self.notes
                self.notes[note] = Spentness.Unspent

            self.total_issuance += tx.issuance
            self.transactions.append(tx)

        return valid

    def copy(self) -> BCContext:
        """Returns an independent copy of this `BCContext`."""
        ctx = BCContext()
        ctx.transactions = self.transactions.copy()
        ctx.utxo_set = self.utxo_set.copy()
        ctx.notes = self.notes.copy()
        ctx.total_issuance = self.total_issuance
        return ctx


class BCBlock:
    """A block in a best-chain protocol."""

    def __init__(self,
                 parent: Optional[BCBlock],
                 added_score: int,
                 transactions: Sequence[BCTransaction],
                 allow_invalid: bool=False):
        """
        Constructs a `BCBlock` with the given parent block, score relative to the
        parent, and sequence of transactions. `transactions` must not be modified
        after passing it to this constructor (copy it if necessary).
        If `allow_invalid` is set, the block need not be valid.
        Use `parent=None` to construct the genesis block.
        """
        self.parent = parent
        self.score = added_score
        if self.parent is not None:
            self.score += self.parent.score
        self.transactions = transactions
        self.hash = BlockHash()
        if not allow_invalid:
            self.assert_noncontextually_valid()

    def assert_noncontextually_valid(self) -> None:
        """Assert that non-contextual consensus rules are satisfied for this block."""
        assert len(self.transactions) > 0
        assert self.transactions[0].is_coinbase()
        assert not any((tx.is_coinbase() for tx in islice(self.transactions, 1, None)))
        assert sum((tx.fee for tx in self.transactions)) == 0

    def is_noncontextually_valid(self) -> bool:
        """Are non-contextual consensus rules satisfied for this block?"""
        try:
            self.assert_noncontextually_valid()
            return True
        except AssertionError:
            return False


@dataclass
class BCProtocol:
    """A best-chain protocol."""

    Transaction: type[object] = BCTransaction
    """The type of transactions for this protocol."""

    Context: type[object] = BCContext
    """The type of contexts for this protocol."""

    Block: type[object] = BCBlock
    """The type of blocks for this protocol."""


__all__ = ['BCTransaction', 'BCContext', 'BCBlock', 'BCProtocol', 'BlockHash', 'Spentness']


import unittest


class TestBC(unittest.TestCase):
    def test_basic(self) -> None:
        ctx = BCContext()
        coinbase_tx0 = BCTransaction([], [10], [], [], 0, issuance=10)
        self.assertTrue(ctx.add_if_valid(coinbase_tx0))
        genesis = BCBlock(None, 1, [coinbase_tx0])
        self.assertEqual(genesis.score, 1)
        self.assertEqual(ctx.total_issuance, 10)

        coinbase_tx1 = BCTransaction([], [6], [], [], -1, issuance=5)
        spend_tx = BCTransaction([coinbase_tx0.transparent_output(0)], [9], [], [], 1)
        self.assertTrue(ctx.add_if_valid(coinbase_tx1))
        self.assertTrue(ctx.add_if_valid(spend_tx))
        block1 = BCBlock(genesis, 1, [coinbase_tx1, spend_tx])
        self.assertEqual(block1.score, 2)
        self.assertEqual(ctx.total_issuance, 15)

        coinbase_tx2 = BCTransaction([], [6], [], [], -1, issuance=5)
        shielding_tx = BCTransaction([coinbase_tx1.transparent_output(0), spend_tx.transparent_output(0)],
                                     [], [], [8, 6], 1)
        self.assertTrue(ctx.add_if_valid(coinbase_tx2))
        self.assertTrue(ctx.add_if_valid(shielding_tx))
        block2 = BCBlock(block1, 2, [coinbase_tx2, shielding_tx])
        block2_anchor = ctx.copy()
        self.assertEqual(block2.score, 4)
        self.assertEqual(ctx.total_issuance, 20)

        coinbase_tx3 = BCTransaction([], [7], [], [], -2, issuance=5)
        shielded_tx = BCTransaction([], [], [shielding_tx.shielded_output(0)], [7], 1,
                                    anchor=block2_anchor)
        deshielding_tx = BCTransaction([], [5], [shielding_tx.shielded_output(1)], [], 1,
                                       anchor=block2_anchor)
        self.assertTrue(ctx.add_if_valid(coinbase_tx3))
        self.assertTrue(ctx.add_if_valid(shielded_tx))
        self.assertTrue(ctx.add_if_valid(deshielding_tx))
        block3 = BCBlock(block2, 3, [coinbase_tx3, shielded_tx, deshielding_tx])
        self.assertEqual(block3.score, 7)
        self.assertEqual(ctx.total_issuance, 25)
