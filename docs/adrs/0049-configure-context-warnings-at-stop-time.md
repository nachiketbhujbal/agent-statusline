# ADR 0049: Configure context warnings at Stop time

- Status: Accepted
- Date: 2026-09-15

## Context

The Claude context guard warned only on `UserPromptSubmit`, after the user had
already chosen to spend another turn. Its 80-percent threshold and compaction
instruction were fixed, and its window-size fallback came from the most recent
global status-line payload rather than the current session.

## Decision

Install the managed context guard for both `Stop` and `UserPromptSubmit` while
running it on `Stop` by default. A Stop warning contains only `systemMessage`,
so the user sees it while choosing the next action and the hook does not inject
instructions that force another model turn. Set
`AGENT_STATUSLINE_CONTEXT_WARN_EVENT` to `submit` or `both` when model-directed
prompt-submit advice is preferred.

Set the warning threshold with `AGENT_STATUSLINE_CONTEXT_WARN_PCT`, which accepts
a finite number from 1 through 100 and defaults to 80. Set a custom warning with
`AGENT_STATUSLINE_CONTEXT_WARN_MESSAGE`; it must be non-empty and contain the
literal `{pct}` placeholder. With no custom message, retain the established
short user warning and focused-compaction guidance.

When a hook payload carries a session identifier, prefer the versioned public
session snapshot from ADR 0048. If no usable snapshot is available, retain the
existing transcript occupancy and last-payload window-size fallback. The
installed self-test validates configuration before exercising synthetic state,
and a live misconfiguration produces a user-visible message without blocking
the host.

## Consequences

Teams can choose their own threshold, wording, and timing without editing the
package. Default advice arrives at the useful decision boundary and stays out
of model context. Reinstallation adds one package-owned Stop hook while
preserving unrelated configuration. The renderer, ten display rows, cost
ledger, dependencies, networking boundary, and metrics schema do not change.
