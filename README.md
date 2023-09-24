# Trailing Finality Layer Simulator

This is an experimental simulator for research into a potential
[Trailing Finality Layer](https://electriccoin.co/blog/the-trailing-finality-layer-a-stepping-stone-to-proof-of-stake-in-zcash/)
for Zcash.

Note the caveats: *experimental*, *simulator*, *research*, *potential*.

## Instructions

1. Install `poetry`:

       sudo apt install python3-poetry

   or see [poetry's installation docs](https://python-poetry.org/docs/)
   if not on Debian/Ubuntu.

2. Install dependencies:

       poetry install

3. Run the script:

       poetry run simtfl

## Programming patterns

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

## License

This software is provided under the terms of the [MIT License](LICENSE).
