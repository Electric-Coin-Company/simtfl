from .util import skip


class Network:
    """
    Simulate the network layer.
    """
    def __init__(self, env, nodes=None, delay=1):
        """
        Constructs a Network with the given `simpy.Environment`, and optionally
        a set of initial nodes and a message delay.
        """
        self.env = env
        self.nodes = nodes or []
        self.delay = delay

    def num_nodes(self):
        """
        Returns the number of nodes.
        """
        return len(self.nodes)

    def node(self, ident):
        """
        Returns the node with the given integer ident.
        """
        return self.nodes[ident]

    def add_node(self, node):
        """
        Adds a node with the next available ident.
        """
        ident = self.num_nodes()
        self.nodes.append(node)
        node.initialize(ident, self.env, self)

    def start_node(self, ident):
        """
        (process) Start the node with the given ident.
        """
        node = self.node(ident)
        print(f"T{self.env.now:5d}: starting  {ident:2d}: {node}")
        return node.run()

    def start_processes(self):
        """
        Start a process for each node.
        """
        print()
        for i in range(self.num_nodes()):
            self.env.process(self.start_node(i))

    def run_all(self, *args, **kwargs):
        """
        Convenience method to start a process for each node, then start
        the simulation. Takes the same arguments as `simpy.Environment.run`.
        """
        self.start_processes()
        self.env.run(*args, **kwargs)

    def send(self, sender, target, message, delay=None):
        """
        (process) Sends a message to the node with ident `target`, from the node
        with ident `sender`. The message delay is normally given by `self.delay`,
        but can be overridden by the `delay` parameter.
        """
        if delay is None:
            delay = self.delay
        print(f"T{self.env.now:5d}: sending   {sender:2d} -> {target:2d} delay {delay:2d}: {message}")

        # Run `convey` in a new process without waiting.
        self.env.process(self.convey(delay, sender, target, message))

        # Sending is currently instantaneous.
        # TODO: make it take some time on the sending node.
        return skip()

    def convey(self, delay, sender, target, message):
        """
        (process) Conveys a message to the node with ident `target`, from the node
        with ident `sender`, after waiting for the given transmission delay.
        This normally should not be called directly because it *may* only complete
        after the message has been handled by the target node. The caller should
        not depend on when it completes.
        """
        yield self.env.timeout(delay)
        print(f"T{self.env.now:5d}: receiving {sender:2d} -> {target:2d} delay {delay:2d}: {message}")
        yield from self.nodes[target].receive(sender, message)
