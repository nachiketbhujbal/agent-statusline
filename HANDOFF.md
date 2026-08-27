# agent-statusline handoff

## Current state

- `main` is released as `v0.2.0`.
- The active `v0.3.0` hardening work is owned by the
  `codex/hardening/v0.3.0-production-readiness` branch.
- The branch is pushed and tracks its namesake remote at `d991b04`; no pull
  request is open and no hosted run was triggered by the branch push.
- Hosted GitHub Actions workflows are administratively disabled while the
  private-account allowance is unavailable. Use the complete locked local gate;
  do not interpret absent hosted checks as evidence.
- Runtime dependencies remain empty and versions remain Git-tag-derived.

## Approved compatibility boundary

The Claude Code renderer retains ten rows in this order:

`PROJECT`, `MODEL`, `CONTEXT`, `USAGE`, `COST`, `SYSTEM`, `TOOLS`, `CACHE`,
`TOKENS`, `TIMING`.

Their existing fields and priority order remain approved. Hardening may improve
acquisition, accounting, privacy, concurrency, validation, and width handling,
but a display removal or reordering requires explicit maintainer approval.

Codex currently exposes only a declarative built-in widget list. It cannot run
the Claude Python renderer. `docs/PORTING.md` records the verified boundary and
the recommended native-widget mapping.

## v0.3.0 work

This ships as one minor release. The installer, accounting, cache, and
concurrency changes share the production-hardening purpose, and the storage
service is their common safety dependency. Performance work begins in 0.3.1;
host-boundary architecture begins in 0.3.2.

Completed on the branch:

- Configuration-owner-safe install and uninstall with malformed-input refusal.
- Private, locked, atomic runtime state.
- Timestamped lifetime-cost deltas, non-accrual seeds, assistant-time
  attribution, exact lower-bound rendering, and 35-day retention for the
  approved rolling cost windows.
- Locked uv, pre-commit, Ruff, Black, mypy, coverage, and build tooling.
- Session-scoped process probes plus bounded probe, transcript, and rate-limit
  observation state under ADRs 0024 and 0025.

Still required before the pull request is merge-ready:

- Finish rendering safety for terminal cell width and control characters.
- Reconcile README and field documentation with the actual Python boundary,
  test gate, installer semantics, and cost migration.
- Replace moving workflow action tags and decide the post-allowance hosted or
  self-hosted trigger policy without enabling a run now.
- Complete the review ledger, privacy sweep, wheel/sdist inspection, installed-
  wheel smoke test, and independent adversarial review.

## Required verification

Follow the release-equivalent gate in `AGENTS.md`. Preview the renderer only
with a disposable `AGENT_STATUSLINE_STATE`; never replay a saved payload against
the live ledger.

## Cross-assistant coordination

ADR 0026 governs concurrent work: one branch owner applies changes and one
independent reviewer reports findings. `AGENTS.md` is authoritative;
`HANDOFF.md` is the tracked current-state record. Private assistant notes are
supporting context, not a competing source of project truth.
