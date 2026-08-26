#!/usr/bin/env python3
"""TEMPORARY: stamp the time a user prompt was submitted.

Stopgap until the server-side flag `tengu_silk_hinge` enables Claude Code's
native `showMessageTimestamps`. Delete this hook once timestamps appear
natively -- see docs/adrs/0015-timestamp-hooks-are-a-stopgap.md.
"""
import json
import sys
import time


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass
    print(json.dumps({"systemMessage": time.strftime("[%Y-%m-%d %H:%M:%S]")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
