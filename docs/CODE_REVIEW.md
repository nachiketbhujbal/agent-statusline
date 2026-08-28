# Review findings

Findings proven on the release branch that fixes them. A row is recorded only
once the regression that demonstrates it exists in this repository.

| ID | Severity | Finding | Release | Status |
| --- | --- | --- | --- | --- |
| INSTALL-001 | High | Installation rewrote `settings.json` wholesale, discarding unrelated settings and unrelated hook entries in managed events. | 0.2.1 | Resolved by [ADR 0020](adrs/0020-own-only-managed-configuration.md) and ownership-preserving regressions |
| INSTALL-002 | High | A malformed, unreadable, non-UTF-8, or non-object settings file was overwritten instead of refused. | 0.2.1 | Resolved by fail-closed loading with byte-preservation regressions |
| INSTALL-003 | Medium | Uninstallation removed a `statusLine` entry and a `~/.claude/statusline` symlink it could not prove it owned. | 0.2.1 | Resolved by managed-command matching and preservation regressions |
| INSTALL-004 | Medium | Reinstallation appended managed hooks again, accumulating duplicates. | 0.2.1 | Resolved by removing managed hooks before writing, with a repeated-install regression |
| INSTALL-005 | High | Publishing replaced a symlinked `settings.json` with a regular file, orphaning the real file in a dotfiles checkout, and copied the symlink's own `0o777` bits onto the new settings file. | 0.2.1 | Resolved by publishing to the resolved target and taking its mode, with symlink and permission regressions |

| INSTALL-006 | Medium | A checkout install created the `~/.claude/statusline` symlink before validating `settings.json`, so refusing a malformed file still left a half-installed tree. | 0.2.1 | Resolved by validating settings before any mutation, with a nothing-changed regression |

INSTALL-005 and INSTALL-006 were found while reviewing the extracted commits rather than in the
original implementation, and is fixed here because it is the same ownership
property the release exists to guarantee.
