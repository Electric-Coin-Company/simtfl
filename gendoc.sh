#!/bin/sh

set -eu

poetry run pdoc simtfl -o apidoc --no-include-undocumented -d markdown
