#!/bin/sh

set -eu
cd -P -- "$(dirname -- "$(command -v -- "$0")")"

echo Running poetry check...
poetry check

echo Running flake8...
poetry run flake8

echo Running pyanalyze...
poetry run pyanalyze .

echo
echo Running unit tests...
args="${*:---buffer}"
poetry run python -m unittest discover -s simtfl -t . -p '[a-z]*.py' --verbose ${args}
