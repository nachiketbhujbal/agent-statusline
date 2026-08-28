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
deleting it. Neither is a bare program name: the installed shape is matched
against the absolute path of *this* installation's console script, so a
`/opt/foreign/agent-statusline` belonging to someone else is never claimed.

The one command shape not written by the current installer that is still claimed
is the released v0.2.0 form, which embedded a literal `~/.claude/statusline/...`
argument. A leading `~` is expanded before the comparison, so those entries are
recognized only when they resolve to the very directory this installation
manages. Without that, upgrading a v0.2.0 installation would stack a second set
of hooks beside the first and uninstalling would leave the originals behind.

Installation refuses rather than overwrites. Because `settings.json` holds
exactly one `statusLine`, installing over one this package does not own destroys
it irrecoverably; the same is true of replacing a `statusline` symlink pointing
at another package. Both are refused, and reinstalling over our own entry or
link stays idempotent.

That refusal is keyed on the *entry*, not on a command parsed out of it. An
entry whose shape the matcher cannot read is one whose ownership certainly
cannot be proven, and overwriting it loses exactly as much as overwriting a
well-formed one. Only an absent or `null` entry counts as nothing to protect.

Every condition that can refuse is checked before the first mutation -- the
settings file's readability, its top-level type, the `hooks` container's type,
and the type of each managed event's container. Refusing after a backup exists,
or after the checkout symlink has been created, is not "nothing changed"; it is a
half-installed tree behind a failure that promised to be inert.

Configuration writes use a private temporary file in the target's own directory,
durable flush, atomic replacement, and a timestamped backup of an existing valid
file. A `settings.json` that is a symlink is published *through*, so the file the
user actually edits is the file that changes, and the mode is taken from that
resolved file rather than from the link. Resolution is confined to the selected
configuration directory: a link pointing outside it is refused, naming the
resolved path, because following it would let an installer write anywhere the
user happened to point a link.

Confinement is a decision about a path, so it is bound to an object before it is
acted on: the receiving directory is opened once, without following a symlink at
any step below the configuration directory, and the temporary file is created,
permissioned, and renamed relative to that descriptor. A second `realpath()`
check would only re-run the race it is meant to detect. Where the platform
cannot offer directory-relative operations, publication refuses rather than
falling back to an unchecked path.

Verification state lives in a uniquely created system temporary directory that
is removed again. A fixed path inside the configuration directory made a normal
install recursively delete whatever already sat there, and made a dry run create
the configuration directory it promised not to write to.

Checkout commands use the selected Claude configuration directory rather than
assuming `~/.claude`.

### One stated exception

`showMessageTimestamps` is set to `true` when absent (ADR 0015) and is
deliberately *not* removed on uninstall. A value already present in a user's
settings cannot be distinguished from one this installer added, so reclaiming it
risks turning off something the user chose. This is a real deviation from "only
what it owns" and is recorded here, in the changelog, and in the README rather
than folded into the broader ownership claim.

## Consequences

Installing is composable with other Claude Code extensions and uninstalling is
ownership-safe. A damaged configuration requires explicit human repair instead
of an automatic reset. Someone already running another status line must remove it
themselves before installing this one, which is the deliberate cost of never
destroying it. The installer needs focused regression tests for mixed hook
ownership, changed status lines, malformed JSON, custom configuration
directories, symlinks it does not own, v0.2.0 upgrade paths, and publication
that is redirected after confinement is checked.
