# Internals

## The four data sources

| source | cost | used for |
| --- | --- | --- |
| **payload** | free | context, rate limits, cost, model, workspace — piped in as JSON on stdin |
| **transcript** | cheap | cumulative session facts, parsed incrementally from a byte offset |
| **probe** | a subprocess | git, `ps`, `vm_stat`, `sysctl`, `statvfs`, account flags — always cached |
| **ledger** | locked local state | spend history across sessions |

Historical measurements found a roughly 30ms warm redraw against a roughly
15ms bare-interpreter floor, down from about 110ms before the Git probe was
collapsed. The v0.3.1 repeat records a separate paired baseline and candidate
from the current environment. These are observations from one machine, not a
cross-platform performance guarantee; [RESEARCH.md](RESEARCH.md) carries the
dated evidence and [ADR 0040](adrs/0040-remove-avoidable-hot-path-imports.md)
keeps elapsed time outside the release gate.

In that same historical measurement, cold costs were: `ps` ~29ms · Git bundle
~35ms · `vm_stat` ~6ms · `sysctl` ~4ms · `~/.claude.json` ~1ms · `statvfs`
~0ms. Cache TTLs remain: Git 3s · processes/memory 8s · disk 30s · account 30s.

Probe observations are retained for seven days and capped at 256 rows. The
active row survives count pruning. Transcript observations are retained for 35
days and capped at 512 rows while preserving the active transcript; its access
time is touched at most hourly. The diagnostic rate-limit JSONL is compacted at
one MiB. Ordinary unchanged rate-limit renders still read only the last four
KiB; full scanning happens only at the compaction boundary. See
[ADR 0025](adrs/0025-bound-ephemeral-observation-state.md).

If flicker ever returns, the next lever is the `ps` sweep (raise its TTL or narrow it),
then Python startup itself, which is the hard floor.

Run the isolated informational benchmark from a synchronized development
environment; it never reads live payload, transcript, ledger, or probe state:

```bash
uv run --locked python scripts/benchmark_renderer.py
```

## Incremental transcript parsing

`statusline-transcript.json` stores a **byte offset plus accumulated totals** per
transcript, so each redraw reads only the bytes appended since the last one. A partial
trailing line is held back rather than parsed.

`SCHEMA` in `transcript.py` versions the shape of those totals ([ADR 0007](adrs/0007-incremental-transcript-with-versioned-totals.md)).
**Bump it whenever you add or change an accumulated field** — without the bump, existing caches keep their old shape
and the new field stays empty forever, with no error anywhere.

## Width fitting

The payload carries **no terminal width**, and neither `stdin`, `stdout`, `stderr` nor
`/dev/tty` is a terminal inside the status-line subprocess — all four raise `OSError`.

What *does* work: Claude Code exports **`COLUMNS`** into the subprocess environment. The
historical implementation read it through `shutil.get_terminal_size()`; v0.3.1 reads it
directly to avoid importing `shutil`. Measured directly from inside a live render before
that replacement:

```
stdin/stdout/stderr fd     -> OSError (pipes)
/dev/tty                   -> OSError (not attached)
COLUMNS                    -> "180"          <-- the only working source
shutil.get_terminal_size() -> (180, 50)
```

The direct implementation preserves positive `COLUMNS`, then tries the terminal API, then
uses the existing 120-column fallback. A terminal API result of zero columns is unusable
and also selects that fallback. This makes the edge deterministic across supported Python
versions: Python 3.9's `shutil` returned zero there, while newer Python versions already
substitute the fallback.

> `ps eww <claude-pid>` does **not** show `COLUMNS` — the parent process lacks it and
> Claude Code injects it per status-line spawn. Do not conclude anything from the parent
> environment; measure from inside a render.

It is read **inside `row()` on every call**, never cached at module level. The status line
is a fresh process per redraw and redraws land every ~1–4 seconds while you work, so a
live terminal resize is picked up almost immediately. A module-level constant would freeze
the layout at whatever width the first render happened to see.

`row(label, segs)` then fits the row in three stages, in this order:

1. **Sanitize and clip** each segment to the budget (`sanitize()` and `clip()`), so one
   oversized segment cannot overflow a line on its own. Only exact package-owned SGR
   styling survives; other escapes and Unicode control, format, or surrogate characters
   are removed. A reset is appended so a cut inside a coloured run cannot leak colour into
   the rest of the line.
