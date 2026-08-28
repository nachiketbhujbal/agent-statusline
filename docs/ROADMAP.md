# Roadmap

Promoted, release-scoped work belongs here. Evidence and open questions that do
not yet justify implementation remain in `RESEARCH.md` or `DEFERRED.md`.

## Release sequence

| Release | Primary purpose | Status |
| --- | --- | --- |
| 0.3.0 | Production-readiness hardening | Active on `codex/hardening/v0.3.0-production-readiness` |
| 0.3.1 | Measured hot-path import and benchmark hygiene | Planned after 0.3.0 |
| 0.3.2 | Explicit host-acquisition architecture | Planned after 0.3.1 |

### 0.3.0 — production-readiness hardening

This is one minor release rather than several retroactive patches. Its changes
share one purpose—making the 0.2 renderer safe to install and run repeatedly—and
the locked storage service underpins the ledger, transcript, probe, and hook
corrections.

Implemented on the active branch:

- Ownership-safe, fail-closed installation and removal.
- Private, locked, atomic runtime state.
- Exact rolling-cost deltas, migration seeds, lower-bound markers, and 35-day
  accounting evidence.
- Bounded transcript, probe, and rate-limit observation state.
- Session-scoped process metrics for concurrent hosts.
- A locked uv, pre-commit, formatting, lint, typing, coverage, and build gate.
- Tracked project instructions, handoff, review ledger, roadmap, and research.
- Terminal-cell-aware Unicode fitting and control-sequence sanitization.
- A shared synthetic end-to-end fixture that gates every approved row through
  pytest and the installed-package smoke.
- An isolated installed-renderer self-test and privacy-safe last-error
  breadcrumb.
- Source-aligned installation, privacy, development, internals, and host-
  porting documentation.

Required before release:

- Pin workflow actions immutably and prove the cost-controlled workflow after
  hosted execution becomes available; do not merge the safety branch without
  green CI.
- Complete a public-readiness audit of the current tree, reachable Git history,
  generated artifacts, historical Actions logs, examples, privacy claims, and
  outside-contributor workflow policy. Repository visibility remains a
  maintainer decision after a direct go/no-go report.
- Complete the full local gate, artifact inspection, isolated wheel install,
  privacy sweep, independent review, and exact-release proof.

### 0.3.1 — measured hot-path performance

- Lazy-load `subprocess` on probe cache misses and `argparse` only for the ledger
  CLI; remove `shutil` from terminal-width detection if direct environment and
  OS calls preserve behavior.
- Add a deterministic import-budget regression that names expensive modules
  imported by the renderer.
- Add a synthetic, isolated benchmark command reporting interpreter floor,
  warm render, cold render, median, range, and the ratio to interpreter startup.
- Track benchmark output as evidence; do not gate on elapsed time until enough
  cross-machine history exists to define a non-flaky boundary.
- Preserve every approved row and field. Performance work does not redesign the
  display.

### 0.3.2 — host-acquisition architecture

- Confine host-specific payload and transcript interpretation to an acquisition
  layer with an explicit internal interface.
- Keep rendering, storage, ledger arithmetic, paths, and host-independent probes
  free of new Claude-specific assumptions.
- Update porting documentation to describe Codex as unsupported by its current
  declarative interface, not permanently incapable of command-backed support.
- Document GitHub Copilot CLI as a credible future command-backed adapter while
  deliberately shipping no speculative adapter in this release.

## Unscheduled promotion candidates

- Implement a Copilot CLI adapter only after a maintained payload contract and
  real user need exist.
- Re-evaluate Codex when its command-backed status-line request changes state;
  never register a command from project-local untrusted configuration.
- Evaluate a security-isolated self-hosted macOS runner separately from package
  behavior. Do not register one without a dedicated account and an explicit
  filesystem-access audit.
- Revisit a compiled implementation only if cold-probe measurements or a new
  field prove Python materially inadequate. Current evidence recommends no
  rewrite.
