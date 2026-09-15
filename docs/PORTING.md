# Porting to other agents

## Current Codex boundary: native footer items, not this renderer

Codex's status line is **declarative, not a command.** The current official
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
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

No Codex adapter or hook ships in this package. Codex has an official stable
[hooks interface](https://learn.chatgpt.com/docs/hooks) whose common input
includes a session identifier and transcript path. That makes a future local
collector credible, but the same documentation says the transcript format is
not a stable hook interface. A current local inventory found exact token and
session evidence but no exact cost field.

The existing Claude ledger remains queryable with `agent-statusline ledger
show`. A future Codex hook may reuse private locked storage for non-currency
facts, but it must not update the currency ledger unless Codex supplies an exact
attributable cost contract. Acquisition would still not make this renderer
appear in Codex's widget-only footer. See [ADR 0046](adrs/0046-separate-host-acquisition-from-presentation.md).

## Porting to a third agent

Ask one question first: **does the agent render an arbitrary command's stdout, or a fixed
widget list?**

- **Command-based** (Claude Code): this repo ports nearly whole. Write an adapter that maps
  the agent's payload into the shape `statusline.py` expects, and keep the renderer.
- **Widget-based** (Codex): the renderer is unusable. Map available fields onto
  native items and treat any ledger hook as new acquisition work requiring its
  own evidence and safety design.

### The seam

The package is layered, and ADR 0046 makes the acquisition/presentation split
explicit. ADR 0047 adds the first implementation of that boundary: Claude's
payload and transcript are normalized by `acquisition.py` before the existing
renderer consumes them.

| module | host-specific? |
| --- | --- |
| `render.py` — colours, units, bars, width fitting | no |
| `probes.py` — cached `ps` / `vm_stat` / git / `statvfs` | no |
| `ledger.py` — cross-session cost accounting | no |
| `storage.py` — locked, private, atomic persistence | no |
| `paths.py` — where Claude-local state currently lives | partly |
| `diagnostics.py` — privacy-safe failure evidence | no |
| `transcript.py` — parses a Claude `.jsonl` | **yes** |
| `acquisition.py` — normalizes Claude payload and transcript facts | **yes** |
| `statusline.py` — builds the approved rows from normalized facts | presentation |
| `installer.py` / `hooks/` — Claude settings and events | **yes** |
| `selftest.py` — synthetic Claude payload health check | **yes** |

So a second host needs a new acquisition adapter and may reuse host-independent
components. Normalized facts cover identity, workspace, model, context, tokens,
limits, activity, and exact money. A fact is absent when its host does not
provide accountable evidence; an adapter never fills gaps with another host's
assumptions. The interface is internal in v0.4.1; v0.4.2 will define the public
session-metrics contract separately.

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
