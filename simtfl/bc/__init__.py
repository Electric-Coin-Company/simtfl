"""
Abstractions for best-chain transactions, contexts, and blocks.
"""

from collections import deque
from dataclasses import dataclass

from ..util import Unique


class BCTransaction:
    """A transaction for a best-chain protocol."""

    @dataclass(frozen=True)
    class _TXO:
        tx: 'BCTransaction'
        index: int
        value: int

    def __init__(self, inputs, output_values, fee, issuance=0):
        """
        Constructs a `BCTransaction` with the given inputs, output values, fee,
        and (if it is a coinbase transaction) issuance.
        The elements of `inputs` are TXO objects obtained from the `output` method
        of another `BCTransaction`.
        For a coinbase transaction, pass `inputs=[]`, and `fee` as a negative value
        of magnitude equal to the total amount of fees paid by other transactions
        in the block.
        """
        assert issuance >= 0
        assert fee >= 0 or len(inputs) == 0
        assert issuance == 0 or len(inputs) == 0
        assert all((isinstance(txin, self._TXO) for txin in inputs))
        assert sum((txin.value for txin in inputs)) + issuance == sum(output_values) + fee
        self.inputs = inputs
        self.outputs = [self._TXO(self, i, v) for (i, v) in enumerate(output_values)]
        self.fee = fee
        self.issuance = issuance

    def input(self, index):
        """Returns the input with the given index."""
        return self.inputs[index]

    def output(self, index):
        """Returns the output with the given index."""
        return self.outputs[index]

    def is_coinbase(self):
        """Returns `True` if this is a coinbase transaction (it has no inputs)."""
        return len(self.inputs) == 0


class BCContext:
    """
    A context that allows checking transactions for contextual validity in a
    best-chain protocol.
    """

    def __init__(self):
        """Constructs an empty `BCContext`."""
        self.transactions = deque()
        self.utxo_set = set()
        self.total_issuance = 0

    def is_valid(self, tx):
        """Is `tx` valid in this context?"""
        return set(tx.inputs).issubset(self.utxo_set)

    def add_if_valid(self, tx):
        """
        If `tx` is valid in this context, add it to the context and return `True`.
        Otherwise leave the context unchanged and return `False`.
        """
        txins = set(tx.inputs)
        valid = txins.issubset(self.utxo_set)
        if valid:
            self.utxo_set -= txins
            self.utxo_set |= set(tx.outputs)
            self.total_issuance += tx.issuance
            self.transactions.append(tx)

        return valid


class BCBlock:
    """A block in a best-chain protocol."""

    def __init__(self, parent, added_score, transactions, allow_invalid=False):
        """
        Constructs a `BCBlock` with the given parent block, score relative to the parent,
        and transactions.
        If `allow_invalid` is set, the block need not be valid.
        Use `parent=None` to construct the genesis block.
        """
        assert all((isinstance(tx, BCTransaction) for tx in transactions))
        self.parent = parent
        self.score = (0 if parent is None else self.parent.score) + added_score
        self.transactions = transactions
        self.hash = Unique()
        assert allow_invalid or self.is_noncontextually_valid()

    def is_noncontextually_valid(self):
        """
        Are non-contextual consensus rules satisfied for this block?
        """
        return (
            len(self.transactions) > 0 and
            self.transactions[0].is_coinbase() and
            not any((tx.is_coinbase() for tx in self.transactions[1:])) and
            sum((tx.fee for tx in self.transactions)) == 0
        )


@dataclass
class BCProtocol:
    """A best-chain protocol."""

    Transaction: type[object] = BCTransaction
    """The type of transactions for this protocol."""

    Context: type[object] = BCContext
    """The type of contexts for this protocol."""

    Block: type[object] = BCBlock
    """The type of blocks for this protocol."""


__all__ = ['BCTransaction', 'BCContext', 'BCBlock', 'BCProtocol']


import unittest


class TestBC(unittest.TestCase):
    def test_basic(self):
        ctx = BCContext()
        issuance_tx0 = BCTransaction([], [10], 0, issuance=10)
        assert ctx.add_if_valid(issuance_tx0)
        genesis = BCBlock(None, 1, [issuance_tx0])
        assert genesis.score == 1

        issuance_tx1 = BCTransaction([], [6], -1, issuance=5)
        spend_tx = BCTransaction([issuance_tx0.output(0)], [9], 1)
        assert ctx.add_if_valid(issuance_tx1)
        assert ctx.add_if_valid(spend_tx)
        block1 = BCBlock(genesis, 1, [issuance_tx1, spend_tx])
        assert block1.score == 2
