# Code review ledger

Findings are evidence records. Resolved means the implementation and focused
regression exist on the named release branch; release status remains separate.

| ID | Severity | Finding | Target | Status |
| --- | --- | --- | --- | --- |
| INST-001 | High | Install and uninstall removed every hook in three shared Claude Code events, including other tools' hooks. | 0.2.1 | Resolved by ADR 0020 and mixed-owner regressions |
| INST-002 | High | Malformed or unreadable existing settings were treated as empty and could be overwritten. | 0.2.1 | Resolved by fail-closed parsing and byte-preservation regression |
| INST-003 | Medium | Checkout commands ignored a custom Claude configuration directory. | 0.2.1 | Resolved with absolute selected-directory commands |
| INST-004 | Medium | Uninstall removed any symlink at the managed path without proving ownership. | 0.2.1 | Resolved by target-identity ownership checks |
| STATE-001 | High | Concurrent redraws shared predictable temporary paths and unlocked read-modify-write state. | 0.2.2 | Resolved by ADR 0021 and subprocess concurrency coverage |
| STATE-002 | Medium | Ledger, payload, history, and cache files inherited potentially public umask permissions. | 0.2.2 | Resolved with private files and newly created state directories |
| COST-001 | High | Rolling windows assigned a session's complete lifetime cost to its last update and could substantially over-count recent spend. | 0.2.3 | Resolved by ADR 0022, timestamped deltas, seeds, and exact lower bounds |
| COST-002 | Medium | A first-seen or reset ledger could misclassify historical session cost as new accrual. | 0.2.3 | Resolved with non-accrual seed records and Tier-1 whole-session evidence |
| COST-003 | Medium | Observation time was weaker than the newest known assistant timestamp for window attribution. | 0.2.3 | Resolved with recorded accrual and observation timestamps |
| COST-004 | High | A future transcript timestamp could keep one accrual inside every rolling window. | 0.2.3 | Resolved by clamping transcript accrual evidence to observation time |
| TEST-001 | Medium | Tool versions, formatting, typing, coverage, and commit-time checks were not reproducible. | 0.2.3 | Resolved by ADR 0023 and `uv.lock` |
| TEST-002 | Medium | The installed-package smoke rendered only an empty object, so it did not prove the approved display or transcript-backed fields. | 0.2.8 | Resolved by ADR 0028 and shared synthetic fixture assertions |
| TEST-003 | Medium | An all-files gate run before staging omitted a new source file, and the shared pre-commit hook was not installed. | 0.2.10 | Resolved by primary-clone hook installation, tracked sequencing guidance, and a full tracked-tree rerun |
| TEST-004 | High | Synthetic renderer evidence depended on the process working directory, live home configuration, and omitted reset clocks. | 0.2.8–0.2.9 | Resolved by shared materialization, disposable home/workspace paths, current timestamps, reset assertions, and installed-smoke reuse |
| DIAG-001 | Medium | Host-swallowed render failures had no safe diagnostic path, while replaying a real payload could mutate live accounting. | 0.2.9 | Resolved by ADR 0029, isolated self-test, negative privacy checks, contract-equivalent evidence, and allowlisted failure breadcrumb |
| STATE-003 | High | Concurrent sessions shared one process-probe cache row, so all could display the first session's PID and RSS. | 0.2.4 | Resolved by ADR 0024 and distinct-session cache regressions |
| STATE-004 | Medium | Path- and session-qualified probe rows accumulated without a lifecycle bound. | 0.2.5 | Resolved by seven-day and 256-row cache bounds |
| STATE-005 | Medium | Transcript cache rows and rate-limit history grew without a lifecycle bound. | 0.2.5 | Resolved by ADR 0025 and retention, byte-bound, and hot-path regressions |
| RENDER-001 | Medium | Printable width used code-point count rather than terminal-cell width for wide and combining Unicode. | 0.2.7 | Resolved by ADR 0027 and Unicode cell regressions |
| RENDER-002 | Medium | Host and user-controlled labels were emitted without control-character sanitization. | 0.2.7 | Resolved by ADR 0027 and injected-control regressions |
| RENDER-003 | Medium | Nested-repository display discovery rebound the workspace used by the later disk probe. | 0.2.7 | Resolved by separate display and resource-probe paths plus focused regression |
| RENDER-004 | Medium | The host could trim a continuation line's raw leading spaces, placing wrapped segments beneath the row label. | 0.2.7 | Resolved by an invisible SGR prefix that preserves the label-column indent |
| DOC-001 | Low | README claims Python 3.8 while package metadata and installer require 3.9. | 0.2.10 | Resolved by package/installer-aligned requirements |
| DOC-002 | Low | README hardcodes an obsolete test count. | 0.2.10 | Resolved by command-based locked gate documentation |
| DOC-003 | Medium | Roadmap, research, and cross-assistant state existed only in machine-local records. | 0.2.6 | Resolved by tracked planning records and ADR 0026 |
| DOC-004 | Medium | Installation, runtime privacy, module boundaries, and the unimplemented Codex ledger path were described inaccurately. | 0.2.10 | Resolved by source-aligned README, internals, and porting references |
