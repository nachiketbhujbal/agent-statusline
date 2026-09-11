"""Expose the console-script interface through ``python -m``."""

import sys

from agent_statusline.cli import main

if __name__ == "__main__":
    sys.exit(main())
