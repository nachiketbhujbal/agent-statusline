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

Ownership is decided by comparing an existing command against the exact command
this installer would write into the selected configuration directory. A trailing
path fragment is not sufficient evidence of ownership: `statusline` is the most
natural directory name another status line would choose, and claiming it means
deleting it.

Configuration writes use a private temporary file in the target's own directory,
durable flush, atomic replacement, and a timestamped backup of an existing valid
file. A `settings.json` that is a symlink is published *through*, so the file the
user actually edits is the file that changes, and the mode is taken from that
resolved file rather than from the link. Resolution is confined to the selected
configuration directory: a link pointing outside it is refused, naming the
resolved path, because following it would let an installer write anywhere the
user happened to point a link.

Checkout commands use the selected Claude configuration directory rather than
assuming `~/.claude`.

## Consequences

Installing is composable with other Claude Code extensions and uninstalling is
ownership-safe. A damaged configuration requires explicit human repair instead
of an automatic reset. The installer needs focused regression tests for mixed
hook ownership, changed status lines, malformed JSON, custom configuration
directories, and symlinks it does not own.
