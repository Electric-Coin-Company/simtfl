"""
Base classes for node implementations.
"""

from collections import deque

from .util import skip


class PassiveNode:
    """
    A node that processes messages concurrently. By default it sends no
    messages and does nothing with received messages. This class is
    intended to be subclassed.

    Inherit from this class directly if all messages are to be processed
    concurrently without blocking. If messages are to be processed
    sequentially, it may be easier to inherit from `SequentialNode`.

    Note that the simulation is deterministic regardless of which option
    is selected.
    """
    def initialize(self, ident, env, network):
        """
        Initializes a `PassiveNode` with the given ident, `simpy.Environment`,
        and `Network`. Nodes are initialized when they are added to a `Network`.
        """
        self.ident = ident
        self.env = env
        self.network = network

    def __str__(self):
        return f"{self.__class__.__name__}"

    def send(self, target, message, delay=None):
        """
        (process) This method can be overridden to intercept messages being sent
        by this node. The implementation in this class calls `self.network.send`
        with this node as the sender.
        """
        return self.network.send(self.ident, target, message, delay=delay)

    def broadcast(self, message, delay=None):
        """
        (process) This method can be overridden to intercept messages being broadcast
        by this node. The implementation in this class calls `self.network.broadcast`
        with this node as the sender.
        """
        return self.network.broadcast(self.ident, message, delay=delay)

    def receive(self, sender, message):
        """
        (process) This method can be overridden to intercept messages being received
        by this node. The implementation in this class calls `self.handle`.
        """
        return self.handle(sender, message)

    def handle(self, sender, message):
        """
        (process) Handles a message by doing nothing. Note that the handling of
        each message, and the `run` method, are in separate simpy processes. That
        is, yielding here will not block other incoming messages for a direct
        subclass of `PassiveNode`.
        """
        return skip()

    def run(self):
        """
        (process) Runs by doing nothing.
        """
        return skip()


class SequentialNode(PassiveNode):
    """
    A node that processes messages sequentially. By default it sends no
    messages and does nothing with received messages. This class is
    intended to be subclassed.
    """
    def initialize(self, ident, env, network):
        """
        Initializes a `SequentialNode` with the given `simpy.Environment` and `Network`.
        """
        super().initialize(ident, env, network)
        self._mailbox = deque()
        self._wakeup = env.event()

    def receive(self, sender, message):
        """
        (process) Add incoming messages to the mailbox.
        """
        self._mailbox.append((sender, message))
        try:
            self._wakeup.succeed()
        except RuntimeError:
            pass
        return skip()

    def handle(self, sender, message):
        """
        (process) Handles a message by doing nothing. Messages are handled
        sequentially; that is, handling of the next message will be blocked
        on this process.
        """
        # This is the same implementation as `PassiveNode`, but the documentation
        # is different.
        return skip()

    def run(self):
        """
        (process) Repeatedly handle incoming messages.
        If a subclass needs to perform tasks in parallel with message handling,
        it should create a separate process and then delegate to this superclass
        implementation.
        """
        while True:
            while len(self._mailbox) > 0:
                (sender, message) = self._mailbox.popleft()
                print(f"T{self.env.now:5d}: handling  {sender:2d} -> {self.ident:2d}: {message}")
                yield from self.handle(sender, message)

            # This naive implementation is fine because we have no actual
            # concurrency.
            self._wakeup = self.env.event()
            yield self._wakeup


__all__ = ['PassiveNode', 'SequentialNode']

from simpy import Environment
import unittest

from .message import PayloadMessage
from .network import Network


class PassiveReceiverTestNode(PassiveNode):
    def __init__(self):
        super().__init__()
        self.handled = deque()

    def handle(self, sender, message):
        # Record when each message is handled.
        self.handled.append((sender, message, self.env.now))
        # The handler takes 3 time units.
        yield self.env.timeout(3)


class SequentialReceiverTestNode(SequentialNode):
    def __init__(self):
        super().__init__()
        self.handled = deque()

    def handle(self, sender, message):
        # Record when each message is handled.
        self.handled.append((sender, message, self.env.now))
        # The handler takes 3 time units.
        yield self.env.timeout(3)


class SenderTestNode(PassiveNode):
    def run(self):
        # We send messages at times 0, 1, 2. Since the message
        # propagation delay is 1 (the default), they will be
        # received at times 1, 2, 3.
        for i in range(3):
            yield from self.send(0, PayloadMessage(i))
            yield self.env.timeout(1)

        # Test overriding the propagation delay. This message
        # is sent at time 3 and received at time 14.
        yield from self.send(0, PayloadMessage(3), delay=11)
        yield self.env.timeout(1)

        # This message is broadcast at time 4 and received at time 5.
        yield from self.broadcast(PayloadMessage(4))


class TestFramework(unittest.TestCase):
    def _test_node(self, receiver_node, expected):
        network = Network(Environment())
        network.add_node(receiver_node)
        network.add_node(SenderTestNode())
        network.run_all()

        self.assertEqual(list(network.node(0).handled), expected)

    def test_passive_node(self):
        # A PassiveNode subclass does not block on handling of
        # previous messages, so it handles each message immediately
        # when it is received.
        self._test_node(PassiveReceiverTestNode(), [
            (1, PayloadMessage(0), 1),
            (1, PayloadMessage(1), 2),
            (1, PayloadMessage(2), 3),
            (1, PayloadMessage(4), 5),
            (1, PayloadMessage(3), 14),
        ])

    def test_sequential_node(self):
        # A SequentialNode subclass *does* block on handling of
        # previous messages. It handles the messages as soon as
        # possible after they are received subject to that blocking,
        # so they will be handled at intervals of 3 time units.
        self._test_node(SequentialReceiverTestNode(), [
            (1, PayloadMessage(0), 1),
            (1, PayloadMessage(1), 4),
            (1, PayloadMessage(2), 7),
            (1, PayloadMessage(4), 10),
            (1, PayloadMessage(3), 14),
        ])
