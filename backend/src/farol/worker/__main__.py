"""Entrada do worker: `python -m farol.worker [coletar --alertas]`."""

import sys

from farol.worker.comando import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
