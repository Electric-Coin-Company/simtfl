from .util import skip

"""
Simulate the network layer.
"""
class Network:
    def __init__(self, env, nodes=None, delay=1):
        self.env = env
        self.nodes = nodes or []
        self.delay = delay

    def num_nodes(self):
        return len(self.nodes)

    def node(self, ident):
        return self.nodes[ident]

    def add_node(self, node):
        self.nodes.append(node)

    """(process) Start the node with the given ident."""
    def start_node(self, ident):
        node = self.node(ident)
        print(f"T{self.env.now:5d}: starting  {node}")
        return node.run()

    """
    (process) Sends a message to the given target ident, from the given sender ident.
    The delay is normally given by `self.delay` but can be overridden.
    """
    def send(self, sender, target, message, delay=None):
        if delay is None:
            delay = self.delay
        print(f"T{self.env.now:5d}: sending   {sender:2d} -> {target:2d} delay {delay:2d}: {message}")
        # Run `convey` in a new process without waiting.
        self.env.process(self.convey(delay, sender, target, message))
        return skip()

    """
    (process) Conveys a message to the given target ident, from the given sender ident,
    after waiting for the given transmission delay. This normally should not be called
    directly because it will only complete once the message has been handled.
    """
    def convey(self, delay, sender, target, message):
        yield self.env.timeout(delay)
        print(f"T{self.env.now:5d}: receiving {sender:2d} -> {target:2d} delay {delay:2d}: {message}")
        yield from self.nodes[target].receive(sender, message)
