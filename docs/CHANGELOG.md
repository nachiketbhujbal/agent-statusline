# Changelog

This project follows semantic versioning. Versions come from immutable Git tags
([ADR 0019](adrs/0019-release-tags-are-immutable.md)); there is no version
string in the source.

## Unreleased — 0.2.1

Installation and removal now mutate only configuration this package owns
([ADR 0020](adrs/0020-own-only-managed-configuration.md)).

- Preserve unrelated top-level settings, hook events, hook groups, matchers, and
  their order. Only the managed `statusLine` entry and the managed hook commands
  are added or removed.
- Fail closed on an unreadable, non-UTF-8, malformed, or non-object
  `settings.json`, and on a non-object `hooks` container. The existing file's
  bytes are left exactly as they were and no replacement is written.
- Preserve a `statusLine` entry or a `~/.claude/statusline` symlink whose
  ownership cannot be proven, rather than removing it on uninstall.
- Publish `settings.json` through a symlink instead of replacing it, and take
  the file mode from the resolved target. A configuration directory that
  symlinks into a dotfiles checkout keeps its indirection, and settings are no
  longer widened to the symlink's own permissions.
- Validate existing settings before any mutation, so a refused install leaves no
  checkout symlink and no backup behind — failing closed now means nothing
  changed at all.
- Back a valid existing settings file up before any applied mutation, publish
  atomically, and leave no temporary file behind if publication fails.
- Keep reinstallation idempotent: repeated installs never accumulate duplicate
  managed hooks.

## 0.2.0

First tagged release. Ten-row width-aware Claude Code status line, cost ledger,
cached probes, incremental transcript reading, both install shapes, and no
runtime dependencies.
