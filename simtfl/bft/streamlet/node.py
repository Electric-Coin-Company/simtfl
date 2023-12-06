"""
An adapted-Streamlet node.
"""


from __future__ import annotations

from ...node import SequentialNode
from ...message import Message, PayloadMessage
from ...util import skip, ProcessEffect

from . import StreamletGenesis, StreamletBlock, StreamletProposal


class Echo(PayloadMessage):
    """
    An echo of another message. Streamlet requires nodes to broadcast each received
    non-echo message to every other node.
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
        self.voted_epoch = genesis.epoch

    def handle(self, sender: int, message: Message) -> ProcessEffect:
        """
        (process) Message handler for a Streamlet node:
        * `Echo` messages are unwrapped and treated like the original message.
        * Non-`Echo` messages are implicitly echoed to every other node.
          (This causes the number of messages to blow up by a factor of `n`,
          but it's what the Streamlet paper specifies and is necessary for
          its liveness proof.)
        * Received non-duplicate proposals may cause us to send a `Vote`.
        * ...
        """
        if isinstance(message, Echo):
            message = message.payload
        else:
            yield from self.broadcast(Echo(message))

        if isinstance(message, StreamletProposal):
            yield from self.handle_proposal(message)
        elif isinstance(message, StreamletBlock):
            yield from self.handle_block(message)
        else:
            yield from super().handle(sender, message)

    def handle_proposal(self, proposal: StreamletProposal) -> ProcessEffect:
        """
        (process) If we already voted in the epoch specified by the proposal or a
        later epoch, ignore this proposal.
        """
        if proposal.epoch <= self.voted_epoch:
            self.log("handle",
                     f"received proposal for epoch {proposal.epoch} but we already voted in epoch {self.voted_epoch}")
            return skip()

        return skip()

    def handle_block(self, block: StreamletBlock) -> ProcessEffect:
        raise NotImplementedError
