# ADR 0020: Mutate only configuration owned by agent-statusline

- Status: Accepted
- Date: 2026-08-26

## Context

Claude Code stores every extension's hooks in one `settings.json` file. The
original installer replaced the complete `SessionEnd`, `UserPromptSubmit`, and
`Stop` hook lists when installing or uninstalling this package. That silently
removed commands owned by other tools. It also treated an unreadable or
malformed settings file as an empty configuration, allowing a parse failure to
become broad data loss.

## Decision

Installation and removal identify and modify only this package's status-line
command, hook commands, and checkout symlink. Unrelated entries remain in their
original order and shape. A malformed or unreadable existing settings file is
an error: preserve it byte-for-byte and stop before writing.

Configuration writes use a same-directory private temporary file, durable
flush, atomic replacement, and a timestamped backup of an existing valid file.
Checkout commands use the selected Claude configuration directory rather than
assuming `~/.claude`.

## Consequences

Installing is composable with other Claude Code extensions and uninstalling is
ownership-safe. A damaged configuration requires explicit human repair instead
of an automatic reset. The installer needs focused regression tests for mixed
hook ownership, changed status lines, malformed JSON, custom configuration
directories, and symlinks it does not own.
