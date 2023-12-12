"""
An adapted-Streamlet node.
"""


from __future__ import annotations
from typing import Optional
from collections.abc import Sequence
from dataclasses import dataclass

from ...node import SequentialNode
from ...message import Message, PayloadMessage
from ...util import skip, ProcessEffect

from .chain import StreamletGenesis, StreamletBlock, StreamletProposal


class Echo(PayloadMessage):
    """
    An echo of another message. Streamlet requires nodes to broadcast each received
    non-echo message to every other node.
    """
    pass


@dataclass(frozen=True)
class Ballot(Message):
    """
    A ballot message, recording that a voter has voted for a `StreamletProposal`.
    Ballots should not be forged unless modelling an attack that allows doing so.
    """
    proposal: StreamletProposal
    """The proposal."""
    voter: int
    """The voter."""

    def __str__(self) -> str:
        return f"Ballot({self.proposal}, voter={self.voter})"


class Proposal(PayloadMessage):
    """
    A message containing a `StreamletProposal`.
    """
    pass


class Block(PayloadMessage):
    """
    A message containing a `StreamletBlock`.
    """
    pass


class StreamletNode(SequentialNode):
    """
    A Streamlet node.
    """

    def __init__(self, genesis: StreamletGenesis):
        """
        Constructs a Streamlet node with parameters taken from the given `genesis`
        block (an instance of `StreamletGenesis`).
        """
        assert genesis.epoch == 0
        self.genesis = genesis
        """The genesis block."""

        self.voted_epoch = genesis.epoch
        """The last epoch on which this node voted."""

        self.tip: StreamletBlock | StreamletGenesis = genesis
        """
        A longest chain seen by this node. The node's last final block is given by
        `self.tip.last_final`.
        """

        self.proposal: Optional[StreamletProposal] = None
        """The current proposal by this node, when it is the proposer."""

        self.safety_violations: set[tuple[StreamletBlock | StreamletGenesis,
                                          StreamletBlock | StreamletGenesis]] = set()
        """The set of safety violations detected by this node."""

    def propose(self, proposal: StreamletProposal) -> ProcessEffect:
        """
        (process) Ask the node to make a proposal.
        """
        assert proposal.is_valid()
        assert proposal.epoch > self.voted_epoch
        self.proposal = proposal
        return self.broadcast(Proposal(proposal), False)

    def handle(self, sender: int, message: Message) -> ProcessEffect:
        """
        (process) Message handler for a Streamlet node:
        * `Echo` messages are unwrapped and treated like the original message.
        * Non-`Echo` messages are implicitly echoed to every other node.
          (This causes the number of messages to blow up by a factor of `n`,
          but it's what the Streamlet paper specifies and is necessary for
          its liveness proof.)
        * Receiving a non-duplicate `Proposal` may cause us to broadcast a `Ballot`.
        * If we are the current proposer, keep track of ballots for our proposal.
        * Receiving a `Block` may cause us to update our `tip`.
        """
        if isinstance(message, Echo):
            message = message.payload
        else:
            yield from self.broadcast(Echo(message), False)

        if isinstance(message, Proposal):
            yield from self.handle_proposal(message.payload)
        elif isinstance(message, Block):
            yield from self.handle_block(message.payload)
        elif isinstance(message, Ballot):
            yield from self.handle_ballot(message)
        else:
            yield from super().handle(sender, message)

    def handle_proposal(self, proposal: StreamletProposal) -> ProcessEffect:
        """
        (process) If we already voted in the epoch specified by the proposal or a
        later epoch, ignore this proposal. Otherwise, cast a vote for it iff it
        is valid.
        """
        if proposal.epoch <= self.voted_epoch:
            self.log("proposal",
                     f"received proposal for epoch {proposal.epoch} but we already voted in epoch {self.voted_epoch}")
            return skip()

        if proposal.is_valid():
            self.log("proposal", f"voting for {proposal}")
            # For now we just forget that we made a proposal if we receive a different
            # valid one from another node. This is not realistic. Note that we can and
            # should vote for our own proposal.
            if proposal != self.proposal:
                self.proposal = None

            self.voted_epoch = proposal.epoch
            return self.broadcast(Ballot(proposal, self.ident), True)
        else:
            return skip()

    def handle_block(self, block: StreamletBlock) -> ProcessEffect:
        """
        If `block.last_final` does not descend from `self.tip.last_final`, reject the block.
        (In this case, if also `self.tip.last_final` does not descend from `block.last_final`,
        this is a detected safety violation.)

        Otherwise, update `self.tip` to `block` iff `block` is later in lexicographic ordering
        by `(length, epoch)`.
        """
        if not self.tip.last_final.preceq(block.last_final):
            self.log("block", f"× not ⪰ last_final:    {block}")
            if not block.last_final.preceq(self.tip.last_final):
                self.log("block", f"! safety violation:    ({block}, {self.tip})")
                self.safety_violations.add((block, self.tip))
            return skip()

        # TODO: analyse tie-breaking rule.
        if (self.tip.length, self.tip.epoch) >= (block.length, block.epoch):
            self.log("block", f"× not updating tip:    {block}")
            return skip()

        self.log("block", f"✓ updating tip:        {block}")
        self.tip = block
        return skip()

    def handle_ballot(self, ballot: Ballot) -> ProcessEffect:
        """
        If we have made a proposal that is not yet notarized and the ballot is
        for that proposal, add the vote. If it is now notarized, broadcast it
        as a block.
        """
        proposal = ballot.proposal
        if proposal == self.proposal:
            self.log("count", f"{ballot.voter} voted for our proposal in epoch {proposal.epoch}")
            proposal.add_vote(ballot.voter)
            if proposal.is_notarized():
                yield from self.broadcast(Block(StreamletBlock(proposal)), True)
                # It's fine to forget that we made the proposal now.
                self.proposal = None

    def final_block(self) -> StreamletBlock | StreamletGenesis:
        """
        Return the last final block seen by this node.
        """
        return self.tip.last_final


