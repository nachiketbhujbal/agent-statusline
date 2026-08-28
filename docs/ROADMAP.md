# Roadmap

Promoted, release-scoped work belongs here. Evidence and open questions that do
not yet justify implementation remain in `RESEARCH.md` or `DEFERRED.md`.

## Release sequence

| Release | Primary purpose | Status |
| --- | --- | --- |
| 0.2.1 | Ownership-safe installation and removal | Next release |
| 0.2.2 | Private, serialized runtime state | Planned |
| 0.2.3 | Exact rolling-cost attribution | Planned |
| 0.2.4 | Session-scoped process evidence | Planned |
| 0.2.5 | Bounded observation state | Planned |
| 0.2.6 | Tracked governance and review records | Planned |
| 0.2.7 | Width-safe, sanitized rendering | Planned |
| 0.2.8 | Hermetic installed-renderer evidence | Planned |
| 0.2.9 | Isolated self-test and safe diagnostics | Planned |
| 0.2.10 | Documentation, workflow, and public-readiness closure | Planned |
| 0.3.0 | Production-ready milestone | Planned after the patch train |
| 0.3.1 | Measured hot-path import and benchmark hygiene | Planned after 0.3.0 |
| 0.3.2 | Explicit host-acquisition architecture | Planned after 0.3.1 |

The current hardening branch is an integration source. It must not be merged as
one release. Release branches will be cut sequentially from `main`, drawing only
the cohesive implementation, tests, ADR, and documentation for the version
below. This preserves review history without rewriting the shared integration
branch.

### 0.2.1 through 0.2.10 — hardening patch train

- **0.2.1 — installation ownership:** preserve unrelated settings and hooks,
  fail closed on malformed configuration, honor custom configuration roots, and
  remove only owned configuration.
- **0.2.2 — runtime-state safety:** coordinate read-modify-write operations,
  publish atomically, and enforce private state permissions.
- **0.2.3 — cost correctness:** record timestamped deltas and non-accrual seeds,
  preserve exact lower bounds, clamp future transcript evidence, and establish
  the locked local quality gate used to prove the accounting change.
- **0.2.4 — process isolation:** prevent concurrent sessions from sharing the
  wrong PID and memory evidence.
- **0.2.5 — bounded state:** cap probe, transcript, and rate-limit observation
  retention without adding full-file work to the hot redraw path.
- **0.2.6 — governance:** track authoritative instructions, research, roadmap,
  review findings, and one-owner/one-reviewer coordination.
- **0.2.7 — rendering safety:** measure terminal cells, sanitize untrusted
  controls, keep disk probes bound to the real workspace, and preserve wrapped
  continuation indentation through the host.
- **0.2.8 — installed evidence:** materialize a privacy-neutral payload and
  transcript into disposable paths and require all ten rows from pytest and an
  installed wheel.
- **0.2.9 — diagnostics:** provide an isolated `selftest` and an allowlisted,
  private last-error breadcrumb without relaying payload or traceback data.
- **0.2.10 — release closure:** align public documentation, pin workflow actions
  immutably, complete artifact and reachable-history privacy sweeps, and give a
  direct public-repository go/no-go recommendation.

Every patch requires its own local gate, adversarial review, pull request,
hosted checks when available, annotated tag, and installed-wheel proof. A later
patch cannot be used as evidence that an earlier tag was sound.

### 0.3.0 — production-ready milestone

After the patch train is released and independently proven, use 0.3.0 as the
explicit supported baseline for public adoption. It is a milestone, not a place
to accumulate unrelated implementation. Its only permitted changes are final
version-boundary documentation or corrections found while proving the complete
train.

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
