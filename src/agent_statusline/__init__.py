"""A dense, width-aware status line for coding agents.

Layered so that only the acquisition layer is host-specific:

    paths       where machine-local state lives
    render      colours, units, bars, and the width-fitting row packer
    transcript  incremental parsing of a session .jsonl
    probes      cached subprocess/file probes
    ledger      cross-session cost accounting
    statusline  the Claude Code status line built from all of the above

`render`, `probes`, `ledger` and `paths` carry no Claude-specific assumptions;
see docs/PORTING.md.
"""
try:                                    # populated by hatch-vcs at build time
    from ._version import __version__
except Exception:                       # running straight from a checkout
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
