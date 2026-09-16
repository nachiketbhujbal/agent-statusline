# agent-statusline

[![CI](https://github.com/nachiketbhujbal/agent-statusline/actions/workflows/ci.yml/badge.svg)](https://github.com/nachiketbhujbal/agent-statusline/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-statusline.svg)](https://pypi.org/project/agent-statusline/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/nachiketbhujbal/agent-statusline/blob/main/LICENSE)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](https://github.com/nachiketbhujbal/agent-statusline/blob/main/pyproject.toml)

A dense, local-first status line for
[Claude Code](https://claude.com/claude-code). See the project, model, context,
usage, cost, tools, cache, tokens, timing, and machine pressure of the session
you are in—without telemetry, runtime network calls, or third-party packages.

```text
PROJECT acme-web/services │ feature/ingest* ↑2 stash1 │ "Rewrite the importer"
MODEL   Opus 5:high │ think │ fast off │ auto │ v2.1.246
CONTEXT ctx[██░░░░░░░░]  19% 189k/1M │ session 25.7M in · 311k out · 107k thinking · 189 api turns · avg 136k/1.65k per turn
USAGE   5h [███░░░░░░░] 26% @19.7%/h ▸ 98% (reset Wed 19:30 | 3h40m) │ 7d [█████░░░░░] 50% @0.3%/h ▸ 50% (reset Wed 17:00 | 1h10m)
COST    $2.10 session │ 24h $9.40 · 7d $31.20 · 30d $88.60 │ last5 $27.50 · all $142.30 (5 convos · 6 sess · 1 fork) │ +174/-12 lines │ credits on
SYSTEM  this session 540M · 5 proc · pid 4821 │ all claude 512M · 1 proc · 1.6% of ram │ ram[█████░░░] 62% of 32.0G · 4.2G compressed │ disk[████░░░░] 48% · 210G free
TOOLS   101 calls │ Bash81 Edit12 Read8 │ 2 tool errors │ 6 files edited · 14 read │ 0 subagents │ 0 compactions
CACHE   97.9% hit │ 1h ttl ▸ expires 16:49 │ 0.12x vs all-uncached │ writes 504k 1h · 0 5m
TOKENS  total 23.8M reused · 504k written · 366 uncached │ turn 184k reused · 5.2k written · 2 uncached
TIMING  turn 12m last · 4m median · 12m max (3 timed) │ wall 1h11m · api 19m (27% busy) │ hooks 3 runs · 133ms median · 0 errors
```

Rows reflow deterministically as the terminal changes width. Each may wrap once;
only then are lower-priority details removed with an `…` marker. No physical
output line exceeds the detected terminal width.

## Install

The recommended installation keeps this frequently invoked command isolated:

```bash
uv tool install agent-statusline
agent-statusline install
```

Restart Claude Code after installation. To preview the configuration changes
first, run `agent-statusline install --dry-run`.

The package is a standard Python distribution. These install the same command
with other package managers:

```bash
pipx install agent-statusline
python -m pip install agent-statusline
```

`pipx` isolates the command like `uv tool`; `pip` installs it into the active
Python environment.

Requirements: Python 3.9 or newer, Claude Code, and macOS or Linux. Git is
optional and enriches the `PROJECT` row. The `SYSTEM` row reads native memory
pressure from macOS or Linux; under WSL it reports the memory available to the
Linux environment rather than the Windows host's full physical capacity.

## What it tracks

- `PROJECT` and `MODEL`: location, Git state, task, model, effort, mode, and host version.
- `CONTEXT` and `USAGE`: context consumption, session tokens, API turns, and rate-limit windows.
- `COST`: current, rolling, recent, and lifetime spend plus session counts and line changes.
- `SYSTEM` and `TOOLS`: process, memory, disk, tool, file, subagent, and compaction activity.
- `CACHE`, `TOKENS`, and `TIMING`: cache efficiency, token flow, turn time, wall time, and hooks.

The [field reference](https://github.com/nachiketbhujbal/agent-statusline/blob/main/docs/FIELDS.md)
documents every value and its source.

## Local and private by design

- Rendering uses local Claude Code payloads, transcripts, and machine state. It
  sends no telemetry and has no cloud fallback.
- Runtime state stays under `~/.claude/`, outside the repository. Package-owned
  state is privately permissioned and locked, using atomic replacement or
  durable append as appropriate.
- Currency-labelled totals are exactly attributable. When retained evidence can
  prove only a lower bound, the display says `≥` instead of presenting it as a total.
- Installation backs up `settings.json`, preserves unrelated settings and hooks,
  and refuses to replace configuration it cannot prove it owns.
- `agent-statusline selftest` uses isolated synthetic state and never touches the
  live cost ledger.

The last-payload and per-session metrics files can contain sensitive paths,
titles, costs, identifiers, and commands. Do not publish or attach files from
the status-line state directory.

## Commands

| Command | Purpose |
| --- | --- |
| `agent-statusline install` | Wire the command and managed hooks into Claude Code |
| `agent-statusline install --dry-run` | Preview installation without writing anything |
| `agent-statusline selftest` | Render all ten rows from isolated synthetic data |
| `agent-statusline metrics <session-id>` | Print the documented local snapshot for one session |
| `agent-statusline ledger show` | Inspect the local cost ledger |
| `agent-statusline uninstall` | Remove only configuration owned by this installation |
| `agent-statusline --version` | Print the installed version |

The managed context guard warns after a turn when context reaches 80% by
default. Configure it in the environment that launches Claude Code:

| Variable | Values |
| --- | --- |
| `AGENT_STATUSLINE_CONTEXT_WARN_PCT` | warning threshold from `1` through `100` |
| `AGENT_STATUSLINE_CONTEXT_WARN_EVENT` | `stop` (default), `submit`, or `both` |
| `AGENT_STATUSLINE_CONTEXT_WARN_MESSAGE` | custom non-empty message containing `{pct}` |

Run `agent-statusline selftest` after changing these values. Stop warnings are
user-visible only; `submit` and `both` allow the configured advice to enter the
next model turn.

If the status line does not appear, run `agent-statusline selftest` first, then
restart Claude Code. Unexpected renderer failures leave only their time and
exception type in `~/.claude/statusline-last-error.json`.

## Update or remove

```bash
uv tool upgrade agent-statusline
agent-statusline install
```

Re-running `install` refreshes the managed Claude Code wiring while preserving
unrelated configuration.

```bash
agent-statusline uninstall
uv tool uninstall agent-statusline
```

Uninstalling leaves the local ledger and history in `~/.claude/` intact.

## Develop from a checkout

```bash
git clone https://github.com/nachiketbhujbal/agent-statusline.git
cd agent-statusline
uv sync --locked --all-groups
uv run --locked python scripts/verify_docs.py
uv run --locked pre-commit run --all-files
uv run --locked pytest --cov=agent_statusline --cov-report=term-missing
uv build
```

Run `python3 install.py` to wire a development checkout into Claude Code through
a symlink; working-tree edits then become live without reinstalling. Tests use
synthetic inputs and must never read the real `~/.claude` state.

Contributor-facing details live in the
[implementation guide](https://github.com/nachiketbhujbal/agent-statusline/blob/main/docs/INTERNALS.md)
and [host-porting boundary](https://github.com/nachiketbhujbal/agent-statusline/blob/main/docs/PORTING.md).

## License

[MIT](https://github.com/nachiketbhujbal/agent-statusline/blob/main/LICENSE).
This independent project is not affiliated with or endorsed by Anthropic.
