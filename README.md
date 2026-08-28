# agent-statusline

[![CI](https://github.com/nachiketbhujbal/agent-statusline/actions/workflows/ci.yml/badge.svg)](https://github.com/nachiketbhujbal/agent-statusline/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](pyproject.toml)

A dense, width-aware status line for [Claude Code](https://claude.com/claude-code). It
reports what the session is doing, what it is costing, how well the prompt cache is
working, and how much machine it is using — all from data the agent already has, with **no
telemetry, no network calls, and no dependencies**.

This is an independent project and is not affiliated with or endorsed by
Anthropic.

```
PROJECT acme-web/services │ feature/ingest* ↑2 stash1 │ "Rewrite the importer"
MODEL   Opus 5:high │ think │ fast off │ auto │ v2.1.246
CONTEXT ctx[██░░░░░░░░]  19% 189k/1M │ session 25.7M in · 311k out · 107k thinking · 189 api turns · avg 136k/1.65k per turn
USAGE   5h [███░░░░░░░] 26.0% @19.7%/h ▸ 98% (reset Wed 19:30 | 3h40m) │ 7d [█████░░░░░] 50.0% @0.3%/h ▸ 50% (reset Wed 17:00 | 1h10m)
COST    $2.10 session │ 24h $9.40 · 7d $31.20 · 30d $88.60 │ last5 $9.40 · all $88.60 (5 convos · 6 sess · 1 fork) │ +174/-12 lines │ credits on
SYSTEM  this session 540M · 5 proc · pid 4821 │ all claude 512M · 1 proc · 3.1% of ram │ ram[██████░░] 62% of 32.0G · 4.2G compressed │ disk[████░░░░] 48% · 210G free
TOOLS   82 calls │ Bash81 Edit12 Read8 │ 2 tool errors │ 6 files edited · 14 read │ 0 subagents │ 0 compactions
CACHE   97.9% hit │ 1h ttl ▸ expires 16:49 │ 0.12x vs all-uncached │ writes 504k 1h · 0 5m
TOKENS  total 23.8M reused · 504k written · 366 uncached │ turn 184k reused · 5.2k written · 2 uncached
TIMING  turn 12m last · 4m median · 12m max (3 timed) │ wall 1h11m · api 19m (27% busy) │ hooks 3 runs · 133ms median · 0 errors
```

Every row is labelled, and **no row ever overflows the terminal.** A row that fits stays on
one line; if it does not, it wraps onto a second line indented under the label, and only
once both lines are full do the least-important segments get dropped with a `…` marker.
Width is re-measured on every redraw, so a live terminal resize is picked up within seconds.

Rows are ordered by how often they answer a question worth asking — `PROJECT` first because
"where am I?" is the question with the worst consequences when you get it wrong.

## Documentation

| document | what is in it |
| --- | --- |
| [docs/FIELDS.md](docs/FIELDS.md) | every row and every field, and where each value comes from |
| [docs/INTERNALS.md](docs/INTERNALS.md) | data sources, width fitting, adding a field, how undocumented signals were discovered |
| [docs/adrs/](docs/adrs/README.md) | architecture decision records — one file per durable decision, with an index. **Read 0001, 0014 and 0004 before changing anything that touches money or dependencies** |
| [docs/DEFERRED.md](docs/DEFERRED.md) | ideas considered and consciously not built |
| [docs/PORTING.md](docs/PORTING.md) | adapting this to Codex or another agent, and why Codex cannot run it as-is |
| [docs/ROADMAP.md](docs/ROADMAP.md) | promoted release sequence and completion boundaries |
| [docs/RESEARCH.md](docs/RESEARCH.md) | measured findings and open questions not yet promoted to implementation |

## Requirements

- **Python 3.9+**, with no runtime packages beyond the standard library.
- **Claude Code** (developed against v2.1.246).
- macOS or Linux. The `SYSTEM` row's machine-wide RAM probe is macOS-specific
  (`vm_stat`, `sysctl`); the row retains process and disk evidence elsewhere
  and degrades instead of failing.
- Optional: `git`, for the `PROJECT` row.

## Install

```bash
uv tool install git+https://github.com/nachiketbhujbal/agent-statusline
agent-statusline install
```

Then restart Claude Code. `pipx install` and `pip install` can install from the
same Git URL. Making the repository public removes the authentication
requirement; installing by package name would still require a separate PyPI
publication.

`agent-statusline install` writes its `statusLine` entry and two managed hooks
into `~/.claude/settings.json`. It adds two temporary timestamp hooks only while
Claude's native timestamp feature is unavailable. The installer points them at
the absolute installed executable, backs up existing settings, preserves
unrelated settings and hooks, and renders the last real payload against
throwaway state. Add `--dry-run` to preview the selected mode and target;
`agent-statusline uninstall` removes only entries it can prove it owns.

Upgrading is `uv tool upgrade agent-statusline` followed by `agent-statusline install`
(the second step is only needed if the wiring itself changed).

### Or from a checkout, to hack on it

```bash
git clone https://github.com/nachiketbhujbal/agent-statusline.git
cd agent-statusline
python3 install.py
```

This symlinks `~/.claude/statusline` to the working tree, so your edits take effect with
no reinstall. The checkout bootstrap and renderer are stdlib-only and run on
the selected Python 3.9+ interpreter. The installer detects checkout versus
installed-package shape; you do not select it manually.

### The commands

| command | what it does |
| --- | --- |
| `agent-statusline` | render a status line from a payload on stdin — what Claude Code calls |
| `agent-statusline install` | wire it into `settings.json` (`--dry-run` to preview) |
| `agent-statusline uninstall` | remove the settings entries and the symlink |
| `agent-statusline hook <name>` | run one hook: `session-end`, `context-guard`, `timestamp-user`, `timestamp-stop` |
| `agent-statusline ledger show` | print the cost ledger; `ledger close <id>` seals a row by hand |
| `agent-statusline selftest` | verify all ten rows in a child process using isolated synthetic state |
| `agent-statusline version` | print the version |

### Code here, state there

The repository holds **only code and documentation**. Runtime state — the cost ledger,
the caches, the rate-limit log — is machine-local and stays in `~/.claude/`:

| stays in `~/.claude/` | why |
| --- | --- |
| `cost-ledger.json` | your spend history, per machine |
| `statusline-transcript.json` | byte offsets + accumulated per-transcript totals |
| `statusline-probe-cache.json` | cached probe results |
| `rate-limit-history.jsonl` | append-on-change rate-limit log |
| `statusline-last-payload.json` | last payload; **load-bearing**, the context-guard hook reads it |
| `statusline-last-error.json` | last unexpected render failure's time and type only; no message, path, or payload |

Override the location with `AGENT_STATUSLINE_STATE=/some/dir` — useful for testing against
a throwaway directory, which is the *only* safe way to exercise cost paths (see
[ADR 0014](docs/adrs/0014-never-exercise-cost-paths-against-the-live-ledger.md)).

### Privacy and trust boundary

Normal rendering is local-only: it makes no network request, sends no
telemetry, and has no cloud fallback. It reads the JSON supplied by Claude,
the payload-selected transcript, local Git/process/memory/disk state, and
`~/.claude.json` for local account flags. Installation additionally reads and
writes `~/.claude/settings.json` and checks the local native-timestamp feature
flag. Those sources can contain sensitive paths, titles, costs, and commands.

Mutable state stays outside the repository, is serialized under sidecar locks,
and is atomically replaced. Newly created state directories use `0700`; state
files and locks use `0600`. The last-payload file intentionally contains the
host payload; do not publish, attach, or commit it. Tests and `selftest` set
`AGENT_STATUSLINE_STATE` before package import and use only synthetic evidence.

## Verify it works

The safe first check is fully synthetic and never touches the live ledger:

```bash
agent-statusline selftest
```

For a visual preview of your own last payload, isolate the state explicitly:

```bash
# render from your last real payload without touching any live state
AGENT_STATUSLINE_STATE=$(mktemp -d) agent-statusline \
  < ~/.claude/statusline-last-payload.json
```

Ten labelled rows means you are done. Then check the wiring itself:

```bash
python3 - <<'PY'
import json, os
d = json.load(open(os.path.expanduser("~/.claude/settings.json")))
print("statusLine:", d["statusLine"]["command"])
for ev, groups in d.get("hooks", {}).items():
    for g in groups:
        for h in g["hooks"]:
            print(f"  {ev}: {h['command']}")
PY
```

## Layout

```
agent-statusline/
├── pyproject.toml          hatchling + hatch-vcs; version comes from git tags
├── install.py              stdlib-only bootstrap for installing from a checkout
├── src/agent_statusline/
│   ├── cli.py              the `agent-statusline` entry point and its subcommands
│   ├── installer.py        settings.json wiring for both install shapes
│   ├── statusline.py       the status line itself: ORDER, rows, main()
│   ├── selftest.py         isolated synthetic installed-renderer check
│   ├── diagnostics.py      allowlisted last-error breadcrumb
│   ├── render.py           colours, units, bars, width fitting  (host-agnostic)
│   ├── transcript.py       incremental .jsonl parsing
│   ├── probes.py           cached subprocess/file probes        (host-agnostic)
│   ├── ledger.py           cost ledger + `close` / `show` CLI   (host-agnostic)
│   ├── storage.py          locked, atomic, private persistence
│   ├── paths.py            the one place that knows where state lives
│   └── hooks/
│       ├── session_end.py     seals the ledger row on exit
│       ├── context_guard.py   warns at 80% context
│       ├── timestamp_user.py  TEMPORARY message timestamps
│       └── timestamp_stop.py  TEMPORARY message timestamps
├── tests/                  pytest; no test may touch the real ~/.claude
├── .github/workflows/      CI: lint, test matrix, install smoke test, build
└── docs/
    ├── FIELDS.md           every row, every field, and where it comes from
    ├── INTERNALS.md        data sources, adding a field, how signals were discovered
    ├── adrs/               architecture decision records, one per decision, with an index
    ├── DEFERRED.md         ideas considered and consciously not built
    ├── PORTING.md          adapting this to Codex or another agent
    ├── ROADMAP.md          promoted release sequence
    └── RESEARCH.md         measured findings and open questions
```

`statusline.py`, `transcript.py`, the hooks, and the installer know about
Claude-specific contracts. The modules marked host-agnostic provide reusable
primitives, but no second-host adapter ships today. See
[docs/PORTING.md](docs/PORTING.md).

## Updating

```bash
uv tool upgrade agent-statusline            # installed
git pull                                    # checkout: edits are already live
```

## Uninstalling

```bash
agent-statusline uninstall        # or: python3 install.py --uninstall
uv tool uninstall agent-statusline
```

That removes the symlink and the settings entries. Your ledger and history in `~/.claude/`
are untouched — delete them by hand if you want them gone.

## Development

```bash
uv sync --locked --all-groups
uv run --locked pre-commit install   # once in the primary clone
uv run --locked pre-commit run --all-files
uv run --locked pytest --cov=agent_statusline --cov-report=term-missing
uv build
```

The suite redirects state before importing the package; no test may touch the
real `~/.claude`. Development tool versions are locked in `uv.lock`. Linked
worktrees share the primary clone's Git hooks; install the hook only once, and
stage new files before `--all-files` so they are included in the gate.

Versioning is [hatch-vcs](https://github.com/ofek/hatch-vcs): there is no version string in
the source, and `git tag v1.2.3` is what makes a release. Tags are immutable
([ADR 0019](docs/adrs/0019-release-tags-are-immutable.md)) — a mistake in a released
version is fixed by a new patch version, never by moving the tag.

The CI workflow is designed to run Python 3.9–3.13 on Linux, plus one combined
job carrying lint, the dependency-policy guard, both install shapes, and the
build. **Hosted macOS is off by default** and requested through
`workflow_dispatch`, because a macOS job bills about ten times a Linux one and
Actions minutes are shared across every private repository
([ADR 0018](docs/adrs/0018-budget-hosted-ci.md)). Documentation-only changes
skip CI. Hosted workflows remain disabled until the repository visibility and
allowance boundary is settled; the locked local gate remains mandatory.

## Troubleshooting

**Nothing appears.** Claude Code silently swallows a status line that errors. Run
`agent-statusline selftest` first; it verifies the installed renderer without reading or
mutating live accounting. An unexpected renderer failure also leaves only its time and
exception type in `~/.claude/statusline-last-error.json`. If the self-test passes, use the
isolated visual-preview command above to inspect your real payload without touching the
live ledger.

**`ModuleNotFoundError: No module named 'agent_statusline'`.** In a checkout, the symlink
is missing or points somewhere stale — re-run `python3 install.py`. If installed, the tool
was removed or its environment was rebuilt — reinstall and re-run `agent-statusline install`.

**Rows are truncated with `…` even though the window looks wide.** By then the row has
already wrapped to two lines and still not fit, so it genuinely does not fit. The status
line re-measures on every redraw (roughly every 1–4 seconds while you are working), so a
resize is picked up almost immediately; if the session is completely idle, it lands on the
next redraw.

**The `git` segment is missing.** The directory is not a repository. If exactly one
child directory *is* one, its branch is shown prefixed with `↳`; with zero or several,
nothing is shown, because ambiguity is worse than absence.

**Costs look doubled.** Almost always caused by rendering against the live ledger by hand.
Read [ADR 0014](docs/adrs/0014-never-exercise-cost-paths-against-the-live-ledger.md) — it explains the
failure and how to repair the row.

**First commit fails with `Author identity unknown`.** A fresh machine has no git identity:

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```
