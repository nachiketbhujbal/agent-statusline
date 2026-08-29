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
`/opt/foreign/agent-statusline` belonging to someone else is never claimed. The
checkout shape names two things, and both must match exactly: the script path
under the selected configuration directory, and the interpreter running it.
Accepting any program whose name merely started with "python" alongside the
right script path claimed a foreign interpreter's command as ours; the
interpreter must be the exact `sys.executable` this installation runs under,
with the one documented exception below.

The one command shape not written by the current installer that is still claimed
is the released v0.2.0 form, which embedded a literal `~/.claude/statusline/...`
argument and a literal bare `python3` interpreter, relying on `PATH`. A leading
`~` is expanded before the script-path comparison, so those entries are
recognized only when they resolve to the very directory this installation
manages, and the literal string `python3` -- not any interpreter whose name
starts with "python" -- is the one interpreter exception, recognized only
alongside that legacy script-path form. Without either half, upgrading a
v0.2.0 installation would stack a second set of hooks beside the first and
uninstalling would leave the originals behind.

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
any step of the walk from the filesystem root down to it, and the temporary file
is created, permissioned, and renamed relative to that descriptor. The walk
covers the configuration root itself and every component above it, not only the
components below it -- a directory that is opened by its resolved *name* alone,
even once, can still be a symlink an attacker swapped in after the name was
resolved and before the open ran. A second `realpath()` check would only re-run
the race it is meant to detect. Where the platform cannot offer
directory-relative operations, publication refuses rather than falling back to
an unchecked path. This same confinement decision is made before existing
settings are read, not only before they are written, so an out-of-tree symlink
target is refused before its content ever reaches memory.

A raw file descriptor is closed exactly once on every path through publication,
success or failure. Setting its permissions is not yet safe to hand off to
Python's buffered file object -- that handoff is what gives the descriptor an
owner that closes it automatically -- so a failure in between closes it
explicitly rather than leaving it open past the error that reports the failure.

Binding the configuration directory correctly at one point in an install or
uninstall does not protect a later point that independently re-derives it from
`cdir`'s pathname -- refusing to follow a symlink there does nothing against an
*ordinary* directory placed at that pathname between the two. So the directory
is bound exactly once per install or uninstall, immediately after it is
confirmed (or created) to exist, and every read, backup, link mutation, and
publication for the rest of that call reuses the same descriptor rather than
re-opening the location by name again. What this closes is broader than
publication alone: the initial settings read and the backup copy, which used
to be made by plain pathname outside the binding publication used, now share
it too, so they carry the same guarantee rather than a narrower one.

Install and uninstall each perform two mutations with no shared commit point:
the checkout symlink, and the settings rewrite. Neither can be made to succeed
or fail together with the other, so instead the link's state is captured before
either mutation begins, and an expected failure in the mutation that runs
second rolls the link back to what it was -- a pre-existing link restored to its
original target, or a link this run just created removed. This does not make
the pair atomic; it makes the two outcomes that were possible before this --
link changed, settings unchanged, or the reverse -- resolve back to a single
consistent state on failure, in the common case. Restoration is itself a
filesystem operation, so it is not guaranteed: if it fails too, that failure is
reported alongside the original one rather than silently discarded, naming the
link that may no longer match settings, so a double failure is reported rather
than mistaken for the single-failure case that does resolve cleanly.

Ownership of a hook applies to the hook entry, not to other fields on the group
that contains it. A group carrying a user's `matcher` alongside a managed hook
keeps that `matcher` when its last managed hook is removed, with `"hooks": []`
left in its place; a group with nothing but managed hooks is still dropped
entirely once emptied, because it then carries no information this release
promises to preserve.

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
directories, symlinks it does not own, v0.2.0 upgrade paths, publication that is
redirected after confinement is checked (at the configuration root as well as
below it, by an ordinary directory swap as well as by a symlink), a foreign
interpreter paired with the expected checkout script path, an interrupted
install or uninstall that must roll a partial link change back (including the
case where that rollback itself fails), and a hook group carrying fields this
package never claimed.

A finding recorded here in an earlier round as explicitly unresolved -- a race
between the confinement decision for an existing `settings.json` and the read
that follows it -- is substantially closed now that the read shares the same
bound descriptor as publication, rather than merely being ordered after a
repeated path-based check. A deliberate same-user pathname race between two of
this installer's own filesystem operations, of which this was one instance, is
outside the practical local threat model this project targets ([ADR
0031](0031-practical-local-threat-model.md)) and is not treated here as an
open release-blocking defect.
