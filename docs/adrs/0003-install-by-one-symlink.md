# ADR 0003: Install by one symlink from the agent's config directory

- Status: Superseded by [ADR 0017](0017-install-as-a-python-tool.md)
- Date: 2026-08-26

## Context

The repository lives outside `~/.claude`, but Claude Code reads its status-line
command and hook paths from `settings.json` there. Copying files in would fork
the source of truth; writing absolute repository paths into `settings.json`
would leave `~/.claude` unable to describe its own setup.

## Decision

`install.py` creates one symlink, `~/.claude/statusline` pointing at
`<repo>/src/agent_statusline`, and writes settings that refer only to
`~/.claude/statusline/...`. Modules locate their siblings through
`os.path.realpath(__file__)`, so execution works identically through the symlink
or by absolute path.

## Consequences

Updating is `git pull`; there is nothing to re-copy. `settings.json` stays
portable between machines. The installer is idempotent, backs the file up before
rewriting it, preserves unrelated settings, and offers `--dry-run` and
`--uninstall`.

## Superseded

[ADR 0017](0017-install-as-a-python-tool.md) keeps this symlink for
checkouts but makes an installed package the default shape, so installing no
longer requires cloning the repository.