2. **Pack** segments onto up to `MAXLINES` (2) lines. A row that fits on one line stays on
   one line — wrapping only happens when the content genuinely does not fit. Continuation
   lines are indented by `LABEL` spaces so the row still reads as one block. The indentation
   follows an SGR prefix because Claude Code was observed trimming raw leading whitespace;
   this host behavior must be re-verified if the interface changes.
3. **Truncate** whatever is left over, marking it with `…`.

Wrapping before truncating is deliberate. Claude Code caps how many lines the status line
may occupy and drops whole rows from the bottom when it runs out, so unbounded wrapping
would trade "lose the least important segment of a row" for "lose the `TIMING` row
entirely". Two lines is the compromise: enough to keep almost everything at realistic
widths, bounded enough that ten rows cannot silently become twenty.

Because colour escapes must not count toward the budget, `vis()` preserves only intentional
SGR styling and measures printable terminal cells. Combining marks occupy zero cells,
wide/full-width characters occupy two, and other printable characters occupy one. Clipping
stops only between complete code points. Measuring `len()` directly both miscounts Unicode
and makes every coloured row look roughly twice as wide as it is.

**Ordering segments is a design decision, not an implementation detail** — the last
segment in the list is the first thing a narrow terminal loses.

## Row order

Rows are built into a dict keyed by name and emitted in the sequence given by `ORDER` in
`statusline.py`. Reordering the status line is a one-line change there rather than a
reshuffle of `main()`, and a row with nothing to say is simply absent from the dict.

```python
ORDER = ["PROJECT", "MODEL", "CONTEXT", "USAGE", "COST",
         "SYSTEM", "TOOLS", "CACHE", "TOKENS", "TIMING"]
```

## Adding a field

1. **Decide the source.** Payload (free), transcript (cheap), probe (subprocess — must be
   cached), ledger, or derived.
2. **Transcript field?** Add it to `_blank()` *and* `_absorb()`, then **bump `SCHEMA`**.
3. **Probe?** Add a function to `probes.py` and call it via `pr.probe(key, ttl, fn)`.
   **Never call a subprocess directly from `statusline.py`.**
4. **Money?** Only if it can be accounted exactly — see [ADR 0001](adrs/0001-exactly-accountable-money.md).
5. **Place it in its row's segment list by importance.** Trailing segments are dropped first.
6. **Preview it** with the recipe below, never against the live ledger.
7. **Document it** in [FIELDS.md](FIELDS.md).

## Safe preview recipe

Running `statusline.py` by hand mutates the live ledger and can corrupt costs. Point it at
a throwaway state directory instead:

```bash
AGENT_STATUSLINE_STATE=$(mktemp -d) COLUMNS=180 \
  python3 ~/.claude/statusline/statusline.py < ~/.claude/statusline-last-payload.json
```

The installed self-test is the safest complete check because it uses only
synthetic evidence and fresh private state:

```bash
agent-statusline selftest
```

The test suite is the faster development loop:

```bash
uv run --locked pytest tests -v
```

`tests/conftest.py` redirects `AGENT_STATUSLINE_STATE` **before** any package import,
because `paths.STATE_DIR` is resolved at import time. No test may touch the real
`~/.claude`.

To check width behaviour across sizes, loop `COLUMNS`:

```bash
for w in 220 180 150 120 100 80; do
  echo "--- $w ---"
  AGENT_STATUSLINE_STATE=$(mktemp -d) COLUMNS=$w \
    python3 ~/.claude/statusline/statusline.py < ~/.claude/statusline-last-payload.json
done
```

## The payload

Every key Claude Code pipes in, as of v2.1.246. Regenerate with:

```bash
python3 -m json.tool ~/.claude/statusline-last-payload.json
```

| path | status |
| --- | --- |
| `context_window.context_window_size` | used |
| `context_window.current_usage.{input,output,cache_creation_input,cache_read_input}_tokens` | used |
| `context_window.used_percentage` | used |
| `context_window.remaining_percentage` | UNUSED — inverse of `used_percentage` |
| `context_window.total_input_tokens` / `total_output_tokens` | UNUSED — per-request, **not** session totals |
| `cost.total_cost_usd` | used — authoritative, never recompute |
| `cost.total_duration_ms` / `total_api_duration_ms` | used |
| `cost.total_lines_added` / `total_lines_removed` | used |
| `cwd`, `session_id`, `session_name`, `transcript_path`, `version` | used |
| `effort.level` | used |
| `exceeds_200k_tokens` | UNUSED — misleading, use `context_window_size` |
| `fast_mode`, `thinking.enabled` | used |
| `model.display_name` / `model.id` | used |
| `output_style.name` | used |
| `prompt_id` | UNUSED |
| `rate_limits.five_hour.{used_percentage,resets_at}` | used |
| `rate_limits.seven_day.{used_percentage,resets_at}` | used |
| `workspace.current_dir` / `project_dir` / `added_dirs` | used |

