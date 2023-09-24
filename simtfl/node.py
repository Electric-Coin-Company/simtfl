from .message import Ping, Pong
from .util import skip

"""
A node that sends no messages and does nothing with received messages.
"""
class PassiveNode:
    """Constructs a PassiveNode with the given simpy Environment and network."""
    def __init__(self, ident, env, network):
        self.ident = ident
        self.env = env
        self.network = network

    def __str__(self):
        return f"{self.ident:2d}: {self.__class__.__name__}"

    """(process) This can be overridden to intercept messages sent by this node."""
    def send(self, target, message):
        return self.network.send(self.ident, target, message)

    """(process) This can be overridden to intercept messages received by this node."""
    def receive(self, sender, message):
        return self.handle(sender, message)

    """(process) Handles a message by doing nothing."""
    def handle(self, message, sender):
        return skip()

    """(process) Runs by doing nothing."""
    def run(self):
        return skip()

"""
A node that sends pings.
"""
class PingNode(PassiveNode):
    """
    (process) Sends a Ping message to every node.
    """
    def run(self):
        for i in range(self.network.num_nodes()):
            yield from self.send(i, Ping(i))
            yield self.env.timeout(3)

"""
A node that responds to pings.
"""
class PongNode(PassiveNode):
    """
    (process) Handles a Ping message by sending back a Pong message with the same payload.
    """
    def handle(self, sender, message):
        if isinstance(message, Ping):
            yield self.env.timeout(5)
            yield from self.send(sender, Pong(message.payload))
        else:
            yield from super().handle(sender, message)