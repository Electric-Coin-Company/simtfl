# Programming patterns

The code makes use of the [simpy](https://simpy.readthedocs.io/en/latest/)
discrete event simulation library. This means that functions representing
processes are implemented as generators, so that the library can simulate
timeouts and asynchronous communication (typically faster than real time).

We use the convention of putting "(process)" in the doc comment of these
functions. They either must use the `yield` construct, *or* return the
result of calling another "(process)" function (not both).

Objects that implement processes typically hold the `simpy.Environment` in
an instance variable `self.env`.

To wait for another process `f()` before continuing, use `yield from f()`.
(If it is the last thing to do in a function with no other `yield`
statements, `return f()` can be used as an optimization.)

A "(process)" function that does nothing should `return skip()`, using
`simtfl.util.skip`.
