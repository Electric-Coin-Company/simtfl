"""
A simple demo of message passing.
"""

from simpy import Environment

from .message import PayloadMessage
from .network import Network
from .node import PassiveNode, SequentialNode


class Ping(PayloadMessage):
    """
    A ping message.
    """
    pass


class Pong(PayloadMessage):
    """
    A pong message.
    """
    pass


class PingNode(PassiveNode):
    """
    A node that sends pings.
    """
    def run(self):
        """
        (process) Sends two Ping messages to every node.
        """
        for i in range(self.network.num_nodes()):
            yield from self.send(i, Ping(i))
            yield self.env.timeout(1)
            yield from self.send(i, Ping(i))
            yield self.env.timeout(2)


class PongNode(SequentialNode):
    """
    A node that responds to pings sequentially.
    """
    def handle(self, sender, message):
        """
        (process) Handles a Ping message by sending back a Pong message with the
        same payload.
        """
        if isinstance(message, Ping):
            yield self.env.timeout(5)
            yield from self.send(sender, Pong(message.payload))
        else:
            yield from super().handle(sender, message)


def run():
    """
    Runs the demo.
    """
    env = Environment()
    network = Network(env, delay=4)
    for i in range(10):
        network.add_node(PongNode(i, env, network))

    network.add_node(PingNode(10, env, network))

    for i in range(network.num_nodes()):
        env.process(network.start_node(i))

    env.run()
