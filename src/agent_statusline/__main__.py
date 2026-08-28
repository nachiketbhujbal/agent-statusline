"""Expose the same interface through `python -m` and the console script."""

import sys

from agent_statusline.cli import main

if __name__ == "__main__":
    sys.exit(main())
