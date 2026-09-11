#!/usr/bin/env python3
"""`agent-statusline` -- one entry point for rendering, installing, and hooks.

Dispatch is hand-rolled rather than argparse-based, and the no-argument case
returns before importing anything else it does not need. That case is the hot
one: Claude Code spawns this process several times a second to redraw, and every
avoided import is time the status line is not on screen (ADR 0006).
"""
import sys

USAGE = """agent-statusline -- a dense, width-aware status line for coding agents

  agent-statusline                     render a status line from a payload on stdin
  agent-statusline install [--dry-run] wire it into Claude Code's settings.json
  agent-statusline uninstall           remove the settings entries and symlink
  agent-statusline hook <name>         run a hook (session-end, context-guard,
                                       timestamp-user, timestamp-stop)
  agent-statusline ledger [...]        inspect or close cost-ledger rows
  agent-statusline selftest            verify rendering using isolated synthetic state
  agent-statusline version             print the version
"""

HOOKS = {
    "session-end": "session_end",
    "context-guard": "context_guard",
    "timestamp-user": "timestamp_user",
    "timestamp-stop": "timestamp_stop",
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    # Hot path: no arguments means render, and nothing else is imported.
    if not argv:
        from agent_statusline.statusline import main as render

        render()
        return 0

    cmd, rest = argv[0], argv[1:]

    if cmd in ("-h", "--help", "help"):
        print(USAGE)
        return 0

    if cmd in ("-V", "--version", "version"):
        from agent_statusline import __version__

        print(__version__)
        return 0

    if cmd == "render":
        from agent_statusline.statusline import main as render

        render()
        return 0

    if cmd in ("install", "uninstall"):
        from agent_statusline import installer

        unknown = [a for a in rest if a != "--dry-run"]
        if unknown:
            print(f"unknown option: {unknown[0]}", file=sys.stderr)
            return 2
        return installer.run(dry_run="--dry-run" in rest, uninstall=cmd == "uninstall")

    if cmd == "hook":
        if not rest or rest[0] not in HOOKS:
            print(f"usage: agent-statusline hook {{{','.join(HOOKS)}}}", file=sys.stderr)
            return 2
        mod = __import__(f"agent_statusline.hooks.{HOOKS[rest[0]]}", fromlist=["main"])
        return mod.main()

    if cmd == "ledger":
        from agent_statusline import ledger

        sys.argv = ["agent-statusline ledger", *rest]
        return ledger._main()

    if cmd == "selftest":
        if rest:
            print(f"unknown option: {rest[0]}", file=sys.stderr)
            return 2
        from agent_statusline import selftest

        return selftest.run()

    print(f"unknown command: {cmd}\n\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
