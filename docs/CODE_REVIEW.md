# Code review ledger

Findings are evidence records. Resolved means the implementation and focused
regression exist on the named release branch; release status remains separate.

| ID | Severity | Finding | Target | Status |
| --- | --- | --- | --- | --- |
| INST-001 | High | Install and uninstall removed every hook in three shared Claude Code events, including other tools' hooks. | 0.3.0 | Resolved by ADR 0020 and mixed-owner regressions |
| INST-002 | High | Malformed or unreadable existing settings were treated as empty and could be overwritten. | 0.3.0 | Resolved by fail-closed parsing and byte-preservation regression |
| INST-003 | Medium | Checkout commands ignored a custom Claude configuration directory. | 0.3.0 | Resolved with absolute selected-directory commands |
| INST-004 | Medium | Uninstall removed any symlink at the managed path without proving ownership. | 0.3.0 | Resolved by target-identity ownership checks |
| STATE-001 | High | Concurrent redraws shared predictable temporary paths and unlocked read-modify-write state. | 0.3.0 | Resolved by ADR 0021 and subprocess concurrency coverage |
| STATE-002 | Medium | Ledger, payload, history, and cache files inherited potentially public umask permissions. | 0.3.0 | Resolved with private files and newly created state directories |
| COST-001 | High | Rolling windows assigned a session's complete lifetime cost to its last update and could substantially over-count recent spend. | 0.3.0 | Resolved by ADR 0022, timestamped deltas, seeds, and exact lower bounds |
| COST-002 | Medium | A first-seen or reset ledger could misclassify historical session cost as new accrual. | 0.3.0 | Resolved with non-accrual seed records and Tier-1 whole-session evidence |
| COST-003 | Medium | Observation time was weaker than the newest known assistant timestamp for window attribution. | 0.3.0 | Resolved with recorded accrual and observation timestamps |
| TEST-001 | Medium | Tool versions, formatting, typing, coverage, and commit-time checks were not reproducible. | 0.3.0 | Resolved by ADR 0023 and `uv.lock` |
| STATE-003 | High | Concurrent sessions shared one process-probe cache row, so all could display the first session's PID and RSS. | 0.3.0 | Resolved by ADR 0024 and distinct-session cache regressions |
| STATE-004 | Medium | Path- and session-qualified probe rows accumulated without a lifecycle bound. | 0.3.0 | Resolved by seven-day and 256-row cache bounds |
| STATE-005 | Medium | Transcript cache rows and rate-limit history grew without a lifecycle bound. | 0.3.0 | Resolved by ADR 0025 and retention, byte-bound, and hot-path regressions |
| RENDER-001 | Medium | Printable width used code-point count rather than terminal-cell width for wide and combining Unicode. | 0.3.0 | Open |
| RENDER-002 | Medium | Host and user-controlled labels were emitted without control-character sanitization. | 0.3.0 | Open |
| DOC-001 | Low | README claims Python 3.8 while package metadata and installer require 3.9. | 0.3.0 | Open |
| DOC-002 | Low | README hardcodes an obsolete test count. | 0.3.0 | Open |