__all__ = ['Echo', 'Ballot', 'StreamletNode']

import unittest
from itertools import count
from simpy import Environment
from simpy.events import Process, Timeout

from ...network import Network
from ...logging import PrintLogger


class TestStreamlet(unittest.TestCase):
    def test_simple(self) -> None:
        """
        Very simple example.

        0 --- 1 --- 2 --- 3
        """
        self._test_last_final([0, 1, 2],
                              [0, 0, 2])

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
        N = None
        self._test_last_final([0, 0, 1, N, 2, 5, 6],
                              [0, 0, 0, 0, 0, 0, 6])

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
        N = None
        self._test_last_final([0, 0, 1, N, 2, 5, 6, 3, 8, 9],
                              [0, 0, 0, 0, 0, 0, 6, 0, 0, 9],
                              expect_divergence_at_epoch=8,
                              expect_safety_violations={(10, 7)})

    def _test_last_final(self,
                         parent_map: Sequence[Optional[int]],
                         final_map: Sequence[int],
                         expect_divergence_at_epoch: Optional[int]=None,
                         expect_safety_violations: set[tuple[int, int]]=set()) -> None:
        """
        This test constructs a tree of proposals with structure determined by
        `parent_map`, and asserts `block.last_final` matches the structure
        determined by `final_map`.

        parent_map: sequence of parent epoch numbers
        final_map: sequence of final epoch numbers
        expect_divergence_at_epoch: first epoch at which a block does not become the new tip
        expect_safety_violations: safety violation proofs
        """

        assert len(parent_map) == len(final_map)

        # Construct the genesis block.
        genesis = StreamletGenesis(3)
        network = Network(Environment(), logger=PrintLogger())
        for _ in range(genesis.n):
            network.add_node(StreamletNode(genesis))

        current = genesis
        self.assertEqual(current.last_final, genesis)
        blocks: list[Optional[StreamletBlock | StreamletGenesis]] = [genesis]

        def run() -> ProcessEffect:
            for (epoch, parent_epoch, final_epoch) in zip(count(1), parent_map, final_map):
                yield Timeout(network.env, 10)
                if parent_epoch is None:
                    blocks.append(None)
                    continue

                parent = blocks[parent_epoch]
                assert parent is not None
                proposer = network.node(genesis.proposer_for_epoch(epoch))
                proposal = StreamletProposal(parent, epoch)
                self.assertEqual(proposal.length, parent.length + 1)
                proposal.assert_valid()
                self.assertFalse(proposal.is_notarized())

                proposer.propose(proposal)
                yield Timeout(network.env, 10)

                # The proposer should have sent the block.
                assert proposer.proposal is None

                # Make a fake block `current` from the proposal so that we can append
                # it to `blocks` and check its `last_final`.
                current = StreamletBlock(proposal)
                self.assertEqual(current.length, proposal.length)
                self.assertTrue(parent.preceq(current))
                self.assertFalse(current.preceq(parent))
                self.assertEqual(len(blocks), current.epoch)
                blocks.append(current)
                final_block = blocks[final_epoch]
                assert final_block is not None
                self.assertEqual(current.last_final, final_block)

                # All nodes' tips should be the same.
                tip = network.node(0).tip
                for i in range(1, network.num_nodes()):
                    self.assertEqual(network.node(i).tip, tip)

                # If we try to create a new block on top of a chain that is not the longest,
                # the nodes will ignore it.
                if epoch == expect_divergence_at_epoch:
                    self.assertLess(current.length, tip.length)
                elif expect_divergence_at_epoch is None or epoch < expect_divergence_at_epoch:
                    self.assertEqual(current.length, tip.length)
                    self.assertEqual(tip.epoch, epoch)
                    self.assertEqual(tip.proposal, proposal)

                    for node in network.nodes:
                        node_final = node.final_block()
                        self.assertEqual(node_final, final_block,
                                         f"epoch {node_final.epoch} != epoch {final_block.epoch}")

            for node in network.nodes:
                self.assertEqual(set(((a.epoch, b.epoch) for (a, b) in node.safety_violations)),
                                 expect_safety_violations)

            network.done = True

        Process(network.env, run())
        network.run_all()
        self.assertTrue(network.done)
