# ADR 0026: Coordinate one owner and one reviewer

- Status: Accepted
- Date: 2026-08-27

## Context

Multiple assistants can use linked Git worktrees. Those worktrees share the
repository's common Git directory and hooks even though their files and virtual
environments are separate. Parallel writers, overlapping reviewers, or hook
installation from a temporary worktree can change another worker's environment
and obscure who owns a release decision.

Machine-local coordination is useful operational context but cannot be the only
durable statement of project state.

## Decision

Each release has exactly one branch owner and one independent reviewer. The
owner alone changes the release branch and applies corrections. Work is serial
by default: at most one independent reviewer is active at a time, review is not
fanned out to additional agents, and the reviewer does not further delegate.

The reviewer inspects an immutable exact candidate SHA from a detached,
disposable worktree, reports evidence, and does not commit to or check out the
owner's worktree. A correction creates a new candidate and requires a renewed
exact-SHA review. Remove the disposable review worktree after the verdict.

[AGENTS.md](../../AGENTS.md) is the authoritative instruction file and the
tracked [HANDOFF.md](../../HANDOFF.md) is the authoritative current-state
record. Private coordination channels cannot override them. Material decisions
live in ADRs, release scope in [ROADMAP.md](../ROADMAP.md), completed behavior in
[CHANGELOG.md](../CHANGELOG.md), and findings in
[CODE_REVIEW.md](../CODE_REVIEW.md).

Provision each worktree with `uv sync --locked`. Install the shared pre-commit
hook once from the primary clone; never reinstall it from a temporary worktree,
because linked worktrees share `.git/hooks`.

## Consequences

- One writer retains a coherent release history and unambiguous authority.
- One reviewer provides independent evidence without concurrent review churn.
- Review corrections cannot inherit an obsolete verdict from an earlier SHA.
- A cold session can recover project state from tracked public files.
- Removing a review worktree cannot strand a shared hook on that worktree's
  virtual environment.
