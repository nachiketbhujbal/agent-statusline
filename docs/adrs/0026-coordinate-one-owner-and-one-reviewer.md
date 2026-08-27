# ADR 0026: Coordinate one owner and one reviewer

- Status: Accepted
- Date: 2026-08-27

## Context

Multiple assistants can work concurrently from linked Git worktrees. Linked
worktrees share the repository's common Git directory and hooks even though
their files and virtual environments are separate. Uncoordinated branch
checkouts, corrections, or hook installation can change another worker's
environment and obscure who owns a release decision.

Machine-local assistant handoffs are useful scratch records but cannot be the
only durable statement of project state.

## Decision

Each release has exactly one branch owner and one independent reviewer. Codex
owns `codex/*` branches and Claude owns `claude/*` branches. The owner applies
corrections; the reviewer reports evidence and does not commit to or check out
the owner's worktree. Read-only inspection of an active worktree uses
`git --no-optional-locks` where possible.

`AGENTS.md` is the authoritative instruction file and the tracked `HANDOFF.md`
is the authoritative current-state record. Private assistant channels may carry
operational detail but cannot override them. Material decisions live in ADRs,
release scope lives in `ROADMAP.md`, and completed behavior lives in
`CHANGELOG.md`.

Provision each worktree with `uv sync --locked`. Install the shared pre-commit
hook once from the primary clone; never reinstall it from an assistant
worktree, because doing so rewrites the common hook's interpreter path.

## Consequences

- Concurrent investigation and implementation remain possible without two
  writers owning the same release.
- Review findings stay independent, while the branch owner retains a coherent
  correction history.
- A cold session can recover project state from tracked files without access to
  a particular assistant's local notes.
- Removing a worktree cannot strand the shared pre-commit hook on that
  worktree's virtual environment.
