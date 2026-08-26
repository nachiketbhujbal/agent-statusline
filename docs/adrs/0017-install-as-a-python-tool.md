# ADR 0017: Install as a Python tool, and keep the checkout path for development

- Status: Accepted
- Date: 2026-08-26
- Supersedes: [ADR 0003](0003-install-by-one-symlink.md)

## Context

ADR 0003 made a symlink from a working tree the only way to install, which
meant every user had to clone the repository and keep it somewhere permanent —
a reasonable ask of a contributor and an unreasonable one of someone who just
wants the status line. Packaging already produced a valid wheel with a console
script, so the capability existed and only the wiring assumed a checkout.

## Decision

Support both shapes and detect which one applies rather than asking. An
installed package — `uv tool install`, `pipx install`, `pip install` — wires
`settings.json` to the `agent-statusline` console script by absolute path and
symlinks nothing. A checkout keeps the ADR 0003 symlink, so edits take effect
with no reinstall. `checkout_root()` distinguishes them by whether a
`pyproject.toml` sits above the package.

One console script carries every entry point as subcommands: bare
`agent-statusline` renders, plus `install`, `uninstall`, `hook <name>`,
`ledger`, and `version`.

## Consequences

Installing no longer requires a clone or a permanent checkout, and `uv tool
upgrade` replaces `git pull` for anyone not developing. The absolute path
matters: Claude Code spawns the status line and hooks with an environment that
need not contain the tool directory, so resolving through `PATH` at render time
would be fragile.

Dispatch is hand-rolled and the no-argument case returns before importing
anything else, because that case runs several times a second (ADR 0006).
`install.py` remains at the repository root as a stdlib-only bootstrap, so a
fresh clone still works on the system Python with nothing set up (ADR 0004).
