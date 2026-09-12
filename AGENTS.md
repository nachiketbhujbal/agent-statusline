# agent-statusline project instructions

This is a local-first, dependency-free Python status line for coding agents.
The installed command is `agent-statusline`. Release versions come from Git
tags through hatch-vcs; never duplicate a version string in source.

## Start here

- Read [HANDOFF.md](HANDOFF.md) completely before changing the repository.
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
  Rolling-cost changes must retain seed, resume, timestamp, pruning, malformed-
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
- Start each short-lived `codex/<type>/<version>-<slug>` or
  `claude/<type>/<version>-<slug>` branch from the preceding released state on
  `main`, not from an unreleased integration branch.
- Add or update synthetic, privacy-neutral pytest coverage with every behavior
  change. Do not read or publish live ledger contents in tests or documentation.
- Run the documentation verifier, locked all-files gate, subprocess-aware
  pytest coverage, and build before requesting review.
- Both hosted workflows are active. Full-scope pull requests and `main` pushes
  automatically run the Linux Python matrix and representative macOS evidence
  behind one aggregate required result. Do not dispatch a duplicate run when an
  automatic run already proves the same SHA. Documentation-only changes run
  only the ancestry audit and remain outside the full hosted gate.
- Pin future workflow action updates to immutable commits. Do not weaken local
  evidence when a hosted lane is intentionally skipped.
- Record durable decisions as one numbered ADR under `docs/adrs/`. Supersede an
  accepted ADR rather than rewriting its history.
- Keep `docs/CODE_REVIEW.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`, and
  `HANDOFF.md` synchronized with implementation status.
- Follow [ADR 0030](docs/adrs/0030-ship-hardening-as-small-pre-one-patches.md)
  while the project is pre-1.0: keep compatible hardening tags small, never
  conceal a breaking change in a patch, describe future scope in the roadmap,
  and keep the changelog limited to the next slice plus landed releases.
- Stage newly added files before an all-files pre-commit gate. Git does not
  include untracked files in `--all-files`.

## Ownership and review

- Each release has exactly one branch owner. The owner alone changes the release
  branch, applies corrections, opens the pull request, and performs the release.
- Work serially by default. At most one independent reviewer may be active at a
  time; do not fan work out to multiple agents or add another delegation layer.
- The reviewer uses a detached disposable worktree, reports findings, and does
  not commit to or check out the owner's worktree. Remove the review worktree
  when the verdict is complete.
- Review an immutable exact candidate SHA against the preceding release. Any
  correction changes the candidate and requires a renewed exact-SHA review.
- Use concise one-line commits. Merge only the reviewed candidate after green
  required checks, and create an immutable annotated release tag only from the
  verified merge commit.
- Use `git --no-optional-locks` for read-only inspection of an active worktree
  where possible. Run `uv sync --locked` per worktree, but install pre-commit
  only once from the primary clone because linked worktrees share `.git/hooks`.

## Release-equivalent local gate

```bash
uv sync --locked --all-groups
uv run --locked python scripts/verify_docs.py
uv run --locked pre-commit run --all-files
uv run --locked pytest --cov=agent_statusline --cov-report=term-missing
uv build
```
