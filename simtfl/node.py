from collections import deque

from .util import skip


class PassiveNode:
    """
    A node that sends no messages and does nothing with received messages.
    This class is intended to be subclassed.
    """
    def initialize(self, ident, env, network):
        """
        Initializes a PassiveNode with the given ident, simpy Environment,
        and network. Nodes are initialized when they are added to a network.
        """
        self.ident = ident
        self.env = env
        self.network = network

    def __str__(self):
        return f"{self.__class__.__name__}"

    def send(self, target, message):
        """
        (process) This method can be overridden to intercept messages being sent
        by this node. The implementation in this class calls `self.network.send`.
        """
        return self.network.send(self.ident, target, message)

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
    A node that processes messages sequentially.
    """
    def initialize(self, ident, env, network):
        """
        Initializes a SequentialNode with the given simpy Environment and network.
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
        self.received = deque()

    def handle(self, sender, message):
        self.received.append((sender, message, self.env.now))
        yield self.env.timeout(3)


class SequentialReceiverTestNode(SequentialNode):
    def __init__(self):
        super().__init__()
        self.received = deque()

    def handle(self, sender, message):
        self.received.append((sender, message, self.env.now))
        yield self.env.timeout(3)


class SenderTestNode(PassiveNode):
    def run(self):
        for i in range(3):
            yield from self.send(0, PayloadMessage(i))
            yield self.env.timeout(1)


class TestFramework(unittest.TestCase):
    def _test_node(self, receiver_node, expected):
        network = Network(Environment())
        network.add_node(receiver_node)
        network.add_node(SenderTestNode())
        network.run_all()

        self.assertEqual(list(network.node(0).received), expected)

    def test_passive_node(self):
        self._test_node(PassiveReceiverTestNode(), [
            (1, PayloadMessage(0), 1),
            (1, PayloadMessage(1), 2),
            (1, PayloadMessage(2), 3),
        ])

    def test_sequential_node(self):
        self._test_node(SequentialReceiverTestNode(), [
            (1, PayloadMessage(0), 1),
            (1, PayloadMessage(1), 4),
            (1, PayloadMessage(2), 7),
        ])
