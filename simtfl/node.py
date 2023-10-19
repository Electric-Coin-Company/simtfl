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

