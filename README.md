# agent-statusline

[![CI](https://github.com/nachiketbhujbal/agent-statusline/actions/workflows/ci.yml/badge.svg)](https://github.com/nachiketbhujbal/agent-statusline/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](pyproject.toml)

A dense, width-aware status line for [Claude Code](https://claude.com/claude-code). It
reports what the session is doing, what it is costing, how well the prompt cache is
working, and how much machine it is using — all from data the agent already has, with **no
telemetry, no network calls, and no dependencies**.

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
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | what changed in each release, and what is queued for the next one |
| [docs/ROADMAP.md](docs/ROADMAP.md) | the 0.2.x release sequence and what each one is for |
| [docs/CODE_REVIEW.md](docs/CODE_REVIEW.md) | review findings, with the release that resolved each |

## Requirements

- **Python 3.9+**, standard library only. There is nothing to `pip install`.
- **Claude Code** (developed against v2.1.246).
- macOS or Linux. The `SYSTEM` row's memory probe is macOS-specific (`vm_stat`, `sysctl`);
  every other row is portable, and the row degrades to disk-only elsewhere rather than failing.
- Optional: `git`, for the `PROJECT` row.

## Install

```bash
uv tool install git+https://github.com/nachiketbhujbal/agent-statusline
agent-statusline install
```

Then restart Claude Code. `pipx install` and `pip install` work identically, and
once the repository is public the `git+ssh://` URL becomes just the package name.

`agent-statusline install` writes the `statusLine` entry and the four hook entries
into `~/.claude/settings.json`, pointing them at the installed executable. It backs the
file up first, preserves every unrelated setting and hook, and renders your last real
payload so you can see it working before restarting. Add `--dry-run` to see exactly what
it would touch — a dry run creates nothing, not even the configuration directory — and
`agent-statusline uninstall` to reverse it.

It only ever touches configuration it owns, and ownership means the exact command this
installation wrote — not a familiar-looking filename or interpreter. Unrelated top-level
settings, hook events, hook groups and matchers are preserved in place, including their
order and shape. A status line or hook belonging to another tool is never claimed, even
when its program happens to be named `agent-statusline` too, or — in a checkout — when
some other Python interpreter is paired with the script path this installation writes.

Installing refuses rather than overwrites: if a `statusLine` this package does not own is
already configured, or `~/.claude/statusline` is a symlink pointing at something else, the
install stops and says so, because the settings format holds only one status line and
replacing yours would be unrecoverable. Every such refusal happens before the first
change, so no backup, symlink, or temporary file is left behind. The same applies to a
`settings.json` that is unreadable, malformed, or not a JSON object: it is left byte for
byte as it was rather than guessed at.

If your `settings.json` is itself a symlink to another file inside your configuration
directory, the link is followed and the real file is updated, so the indirection and its
permissions survive. A link resolving *outside* that directory is refused rather than
followed — an installer that writes wherever a link points is a write-anywhere primitive.
Publication is bound to a configuration directory opened once, without following a
symlink at any step from the filesystem root down, and every read, backup, link change,
and write in the same install or uninstall reuses that same binding rather than
re-resolving the configuration directory's location partway through — so redirecting
publication by changing what occupies that location mid-operation, whether by a symlink
or an ordinary directory swap, is refused
([ADR 0020](docs/adrs/0020-own-only-managed-configuration.md)).

An expected failure partway through an install or uninstall — a full disk, a permission
error — cannot always avoid touching anything (the checkout symlink and the settings file
are two separate writes), so if one has already changed when the other fails, the change
is rolled back. That restoration is itself a filesystem operation and can itself fail in
the same rare conditions; when it does, the failure is reported rather than hidden, so a
link and settings left disagreeing are never silently mistaken for a clean failure.

One documented exception to "only what it owns": `showMessageTimestamps` is set to `true`
when absent and is deliberately *not* removed on uninstall, because a value already in
your settings cannot be told apart from one this installer added
([ADR 0015](docs/adrs/0015-timestamp-hooks-are-a-stopgap.md)).

Upgrading is `uv tool upgrade agent-statusline` followed by `agent-statusline install`
(the second step is only needed if the wiring itself changed).

### Or from a checkout, to hack on it

```bash
git clone https://github.com/nachiketbhujbal/agent-statusline.git
cd agent-statusline
python3 install.py
```

This symlinks `~/.claude/statusline` to the working tree, so your edits take effect with
no reinstall. **There is nothing to `pip install`** — `install.py` and the status line
itself are stdlib-only and run on the system Python. The installer detects which of the
two shapes it is in; you do not tell it.

### The commands

| command | what it does |
| --- | --- |
| `agent-statusline` | render a status line from a payload on stdin — what Claude Code calls |
| `agent-statusline install` | wire it into `settings.json` (`--dry-run` to preview) |
| `agent-statusline uninstall` | remove the settings entries and the symlink |
| `agent-statusline hook <name>` | run one hook: `session-end`, `context-guard`, `timestamp-user`, `timestamp-stop` |
| `agent-statusline ledger show` | print the cost ledger; `ledger close <id>` seals a row by hand |
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

Override the location with `AGENT_STATUSLINE_STATE=/some/dir` — useful for testing against
a throwaway directory, which is the *only* safe way to exercise cost paths (see
[ADR 0014](docs/adrs/0014-never-exercise-cost-paths-against-the-live-ledger.md)).

## Verify it works

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
│   ├── render.py           colours, units, bars, width fitting  (host-agnostic)
│   ├── transcript.py       incremental .jsonl parsing
│   ├── probes.py           cached subprocess/file probes        (host-agnostic)
│   ├── ledger.py           cost ledger + `close` / `show` CLI   (host-agnostic)
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
    └── PORTING.md          adapting this to Codex or another agent
```

Only `statusline.py` and `transcript.py` know what a Claude payload looks like; the modules
marked host-agnostic are reusable as-is. See [docs/PORTING.md](docs/PORTING.md).

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

That removes the symlink and the settings entries it can prove it added. A `statusLine`
command you replaced by hand, and a `~/.claude/statusline` symlink pointing somewhere
else, are left alone and reported rather than removed. Your ledger and history in
`~/.claude/` are untouched — delete them by hand if you want them gone.

If an install goes wrong, the timestamped `settings.json.bak.*` in your configuration
directory is the state from immediately before it ran. If your `settings.json` is a
symlink, restore by copying that backup over the *link target*, not over the link, or you
will replace the link with a regular file.

## Development

Uses [uv](https://docs.astral.sh/uv/) 0.12+ and a committed lockfile
([ADR 0023](docs/adrs/0023-use-a-locked-local-quality-gate.md)):

```bash
uv sync --locked --all-groups
uv run --locked pre-commit install    # once, from the primary clone
uv run --locked pre-commit run --all-files
uv run --locked pytest --cov=agent_statusline --cov-report=term-missing
uv build
```

`pytest` runs 213 tests, none of which touch `~/.claude`. `pre-commit` runs
repository hygiene checks, Ruff, Black, and mypy from the locked environment;
run it directly rather than relying on the installed git hook when working in
a linked worktree, since the hook itself is shared and installed once from the
primary clone.

Versioning is [hatch-vcs](https://github.com/ofek/hatch-vcs): there is no version string in
the source, and `git tag v1.2.3` is what makes a release. Tags are immutable
([ADR 0019](docs/adrs/0019-release-tags-are-immutable.md)) — a mistake in a released
version is fixed by a new patch version, never by moving the tag.

CI runs Python 3.9–3.13 on Linux, plus one combined job carrying lint, the
dependency-policy guard, both install shapes, and the build. **Hosted macOS is off by
default** and requested through `workflow_dispatch`, because a macOS job bills about ten
times a Linux one and Actions minutes are shared across every private repository
([ADR 0018](docs/adrs/0018-budget-hosted-ci.md)). Documentation-only pushes skip CI.

## Troubleshooting

**Nothing appears.** Claude Code silently swallows a status line that errors. Run the
verify command above; a traceback there is the answer.

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
