# ADR 0002: Keep runtime state outside the repository

- Status: Accepted
- Date: 2026-08-26

## Context

The code began life inside `~/.claude` alongside the cost ledger and several
caches. Making it a repository that syncs across machines would have committed
per-machine spend history, guaranteeing merge conflicts and leaking usage data
into any clone.

## Decision

The repository holds code and documentation only. Runtime state — the ledger,
the probe and transcript caches, the rate-limit log, the last payload — stays in
the agent's own config directory. `paths.py` is the single place that resolves
it, and `AGENT_STATUSLINE_STATE` overrides the location.

## Consequences

A checkout is disposable and machine-independent. Tests and previews point the
override at a throwaway directory, which is what makes ADR 0014 enforceable.
State files are also listed in `.gitignore` so a stray run inside the checkout
cannot commit a ledger.
