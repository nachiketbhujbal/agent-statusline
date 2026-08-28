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
  the file mode from the resolved target, so a link inside the configuration
  directory keeps its indirection and settings are no longer widened to the
  symlink's own permissions. A link resolving outside the configuration
  directory is refused, with the resolved path named, rather than followed.
- Decide ownership by the exact commands this installer writes: the checkout
  form is anchored to the selected configuration directory, and the installed
  form to the absolute path of this installation's console script. A third-party
  status line or hook is no longer claimed — neither one whose files live in a
  directory named `statusline`, nor one whose program is also named
  `agent-statusline` — and so is no longer removed on uninstall.
- Recognize the `~/.claude/statusline/...` commands written by the released
  v0.2.0 installer, so upgrading from it replaces those entries instead of
  stacking a second set of hooks beside them, and uninstalling removes them.
  The tilde is expanded before an otherwise exact comparison, so a lookalike
  path elsewhere is still not claimed.
- Refuse to install over configuration this package does not own. A `statusLine`
  belonging to another tool, or a `~/.claude/statusline` symlink pointing at one,
  stops the install with an explanation instead of being overwritten; only one
  status line can be configured, so replacing yours would be unrecoverable.
  Reinstalling over this package's own entry and link stays idempotent.
- Validate every schema condition an operation depends on — the settings file's
  readability and top-level type, the `hooks` container's type, and each managed
  event's container type — before the first mutation on both the install and the
  uninstall path. A refusal now leaves no checkout symlink, no backup, no
  temporary file, and no replacement behind. A non-list event container such as
  `{"SessionEnd": "valuable"}` is refused rather than raising `AttributeError`
  partway through.
- Treat an uninstall that owns nothing as a true no-op: no `{}` is created, no
  backup is written, and unrelated settings are not rewritten. Empty hook groups
  and events belonging to other tools keep their shape rather than being
  normalized away.
- Report expected filesystem failures — a read-only or missing configuration
  directory, a failed backup, a failed publication or symlink — as a concise
  error instead of a traceback, preserving the original bytes and leaving no
  temporary file behind.
- Run installation verification against a uniquely created system temporary
  directory. It previously used a fixed `<config>/.verify-state` path and always
  removed it recursively, so an install deleted a pre-existing directory of that
  name and its contents. As a result `--dry-run` now genuinely writes nothing:
  it no longer creates the configuration directory.
- Bind settings publication to an opened directory descriptor, reached without
  following a symlink at any step below the configuration directory, and create,
  permission, and rename the temporary file relative to it. Confining a path and
  then writing through that same path left a window in which swapping a checked
  directory for a symlink redirected publication onto an unrelated file outside
  the configuration directory.
- Back a valid existing settings file up before any applied mutation, publish
  atomically, and leave no temporary file behind if publication fails.
- Keep reinstallation idempotent: repeated installs never accumulate duplicate
  managed hooks.

One deliberate exception to the ownership rule: `showMessageTimestamps` is set
to `true` when absent ([ADR 0015](adrs/0015-timestamp-hooks-are-a-stopgap.md))
and is **not** removed on uninstall, because a value already present cannot be
distinguished from one this installer added. It is stated here rather than
folded into the broader claim.

## 0.2.0

First tagged release. Ten-row width-aware Claude Code status line, cost ledger,
cached probes, incremental transcript reading, both install shapes, and no
runtime dependencies.
