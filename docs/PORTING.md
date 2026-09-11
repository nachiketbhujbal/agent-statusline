# Porting to other agents

## Current Codex boundary: native footer items, not this renderer

Codex's status line is **declarative, not a command.** The current official
[configuration reference](https://developers.openai.com/codex/config-reference/)
defines `tui.status_line` as an ordered list of footer-item identifiers (or
`null` to disable it):

```toml
[tui]
status_line = ["model", "context-remaining", "git-branch"]
```

The documented setting has no arbitrary-command form, so this Python renderer
cannot be registered there. Footer item names and defaults belong to Codex and
may change; use the current configuration reference rather than treating the
examples here as a compatibility contract.

This is the opposite design from Claude Code, which runs an arbitrary command and renders
whatever it prints. So a port is not a port — it is two different jobs.

### What Codex gives you natively

The documented footer can cover core location, model, Git, and context signals.
Representative mappings are:

| this repo's row | Codex widget(s) |
| --- | --- |
| `PROJECT` | `current-dir`, `git-branch` |
| `MODEL` | `model` or `model-with-reasoning` |
| `CONTEXT` | `context-remaining` |

### What has no Codex equivalent

- **Cache economics.** No hit rate, no TTL bucket, no effective multiplier. This is the
  single biggest loss, and it is the row that most often changes behaviour.
- **Token flow** split into reused / written / uncached.
- **Cross-session cost history** — `estimated-thread-cost` is this thread only, so no
  24h/7d/30d, no `all`, no conversation/fork accounting.
- **Machine pressure** — no RAM, disk, or process figures.
- **Width-aware truncation**, which Codex handles its own way.

### What ships for Codex today

No Codex adapter or hook ships in this package. Codex has an official
[hooks interface](https://developers.openai.com/codex/hooks/), but this project
has not established an authoritative Codex cost source or a safe installation
boundary for it. Claiming cross-agent accounting before those facts are measured
would violate the exact-money rule.

The existing Claude ledger remains queryable with `agent-statusline ledger
show`. A future Codex hook may reuse its host-independent arithmetic only after
the event contract and cost evidence are verified. That work is research, not a
current capability.

## Porting to a third agent

Ask one question first: **does the agent render an arbitrary command's stdout, or a fixed
widget list?**

- **Command-based** (Claude Code): this repo ports nearly whole. Write an adapter that maps
  the agent's payload into the shape `statusline.py` expects, and keep the renderer.
- **Widget-based** (Codex): the renderer is unusable. Map available fields onto
  native items and treat any ledger hook as new acquisition work requiring its
  own evidence and safety design.

### The seam

The package is layered, but several acquisition and installation modules remain
host-specific:

| module | host-specific? |
| --- | --- |
| `render.py` — colours, units, bars, width fitting | no |
| `probes.py` — cached `ps` / `vm_stat` / git / `statvfs` | no |
| `ledger.py` — cross-session cost accounting | no |
| `storage.py` — locked, private, atomic persistence | no |
| `paths.py` — where Claude-local state currently lives | partly |
| `diagnostics.py` — privacy-safe failure evidence | no |
| `transcript.py` — parses a Claude `.jsonl` | **yes** |
| `statusline.py` — reads the Claude payload, builds rows | **yes** |
| `installer.py` / `hooks/` — Claude settings and events | **yes** |
| `selftest.py` — synthetic Claude payload health check | **yes** |

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
