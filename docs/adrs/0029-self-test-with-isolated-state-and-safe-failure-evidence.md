# ADR 0029: Self-test with isolated state and safe failure evidence

- Status: Accepted
- Date: 2026-09-11

## Context

Claude Code silently hides status-line process failures. Replaying a real
payload is a poor diagnostic because rendering updates accounting and cache
state, while exception messages and tracebacks can expose payload values,
transcript paths, commands, or filenames. A health check must be meaningful
without reading or mutating live accounting evidence.

## Decision

Add `agent-statusline selftest`. It launches the installed renderer in a fresh
Python process, supplies a complete synthetic payload and transcript, redirects
`HOME`, `CLAUDE_CONFIG_DIR`, and `AGENT_STATUSLINE_STATE` beneath one temporary
workspace, and renders with that workspace as the child's current directory. It
requires all ten rows in their approved order and verifies that home, the state
directory, nested directories, and state files have private modes and supported
regular types. The command prints only a generic result and never relays child
output.

Derive expected rows from the renderer's authoritative `ORDER`. Keep the runtime
self-test payload and transcript equivalent to the v0.2.10 committed synthetic
contract under a regression, even though the runtime wheel intentionally carries
its own small builder rather than test files. Reject public, symlinked, or
non-regular private-state entries.

Wrap normal rendering so an unexpected exception atomically publishes
`statusline-last-error.json` in the configured state directory. The breadcrumb
allowlists only a schema version, UTC occurrence time, fixed phase, and exception
type. It never includes the exception message, traceback, payload, transcript
path, command, or filename. Failure to write it never masks the original render
failure.

Malformed input remains an expected degraded render and creates no breadcrumb.
A closed host pipe is routine lifecycle behavior and also creates none.

## Consequences

- Installation health can be checked without touching the real cost ledger or
  configuration.
- Failures hidden by the host leave minimal private local evidence.
- The recorded error is historical evidence, not a claim that the renderer is
  still unhealthy.
- Self-test and diagnostics add no dependency or network access.

## Evidence

CLI integration exercises the self-test through a child renderer. Regressions
prove contract equivalence, exact row coverage, isolated home/config/state/cwd,
private modes, unsupported-entry refusal, child-output suppression, breadcrumb
field allowlisting, message/path exclusion, `0600` publication, original-error
preservation, and the malformed-input/BrokenPipe exclusions. CI invokes the
self-test from the installed wheel.
