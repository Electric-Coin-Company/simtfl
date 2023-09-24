from simpy import Environment

from .network import Network
from .node import PingNode, PongNode


def run():
    env = Environment()
    network = Network(env, delay=4)
    for i in range(10):
        network.add_node(PongNode(i, env, network))

    network.add_node(PingNode(10, env, network))

    for i in range(network.num_nodes()):
        env.process(network.start_node(i))

    env.run()
