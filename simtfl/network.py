"""
Framework for message passing in a network of nodes.
"""


from __future__ import annotations
from typing import Optional
from numbers import Number

from simpy import Environment
from simpy.events import Timeout, Process

from .message import Message
from .util import skip, ProcessEffect
from .logging import Logger


class Node:
    """
    A base class for nodes. This class is intended to be subclassed.
    """

    def initialize(self, ident: int, env: Environment, network: Network):
        """
        Initializes a `Node` with the given ident, `simpy.Environment`, and `Network`.
        Nodes are initialized when they are added to a `Network`. The implementation
        in this class sets the `ident`, `env`, and `network` fields.
        """
        self.ident = ident
        self.env = env
        self.network = network

    def __str__(self):
        return f"{self.__class__.__name__}"

    def log(self, event: str, detail: str):
        """
        Logs an event described by `event` and `detail` for this node.
        """
        self.network.log(self.ident, event, detail)

    def send(self, target: int, message: Message, delay: Optional[Number]=None) -> ProcessEffect:
        """
        (process) This method can be overridden to intercept messages being sent
        by this node. The implementation in this class calls `self.network.send`
        with this node as the sender.
        """
        return self.network.send(self.ident, target, message, delay=delay)

    def broadcast(self, message: Message, delay: Optional[Number]=None) -> ProcessEffect:
        """
        (process) This method can be overridden to intercept messages being broadcast
        by this node. The implementation in this class calls `self.network.broadcast`
        with this node as the sender.
        """
        return self.network.broadcast(self.ident, message, delay=delay)

    def receive(self, sender: int, message: Message) -> ProcessEffect:
        """
        (process) This method can be overridden to intercept messages being received
        by this node. The implementation in this class calls `self.handle`.
        """
        return self.handle(sender, message)

    def handle(self, sender: int, message: Message) -> ProcessEffect:
        """
        (process) Handles a message. Subclasses must implement this method.
        """
        raise NotImplementedError

    def run(self) -> ProcessEffect:
        """
        (process) Runs the node. Subclasses must implement this method.
        """
        raise NotImplementedError


class Network:
    """
    Simulate the network layer.
    """
    def __init__(self, env: Environment, nodes: Optional[list[Node]]=None, delay: Number=1,
                 logger: Logger=Logger()):
        """
        Constructs a `Network` with the given `simpy.Environment`, and optionally
        a set of initial nodes, message propagation delay, and logger.
        """
        self.env = env
        self.nodes = nodes or []
        self.delay = delay
        self._logger = logger
        logger.header()

    def log(self, ident: int, event: str, detail: str) -> None:
        """
        Logs an event described by `event` and `detail` for the node with the
        given `ident`.
        """
        self._logger.log(self.env.now, ident, event, detail)

    def num_nodes(self) -> int:
        """
        Returns the number of nodes.
        """
        return len(self.nodes)

    def node(self, ident: int) -> Node:
        """
        Returns the node with the given integer ident.
        """
        return self.nodes[ident]

    def add_node(self, node: Node) -> None:
        """
        Adds a node with the next available ident.
        """
        ident = self.num_nodes()
        self.nodes.append(node)
        node.initialize(ident, self.env, self)

    def _start(self, node: Node) -> None:
        """
        Starts a process for the given node (which is assumed to
        have already been added to this `Network`).
        """
        self.log(node.ident, "start", str(node))
        Process(self.env, node.run())

    def start_node(self, ident: int) -> None:
        """
        Starts a process for the node with the given ident.
        A given node should only be started once.
        """
        self._start(self.nodes[ident])

    def start_all_nodes(self) -> None:
        """
        Starts a process for each node.
        A given node should only be started once.
        """
        for node in self.nodes:
            self._start(node)

    def run_all(self, *args, **kwargs) -> None:
        """
        Convenience method to start a process for each node, then start
        the simulation. Takes the same arguments as `simpy.Environment.run`.
        """
        self.start_all_nodes()
        self.env.run(*args, **kwargs)

    def send(self, sender: int, target: int, message: Message, delay: Optional[Number]=None) -> ProcessEffect:
        """
        (process) Sends a message to the node with ident `target`, from the node
        with ident `sender`. The message propagation delay is normally given by
        `self.delay`, but can be overridden by the `delay` parameter.
        """
        if delay is None:
            delay = self.delay
        self.log(sender, "send", f"to   {target:2d} with delay {delay:2d}: {message}")

        # Run `convey` in a new process without waiting.
        Process(self.env, self.convey(delay, sender, target, message))

        # Sending is currently instantaneous.
        # TODO: make it take some time on the sending node.
        return skip()

    def broadcast(self, sender: int, message: Message, delay: Optional[Number]=None) -> ProcessEffect:
        """
        (process) Broadcasts a message to every other node. The message
        propagation delay is normally given by `self.delay`, but can be
        overridden by the `delay` parameter.
        """
        if delay is None:
            delay = self.delay
        self.log(sender, "broadcast", f"to    * with delay {delay:2d}: {message}")

        # Run `convey` in a new process for each node.
        for target in range(self.num_nodes()):
            if target != sender:
                Process(self.env, self.convey(delay, sender, target, message))

        # Broadcasting is currently instantaneous.
        # TODO: make it take some time on the sending node.
        return skip()

    def convey(self, delay: Number, sender: int, target: int, message: Message) -> ProcessEffect:
        """
        (process) Conveys a message to the node with ident `target`, from the node
        with ident `sender`, after waiting for the given message propagation delay.
        This normally should not be called directly because it *may* only complete
        after the message has been handled by the target node. The caller should
        not depend on when it completes.
        """
        yield Timeout(self.env, delay)
        self.log(target, "receive", f"from {sender:2d} with delay {delay:2d}: {message}")
        yield from self.nodes[target].receive(sender, message)
