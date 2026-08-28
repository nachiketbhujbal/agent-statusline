# agent-statusline project instructions

This is a local-first, dependency-free Python status line for coding agents.
The installed command is `agent-statusline`. Release versions come from Git
tags through hatch-vcs; never duplicate a version string in source.

## Start here

- Read `HANDOFF.md` completely before changing the repository.
- Read the affected module, tests, ADRs, and field documentation before
  changing behavior.
- Treat this file as the only authoritative assistant instruction file.

## Product invariants

- Preserve the approved Claude Code display: ten rows in `ORDER`, with their
  current fields and priority order. Do not remove, rename, reorder, or simplify
  a row or field without explicit maintainer approval.
- Keep runtime behavior local. No telemetry, analytics, runtime networking,
  automatic downloads, or cloud fallbacks.
- Keep runtime dependencies empty. The renderer is a frequent short-lived
  process and must run with the Python standard library alone.
- Never test cost paths against live state. Set `AGENT_STATUSLINE_STATE` to a
  disposable directory before importing the package.
- A currency-labelled claim must be exactly accountable. An exact lower bound
  uses `≥`; do not silently present partial or estimated spend as a total.
- Preserve lifetime session, rolling 24h/7d/30d, `last5`, and `all` cost fields.
  Rolling cost changes must retain seed, resume, timestamp, pruning, malformed-
  evidence, and concurrent-redraw coverage.
- Keep mutable state outside the repository. Coordinate every read-modify-write
  transaction through the locked storage service, publish atomically, and use
  private file permissions.
- Installation and removal may mutate only this package's status line, hooks,
  and checkout symlink. Preserve unrelated configuration and fail closed on an
  unreadable or malformed existing settings file.
- Keep width fitting deterministic and ensure no physical output line exceeds
  the detected terminal-cell width.
- Treat Codex as a separate widget-based host. Do not claim that this Python
  renderer can run in Codex unless the installed Codex interface actually adds
  an arbitrary-command status line.

## Development workflow

- Use uv 0.12 or newer. Commit `uv.lock` and manage development tools in
  `pyproject.toml`; do not add requirements files.
- Use Hatchling and hatch-vcs with standard PEP 621 metadata.
- Work on a short-lived `codex/<type>/<version>-<slug>` or
  `claude/<type>/<version>-<slug>` branch based on `main`.
- Add or update synthetic, privacy-neutral pytest coverage with every behavior
  change. Do not read or publish live ledger contents in tests or documentation.
- Run `uv run --locked pre-commit run --all-files`, subprocess-aware pytest
  coverage, and `uv build` before requesting review.
- Keep hosted Actions disabled while the account allowance is unavailable.
  Local release evidence must remain complete; do not weaken gates because CI
  is paused.
- Pin every future workflow action to an immutable commit. Keep documentation-
  only changes out of hosted test runs.
- Record durable decisions as one numbered ADR under `docs/adrs/`. Supersede an
  accepted ADR rather than rewriting its history.
- Keep `docs/CODE_REVIEW.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`, and
  `HANDOFF.md` synchronized with implementation status.
- Use concise one-line commits. Open a pull request, obtain adversarial review,
  merge only after approval, and create an immutable annotated release tag only
  from the verified merge commit.
- Give each release one branch owner and one independent reviewer. Codex owns
  `codex/*`; Claude owns `claude/*`. Reviewers report findings and never commit
  to or check out the owner's worktree; the owner applies corrections.
- Use `git --no-optional-locks` for read-only inspection of an active worktree
  where possible. Run `uv sync --locked` per worktree, but install pre-commit
  only once from the primary clone because linked worktrees share `.git/hooks`.
- Stage newly added files before an all-files pre-commit gate (or pass them
  explicitly). Git does not include untracked files in `--all-files`.

## Release-equivalent local gate

```bash
uv sync --locked --all-groups
uv run --locked pre-commit run --all-files
uv run --locked pytest --cov=agent_statusline --cov-report=term-missing
uv build
```
