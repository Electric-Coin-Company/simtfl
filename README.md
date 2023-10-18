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

3. Run the demo (currently just an example of message passing):

       poetry run demo

## Documentation

Design documentation is under the `doc/` directory:

* [Programming patterns for use of simpy](doc/patterns.md).

## Contributing

Please check `poetry run flake8` before submitting a PR.

## License

This software is provided under the terms of the [MIT License](LICENSE).
