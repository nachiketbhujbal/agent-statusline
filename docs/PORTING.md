# Porting to other agents

## Read this first: Codex cannot run this script

Codex's status line is **declarative, not a command.** `~/.codex/config.toml` takes a list
of built-in widget identifiers and a colour toggle, and nothing else:

```toml
status_line = ["model-with-reasoning", "current-dir", "git-branch", "context-remaining", ...]
status_line_use_colors = true
```

Codex validates those identifiers against a fixed internal enum and rejects unknown ones
("terminal title configuration contains unknown item identifiers"). There is **no
`command`-type status line**, so there is nowhere to plug a Python script in. Verified
against `codex-cli 0.149.1` by inspecting the shipped binary; re-check after an upgrade.

This is the opposite design from Claude Code, which runs an arbitrary command and renders
whatever it prints. So a port is not a port — it is two different jobs.

### What Codex already gives you natively

Most of what this status line computes, Codex has a widget for. Enable these to get the
closest equivalent:

| this repo's row | Codex widget(s) |
| --- | --- |
| `PROJECT` | `project-name`, `current-dir`, `git-branch`, `branch-changes`, `pull-request-number`, `workspace-headline` |
| `MODEL` | `model`, `reasoning`, `model-with-reasoning`, `fast-mode`, `codex-version` |
| `CONTEXT` | `context-remaining`, `context-used`, `context-window-size`, `used-tokens`, `total-input-tokens`, `total-output-tokens` |
| `USAGE` | `five-hour-limit`, `weekly-limit` |
| `TOOLS` / `TIMING` | `run-state`, `task-progress` |
| `COST` | `estimated-thread-cost`, `thread-credits` |
| *(mode)* | `permissions`, `approval-mode` |

### What has no Codex equivalent

- **Cache economics.** No hit rate, no TTL bucket, no effective multiplier. This is the
  single biggest loss, and it is the row that most often changes behaviour.
- **Token flow** split into reused / written / uncached.
- **Cross-session cost history** — `estimated-thread-cost` is this thread only, so no
  24h/7d/30d, no `all`, no conversation/fork accounting.
- **Machine pressure** — no RAM, disk, or process figures.
- **Width-aware truncation**, which Codex handles its own way.

### What you *can* port to Codex today

**The ledger.** Codex has a hook system with these events: `SessionStart`, `SessionEnd`,
`UserPromptSubmit`, `Stop`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`,
`PostCompact`, `SubagentStart`, `SubagentStop`.

`SessionEnd` is enough to keep `cost-ledger.json` populated from Codex sessions too, giving
you one cross-agent spend history even though Codex's own status line cannot display it.
`src/agent_statusline/ledger.py` is deliberately free of Claude-specific assumptions — it takes a session id,
a cost, and a timestamp — so the work is writing a Codex `SessionEnd` hook that calls
`ledger.apply_cost` / `ledger.close_session`, not changing the ledger.

Query it from anywhere:

```bash
python3 ~/.claude/statusline/ledger.py show     # or: agent-statusline-ledger show
```

## Porting to a third agent

Ask one question first: **does the agent render an arbitrary command's stdout, or a fixed
widget list?**

- **Command-based** (Claude Code): this repo ports nearly whole. Write an adapter that maps
  the agent's payload into the shape `statusline.py` expects, and keep the renderer.
- **Widget-based** (Codex): the renderer is unusable. Port the ledger via hooks, map the
  rest onto whatever widgets exist, and document the gaps.

### The seam

The package is already layered, and only one layer is host-specific:

| module | host-specific? |
| --- | --- |
| `render.py` — colours, units, bars, width fitting | no |
| `probes.py` — cached `ps` / `vm_stat` / git / `statvfs` | no |
| `ledger.py` — cross-session cost accounting | no |
| `paths.py` — where state lives | no |
| `transcript.py` — parses a Claude `.jsonl` | **yes** |
| `statusline.py` — reads the Claude payload, builds rows | **yes** |

So a second command-based agent needs a new acquisition layer and reuses everything else.
The clean refactor is `src/agent_statusline/adapters/<agent>.py`
exposing one function that returns a normalised dict:

```python
{
  "model": {"name": str, "effort": str|None},
  "context": {"used_pct": float, "size": int, "current": {...}},
  "limits": {"5h": {"pct": float, "resets_at": int}, "7d": {...}},
  "cost": {"usd": float, "lines_added": int, "lines_removed": int},
  "session": {"id": str, "name": str|None, "transcript": str|None},
  "workspace": {"cwd": str, "project_dir": str, "added_dirs": [str]},
}
```

Everything downstream consumes that dict, and adding an agent becomes one adapter file
plus a row-availability table. **This has not been built** — the current code reads the
Claude payload directly. Do it when the second command-based agent actually arrives, not
before; a normalisation layer designed against one real consumer and one hypothetical one
tends to fit neither.

### What to keep no matter the agent

- **The decisions in [adrs/](adrs/README.md)** — especially "if it cannot be accounted
  exactly, it does not get a dollar sign", and never testing against the live ledger.
- **State separate from code** (`paths.py`). A shared repo across machines with a ledger
  committed into it is a merge conflict waiting to happen.
- **Probe caching.** Every agent redraws its status line far more often than you expect.
- **Width fitting with ordered segments.** Whatever the host, terminals get narrow.

## Handing this to an agent to rebuild

If you are pointing Codex (or any agent) at this repository to recreate the setup, give it
these in order:

1. `README.md` — what it is and how to install it.
2. `docs/adrs/` — **before** it writes any code, so it does not rebuild the removed
   cache bar or re-derive a dollar figure that was deliberately dropped.
3. `docs/INTERNALS.md` — data sources and the discovery method for anything undocumented.
4. `docs/FIELDS.md` — the target output.
5. This file — so it checks the host's status-line model before assuming a port is possible.

The single most valuable instruction to give it: **the field names in `INTERNALS.md` were
verified against real transcripts and are documented nowhere else — do not guess at them,
and re-run the discovery snippet if the host version has moved.**