**There is no `permission_mode` in the payload.** The `MODEL` row reads it from the
transcript's `permissionMode` entries instead.

## Transcript signals

Derived by `_absorb()`, one entry at a time. Field names were verified against real
transcripts — they are **not documented anywhere**, so do not guess at them.

| signal | where it lives |
| --- | --- |
| token counts | `message.usage.{input,output,cache_creation_input,cache_read_input}_tokens` |
| thinking tokens | `message.usage.output_tokens_details.thinking_tokens` |
| cache TTL bucket | `message.usage.cache_creation.{ephemeral_1h,ephemeral_5m}_input_tokens` |
| service tier | `message.usage.service_tier` |
| web search/fetch | `message.usage.server_tool_use.{web_search_requests,web_fetch_requests}` — UNUSED |
| per-turn duration | `type:"system"`, `subtype:"turn_duration"` -> `durationMs` |
| hook health | `type:"system"`, `subtype:"stop_hook_summary"` -> `hookInfos[].durationMs`, `hookErrors` |
| slash commands | `type:"system"`, `subtype:"local_command"` -> `<command-name>` in `content` |
| tool calls | `message.content[]` blocks, `type:"tool_use"` -> `name`, `input.file_path` |
| tool errors | `message.content[]` blocks, `type:"tool_result"` with `is_error` truthy |
| api errors | assistant entries with `message.model == "<synthetic>"` |
| subagents | top-level `isSidechain` |
| permission mode | top-level `permissionMode` |
| last activity | top-level `timestamp` on assistant entries (drives cache expiry) |

Other `system` subtypes seen but unused: `informational`, `away_summary`. Other entry types
seen: `mode`, `permission-mode`, `atis-latch`, `file-history-snapshot`, `file-history-delta`,
`last-prompt`, `ai-title`, `attachment`, `queue-operation`.

## Dead ends — already searched, do not redo

| wanted | verdict |
| --- | --- |
| credit balance / remaining | **Not available.** Not in the payload, not in `~/.claude.json`, no non-interactive CLI |
| cache TTL / expiry field | **Not in the payload.** But the TTL *is* observable from the `cache_creation` buckets |
| terminal width in the payload | **Not there.** `COLUMNS` in the subprocess env is the only source — see [width fitting](#width-fitting) |
| session cost broken down by model | not in the payload; `~/.claude.json` has `projects.<dir>.lastModelUsage`, but it is last-request, not cumulative |
| rate-limit history | nothing cached on disk; now logged locally by `rl_log()`; see [ADR 0009](adrs/0009-suppress-derived-rate-limit-figures-in-overage.md) |
| per-message cost in transcripts | **does not exist**; only token counts |
| native message timestamps | gated behind the server-side flag `tengu_silk_hinge` |

Each row cost real time to establish. Before re-investigating any of them, read
the row and then the ADR it points at.

## How to discover more

The method that found all of the above, reusable verbatim — point `D` at a project's
transcript directory and count what actually appears:

```python
import json, glob, collections, os
D = os.path.expanduser("~/.claude/projects/<project-dir>")
types = collections.Counter(); keys = collections.Counter(); sub = collections.Counter()
for p in glob.glob(f"{D}/*.jsonl"):
    for line in open(p):
        try: e = json.loads(line)
        except Exception: continue
        types[e.get("type")] += 1
        keys.update(e.keys())
        if e.get("type") == "system": sub[e.get("subtype")] += 1
print(types); print(keys.most_common(25)); print(sub)
```

Then dump one example of each interesting subtype in full.

## Reading Claude Code's own behaviour out of the binary

The permission-mode colour table in [FIELDS.md](FIELDS.md) was not guessed — it was read
out of the shipped binary, which is the right move whenever you want the status line to
*match* the host rather than invent its own convention:

```bash
B=~/.local/share/claude/versions/<version>
strings -a "$B" > /tmp/cc.strings
grep -o 'auto:{title:.\{0,200\}' /tmp/cc.strings     # mode -> colour key
grep -o 'warning:"ansi:[a-zA-Z]*"' /tmp/cc.strings   # colour key -> ansi colour
```

This is inspection of a local file for interoperability. It is also **version-specific**:
re-check it after a Claude Code upgrade rather than assuming the mapping held.
