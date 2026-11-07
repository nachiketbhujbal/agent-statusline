# Customization and refresh design

This is the approved direction, recorded with v0.5.9; it is **not the installed
configuration reference**. The [README](../README.md#configure-the-view) and
[field catalog](FIELDS.md#configurable-field-groups) describe shipped schema 1.
The [roadmap](ROADMAP.md#next-release-and-milestones) assigns focused slices.
Only v0.5.9 is the current implementation target. Later numbers are planning
slots; fixes can take any next patch and shift the remaining work.

## Product contract

- Keep one optional TOML file: `~/.config/agent-statusline/config.toml`, with
  the existing absolute `XDG_CONFIG_HOME` convention. No profiles, `--config`,
  project discovery, alternate path environment variable, or per-host config files.
- Remain useful without a file. Preserve the approved ten-row default, field
  priorities, current omissions, plain output, and existing environment overrides.
- Provide a finite catalog of fields and formatting choices. No shell widgets,
  executable templates, arbitrary expressions, runtime plugins or network sources.
- Treat collection, calculation and persistence as independent from the view.
  Row/element hiding, conditions, width fitting and layouts never suppress
  ledger updates, transcript consumption, probe scheduling or metric computation.
  Hiding `24h` must leave its next visible value as accurate as retained evidence
  permits. Keep `≥` and source/estimate qualifiers whenever required.
- Collection still needs an invocation or supported hook; this is not a promise
  to observe events while the host and package are stopped. Missing historical
  evidence stays missing. Existing explicit metrics-publication opt-out remains
  distinct from hiding fields; it does not disable the cost ledger.
- Keep Python 3.11+, standard-library runtime, local state, private locked atomic
  writes and session isolation. Launch editor code only for an editor command.

## Configuration model before the editor

0.6.0 introduces schema 2 for the richer view contract. It continues accepting
schema 1 unchanged. Migration is explicit and previewed; a renderer never rewrites
configuration. Earlier versions reject schema 2 as a whole and fall back to
defaults plus existing environment values, so downgrade guidance must make that
visible. Retain all 41 existing group IDs and their meanings. The new catalog
records each independently displayable element's row, parent group, type, source,
default inclusion, availability, priority and allowed formatting/conditions.

Rows remain `show`/`hide`. Group lists remain whitelist filters in canonical
priority order. Add separate per-element `show`/`hide` overrides, initially for
the existing compound groups. For example, the proposed schema-2 syntax is:

```toml
schema_version = 2

[display.rows]
SYSTEM = "show"

[display.fields]
COST = ["session", "rolling", "history", "lines", "credits"]

[display.elements.COST]
"rolling.24h" = "show"
"rolling.7d" = "hide"
"rolling.30d" = "show"
```

These keys are **planned**, not accepted by v0.5.9. Initial element inventory
must cover each compound group, including rolling periods, history totals and
counts, input/output/thinking throughput, per-window rate/projection/reset,
memory/process details, token buckets and timing statistics. Atomic groups keep
their existing selector rather than acquiring duplicate names. Discovery, check,
show, example, preview and editor all use this one catalog, with no separate UI
field list. Every final element ID is documented and tested before it ships.

Apply visibility in this order: row gate, existing group gate, element gate,
optional condition, existing evidence rules, layout, cell-width fitting.
An element's `show` cannot resurrect a hidden row or excluded group. An omitted
override preserves the original inclusion. Explicit `show` does not invent data
or disable width fitting. Unknown/duplicate IDs, invalid enums and incompatible
types reject the entire file, consistent with today's fallback/check contract.

New native host elements are opt-in even when their parent group is visible;
they do not silently enlarge the existing default view. Collector normalization
is independent of selection. Each new fact documents scope, source, supported
host/client version, absence behavior and freshness. New public metrics fields
require their own versioned contract; the view catalog does not change metrics
schema 1 implicitly.

## Interactive editor: the first follow-up to schema 2

0.6.1 delivers `agent-statusline config edit` for row, group and element
visibility, plain/default color, and synthetic width preview. It edits the one
canonical file. The first release is useful without layouts or a theme engine.
Use standard-library terminal support on supported macOS/Linux terminals,
keyboard navigation and a line-oriented fallback; retain zero runtime dependencies.

The editor loads one immutable starting snapshot, edits a draft, validates with
the runtime resolver and previews through the regular formatter. Display the
effective source and environment overrides so an overridden edit is understandable.
Provide undo, reset-to-default for the selected setting, a visible diff, explicit
Save/Cancel and an unsaved-change exit choice. Never render live session data,
open the ledger, run probes or write Claude settings for a preview.

Saving is one private atomic transaction for package configuration, with a
backup and a concurrent-edit check. Preserve comments and unrelated TOML text
using bounded edits to recognized assignments; reparse and compare the intended
semantic result before replacement. Do not solve this by adding a TOML runtime
dependency. If a valid but unusual representation cannot be edited losslessly,
refuse the write and show a proposed patch for manual editing. Invalid files
are diagnosed, not silently replaced. A schema-1 migration uses the same diff
and explicit save. Cancelling leaves exact prior bytes and permissions intact.
Later features extend this editor in their own slice rather than postponing it.

## Presentation after visibility

Add typed options with product-defined defaults and enum choices:

| Area | Intended control | Constraint |
| --- | --- | --- |
| Paths | Relative/home-abbreviated/full and segment limit | Keep workspace identity and sanitize terminal text |
| Numbers | Compact or precise; bounded decimal places | Do not round away a lower-bound or estimate qualifier |
| Units and time | Memory units, compact duration, local/UTC clock format | Same source values; no price conversion or invented precision |
| Labels and symbols | Full/short labels, Unicode/ASCII symbols and bars | Product-defined text; plain means no styling, not ASCII |
| Palette | Semantic normal/muted/warning/critical roles and accessible built-ins | Keep warnings distinguishable without color; plain wins |
| Thresholds | Typed visual thresholds for percentages | Separate from context-guard warning behavior |
| Conditions | `available`, `nonzero`, `active`, bounded numeric thresholds | Missing is not zero; no expression language or data collection effects |

The implementation slice must finalize exact TOML keys, enum domains and
per-element applicability in a follow-up ADR. This document fixes the model and
constraints without advertising unimplemented keys as usable configuration.
No named runtime profiles or competing config locations are introduced. Editor
reset actions operate on the same document, not on a profile system.

## Optional layouts

The default layout remains the current ten rows, order and field priorities.
0.7.0 adds only opt-in ordering of existing canonical rows; it does not make
users author templates. Follow with field ordering, editor reorder controls,
then density/separator/wrap choices in separate releases. Visibility stays in
the visibility tables rather than being encoded by missing layout entries.
Require a complete, duplicate-free row order when one is specified. A per-row
field order prioritizes listed known elements and appends other enabled elements
in canonical order, preserving future opt-ins without duplicating fields.

Keep canonical IDs and row meanings. Width fitting remains deterministic for
ANSI, Unicode and ASCII and may drop lower-priority visible details. No physical
line may exceed the host's cell width. A new layout must not hide the fact that
a value is partial, estimated, stale or unavailable. Custom rows, arbitrary
cross-row duplication and a programmable formatting language remain deferred.

## Refresh and freshness

Claude's documented `statusLine.refreshInterval` supports an integer interval
of at least one second, in addition to assistant-message and other event updates.
It can redraw an idle session while other work changes local state. The host
debounces events and cancels an in-flight renderer when another update arrives;
this is not a promise of per-token streaming or an exact refresh deadline.
See the dated [research](RESEARCH.md#customization-and-refresh-comparison).

The planned 0.5.x refresh slice adds explicit installer controls for setting or
removing that owned status-line interval, with dry-run output and supported-host
detection. Omission preserves an existing interval; fresh installs retain today's
event-driven default. Recommend 10 seconds as an initial opt-in, not a forced
setting. Check the installed host's support before introducing the key. Do not
modify unrelated settings, hooks or idle-compaction policy. TOML editing must
not secretly write Claude settings; the editor may later explain or launch the
same explicit installation action with its own preview.

Timed redraws use normal acquisition and collection, cached probes and incremental
transcript parsing. Repeated payloads must not accrue duplicate cost or compaction
events or extend a host observation's freshness. Session-bound facts stay bound
to their identity. Local rolling totals can reflect another local session's new
ledger entry on the next redraw, while cached process/Git probes update on their
normal TTLs. Host rate limits and other remote/session facts can remain stale
until that host supplies new evidence; a timer cannot refresh Anthropic's data.
Do not borrow another session's context, cache state or tool counts to fill gaps.

No daemon, runtime network polling, auto-installation or TTL reduction is needed
for the first refresh feature. Any further refresh mechanism needs measured
benefit and a host-supported contract before it enters the implementation plan.

## Performance and acceptance

Measure paired baseline/candidate installed commands with identical synthetic
inputs and disposable state. Record interpreter/import floor, cold and warm
median/p95, config overhead, incremental transcript size, probe cache hits/misses,
state-lock contention and six concurrent sessions at event, 10-second and
1-second cadences. Include hidden/all-visible views to prove that hiding only
changes presentation. Report hardware, Python, sample size and exact commits;
do not claim a Rust speed advantage or a Python win without equivalent work.

Keep existing deterministic import/probe/width checks. Add relevant regression
coverage per slice rather than brittle wall-clock gates on shared runners.
Investigate demonstrated overhead in imports, repeated parsing, probe scheduling
or aggregation before native helpers, daemons or a language rewrite. Optimization
must preserve collection completeness, session identity, locks and accounting.

Every feature retains the repository's complete local gate, independent exact-SHA
review, hosted evidence and isolated installed-artifact check. Tests use synthetic
homes, settings and ledgers. Before shipping refresh, prove duplicate-payload
idempotence, idle cross-session rolling totals, normal TTL behavior and preservation
of unrelated settings. Before shipping element controls, prove hidden/re-shown
cost and metric parity, default output parity and narrow-width behavior. Before
shipping the editor, prove save/cancel, comments, migration, conflict refusal,
unreadable-file refusal and absence of live-state or implicit host-setting writes.

## Host generalization

Reuse normalized facts, the view catalog, private storage and metrics where
their semantics match; keep host adapters, installation and event protocols
separate. Claude's subagent panel has a batch input/JSONL output protocol and
requires a separate adapter. Codex acquisition can support non-currency local
metrics without implying that its widget-only footer runs this renderer.
Host identity must namespace state before any multi-host collector ships.
Missing host facts remain unavailable; no estimated token-price table enters
the existing currency ledger. Other hosts enter only after current official
contracts and synthetic fixtures establish their capabilities.

See [PORTING.md](PORTING.md) and [ADR 0046](adrs/0046-separate-host-acquisition-from-presentation.md).
