#!/usr/bin/env python3
"""Install from a checkout, with no install step of its own.

    python3 install.py [--dry-run|--uninstall]

Equivalent to `agent-statusline install` once the package is installed; this
exists so a fresh clone works on the system Python with nothing set up yet.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))

from agent_statusline.installer import run

if __name__ == "__main__":
    args = sys.argv[1:]
    unknown = [a for a in args if a not in ("--dry-run", "--uninstall")]
    if unknown:
        sys.exit(f"unknown option: {unknown[0]}")
    sys.exit(run(dry_run="--dry-run" in args, uninstall="--uninstall" in args))
