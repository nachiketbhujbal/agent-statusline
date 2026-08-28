# ADR 0029: Self-test with isolated state and safe failure evidence

- Status: Accepted
- Date: 2026-08-28

## Context

Claude Code silently hides status-line process failures. Replaying a real
payload is a poor default diagnostic because rendering updates accounting and
cache state, while exception messages and tracebacks can expose payload values,
transcript paths, commands, or filenames. A health check must be meaningful
without reading or mutating live accounting evidence.

## Decision

Add `agent-statusline selftest`. It launches the installed renderer in a fresh
Python process, supplies a full synthetic payload and transcript, redirects
`AGENT_STATUSLINE_STATE` to a temporary directory, and requires all ten rows in
their approved order. It also verifies that the isolated state directory and
files have private permissions. The command prints only a generic pass or
failure reason and never relays child output.

Wrap normal rendering so an unexpected exception atomically publishes
`statusline-last-error.json` in the configured state directory. The breadcrumb
contains only a schema version, UTC occurrence time, fixed phase, and exception
type. It must never contain the exception message, traceback, payload,
transcript path, command, or filename. Failure to write the breadcrumb never
masks the original render failure.

Malformed input remains an expected degraded render and does not create a
failure breadcrumb.

## Consequences

- Installation health can be checked without touching the real cost ledger.
- Failures swallowed by the host leave minimal local evidence for diagnosis.
- The last recorded error is historical evidence, not a claim that the current
  renderer remains unhealthy.
- The self-test intentionally duplicates a small synthetic payload in runtime
  code so installed wheels do not depend on test files.

## Evidence

CLI integration exercises the self-test through a child renderer. Focused
regressions prove exact row coverage, isolated private state, breadcrumb field
allowlisting, message/path exclusion, mode `0600`, and preservation of the
original exception when breadcrumb publication fails.
