# Research

These findings are durable evidence and open questions, not implementation
commitments. Measurements are dated and should be repeated before they support
a new decision.

## Renderer performance

Measurements on a reference ARM64 macOS system on 2026-08-26, using medians of
12–40 isolated subprocess runs, decomposed the warm renderer at that revision:

| Boundary | Median | Share of Python render |
| --- | ---: | ---: |
| Interpreter startup | 14.7 ms | 42.3% |
| Project imports | 13.7 ms | 39.4% |
| Parsing, state, calculation, and rendering | 6.4 ms | 18.3% |
| Complete warm render | 34.7 ms | 100% |

A trivial compiled C executable measured 2.29 ms; adding equivalent file I/O
raised it to 2.53 ms. In that sample, file I/O was not the meaningful bottleneck.
Python import hygiene is the lowest-risk next investigation, but the measurement
must be repeated against the release being optimized.

`subprocess`, `shutil`, and `argparse` were material avoidable top-level imports
in the measured revision. An import-budget test can be deterministic; elapsed
time on shared runners is noisy and should initially be recorded rather than
gated. Comparing render time with the interpreter floor is more portable than
an absolute millisecond threshold.

A paired 2026-09-12 repeat against exact v0.3.0 and the v0.3.1 implementation
used the same Python 3.9.6 environment on the reference ARM64 macOS machine.
Each interpreter, import, and warm result is the median of 40 isolated child
processes; cold results use 12 fresh state roots:

| Boundary | v0.3.0 | v0.3.1 implementation | Change |
| --- | ---: | ---: | ---: |
| Interpreter startup | 45.635 ms | 45.708 ms | informational floor |
| Project imports | 131.720 ms | 93.109 ms | -29.3% |
| Complete warm render | 148.885 ms | 105.270 ms | -29.3% |
| Complete cold render | 182.580 ms | 167.780 ms | -8.1% |
| Warm / interpreter | 3.263x | 2.303x | -29.4% |

The absolute values differ from the older interpreter and environment, which is
why elapsed time remains recorded evidence rather than a gate. The deterministic
release boundary is instead that a fresh renderer import excludes `argparse`,
`subprocess`, and `shutil`.

### Compiled implementation

A compiled one-shot could approach the roughly 2.5 ms floor observed in that
experiment and could replace process and Git subprocesses with native APIs. A
rewrite would also introduce platform wheels, a native toolchain, a larger
release matrix, and fallback obligations. Current evidence does not justify it.

If the boundary is revisited, Rust is the leading candidate because its
memory-safe JSON handling and maturin wheel path fit this workload. Cython would
retain Python startup and import cost. SQLite is also not justified at current
state scale; its measured import and query overhead exceeded loading the small
locked JSON ledger.

Open questions:

- RQ-1: Measure native process-table and direct Git reads against current cold
  and warm cached probes.
- RQ-2: Price a platform-wheel matrix, including whether Linux
  cross-compilation can avoid hosted macOS cost.
- RQ-3: Compare a persistent daemon plus spawned client with a compiled
  one-shot, including lifecycle and stale-state failures.
- RQ-4: Determine whether a native probe helper removes enough cold latency to
  justify distributing only part of a native stack.
- RQ-5: Measure normal render cadence across longer sessions before converting
  latency into duty-cycle claims.
- RQ-6: Map a real second host's payload against the approved rows before
  deciding whether multi-host support is an adapter or a redesign.

## Host interfaces

A 2026-09-14 repeat against installed Codex CLI 0.153.3, with local rollout
metadata also reporting 0.153.4, confirmed that `tui.status_line` remains an
ordered list of built-in footer identifiers. It has no arbitrary-command form,
so Codex still cannot run this Python renderer. This agrees with the earlier
2026-08-26 measurement of Codex CLI 0.149.1.

The same repeat found that Codex hooks are now a stable installed feature. The
official event contract supplies a session identifier, transcript path, current
directory, event name, model, and—where applicable—a turn identifier. This is
a credible local acquisition trigger, not a presentation surface. The official
documentation warns that the transcript format itself is not a stable hook
interface, so any reader must be shape-tolerant and proven with synthetic
fixtures rather than treating current JSONL as a versioned public schema.

The command-backed status-line request
[`openai/codex#17827`](https://github.com/openai/codex/issues/17827) was open in
that historical inspection. Its present state is deliberately not inferred
here; verify the upstream issue before promoting related work.

A historical GitHub Copilot CLI experiment exposed a command-backed status line
whose input overlapped project, session, model, context, cost, duration, and
token fields. That supports an adapter seam but does not justify speculative
implementation. Before sharing a monetary ledger across hosts, prove from an
official or isolated measured contract that the host supplies exact cost. Never
infer currency from tokens or a drifting price table.

A privacy-bounded 2026-09-14 inventory covered 496 local JSONL files totaling
about 2.47 GB without recording message contents, local paths, identifiers, or
private numeric values. A 48-file structural sample contained 10,217 valid JSON
records and no malformed rows; a separate 64-file sample found 1,498 token-usage
records. First-record metadata across 492 rollouts spanned seven observed CLI
versions from 0.147.0-alpha.6.5 through 0.154.0-alpha.6.2.

The observed token records consistently exposed input, cached-input,
cache-write-input, output, reasoning-output, and total-token counters at turn
and thread scopes. Other records exposed session, thread, root-turn and turn
identifiers, context-window size, rate-limit windows, and response timing. No
cost, USD, billing, or price field was found. The only money-adjacent key was a
boolean spend-control boundary, which cannot support an accountable currency
claim. Post-hoc approximate cost remains useful private analysis, but it cannot
enter this package's currency ledger or acquire a dollar label.

[ADR 0046](adrs/0046-separate-host-acquisition-from-presentation.md) records the
resulting architecture: acquisition is independent from presentation, Codex
tokens may become a local adapter input, and Codex rendering and exact money
remain separate capability gates.

## Repository visibility and CI

The repository's conservative workflow shape tests supported Python versions on
hosted Linux, combines work that gains no safety from separate jobs, skips
documentation-only changes, keeps tags immutable, and makes hosted macOS
deliberate. Both workflows are active and were exercised successfully through
v0.2.7. A pull-request run, its automatic merged-`main` run, and the tag-triggered
release are sufficient evidence; an extra manual dispatch of the same SHA is not.

Repository visibility remains a maintainer decision and is outside v0.2.8.
Before changing it, re-check current GitHub plan and ruleset behavior, audit the
complete Git history and historical workflow logs, and document the irreversible
effects of public forks and public logs. Do not rely on an old account-specific
measurement as current policy.

Do not attach a persistent self-hosted runner to a public repository if it can
execute untrusted pull-request code or read unrelated credentials and files.

## Self-hosted runner boundary

Runner-image repositories contain build definitions, not a universal registry
of ready-to-run images. Linux ARM64 can run in a container on Apple Silicon, but
container jobs still need an explicit socket or nested-container security policy.
Native macOS evidence requires a macOS runner rather than a Linux container.

For this project, routine hosted Linux remains simpler than maintaining a
self-hosted runner. A future macOS runner should use a dedicated
non-administrator account, repository scope, no broad disk access, no personal
credentials, and a verified inability to read unrelated workspaces or mounted
media. Provisioning intended for clean images must not be run on a working
desktop without a dedicated virtual machine and a separate destructive-change
audit.

## Compaction records and session isolation

A bounded read-only structural check on 2026-10-23 examined up to the first
16 MiB of each of 24 recent top-level Claude transcripts, with a two-MiB
per-line bound. It found three `system` / `compact_boundary` records and three
`isCompactSummary: true` records. Each summary's parent identifier matched the
preceding boundary identifier. No message contents, transcript paths, concrete
identifiers, or private token/cost values were retained in public evidence.
This verifies the observed pair shape, not every host version or compaction
variant. No real compaction was triggered for the experiment.

Synthetic fixtures cover boundaries without summaries, summary-only legacy
records, boundary/summary pairs split across redraws, partial lines, old-cache
replay, truncation, and independent compaction counts in six concurrent
renderer/hook sessions. A shared transcript cache is keyed by transcript path;
separate sessions must receive distinct transcript paths from the host.
Inherited history on resume or fork can legitimately produce equal counts.

The context guard's old missing-snapshot fallback reproducibly used a different
session's last-render window size with the current transcript's token count.
The v0.4.5 correction requires matching identity and omits the warning when
current-session window evidence is unavailable. It does not establish that the
reported real-world equal compaction counts were caused by cache crossover.

## Claude Code status-line capability audit

Checked 2026-11-07 against Anthropic's current
[status-line reference](https://code.claude.com/docs/en/statusline),
[cache policy](https://code.claude.com/docs/en/prompt-caching),
[API cache contract](https://platform.claude.com/docs/en/build-with-claude/prompt-caching),
and [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md#21251).
The API's per-TTL usage keys remain documented. No rename was found.

A synthetic reproduction on v0.5.7 showed a current warm/1h host signal being
ignored while older transcript evidence rendered 5m/COLD. Read-only cache hits
already advance the transcript timestamp; the timer is not write-only.
Mixed TTL history cannot be represented exactly by the newest write bucket.
v0.5.8 resolves the source-precedence defect and labels older-client inference.
This does not establish the cause in a particular private session.

| Host surface | Current support and next boundary |
| --- | --- |
| Model, effort, thinking, fast mode, output style | Existing `MODEL` fields |
| Session name and directory | Existing `PROJECT` fields |
| Context use and per-turn tokens | Existing `CONTEXT` and `TOKENS`; optional additional detail later |
| Session cost, timing, changed lines | Existing fields; host totals, not independent invoice evidence |
| Five-hour and weekly limits | Existing `USAGE` fields |
| Native cache lifetime | v0.5.8, host minimum 2.1.251 |
| Native cache performance counters | Separate optional slice |
| Cache miss causes | Separate optional slice; host minimum 2.1.260 |
| Agent identity, prompt identity, Vim mode | Available upstream; not yet exposed |
| Repository identity and worktree metadata | Local git facts supported; native metadata not yet exposed |
| PR/MR and review state | Not yet exposed |
| Gateway spend limits | Not yet exposed; estimated currency requires separate design |
| Subagent panel | Separate input/output protocol; needs its own adapter and opt-in installer contract |

Inventory is not a promise that every client provides every field. Each follow-up
must pin its supported schema, client minimum and absence behavior before coding.
Subagent panel support is not equivalent to the main renderer accepting task JSON.
No automatic host settings changes or network lookups are implied by this audit.

Two economic questions remain separate from native TTL precedence: the existing
relative multiplier applies fixed read/write weights across models and TTLs;
and host-reported session cost is described upstream as a client-side estimate,
which should not be represented as an independently reconciled bill. Audit those
claims in a dedicated correction before adding more currency presentation.

## Customization and refresh comparison

Checked 2026-11-07 against released source: agent-statusline v0.5.8,
[ccstatusline v2.2.34 usage guide](https://github.com/sirmalloc/ccstatusline/blob/v2.2.34/docs/USAGE.md)
and [widget types](https://github.com/sirmalloc/ccstatusline/blob/v2.2.34/src/types/Widget.ts),
and the distinct Rust project
[scottlz0310/agent-statusline v0.5.0](https://github.com/scottlz0310/agent-statusline/tree/v0.5.0).
Competitor code was inspected, not executed or installed. These are dated
feature comparisons, not equivalent-load speed or reliability benchmarks.

| Capability | This package v0.5.8 | ccstatusline v2.2.34 | Rust project v0.5.0 |
| --- | --- | --- | --- |
| Configuration | Optional TOML, schema 1, one canonical location | JSON, config-path option, import/export | TOML, config-path option/environment override |
| Selection/layout | Ten fixed rows, show/hide and 41 group selectors | Widgets and multi-line ordering | Module format strings and line ordering |
| Presentation | Default/plain, existing fixed formatting | Labels, symbols, numeric styles, themes, colors, conditional widget choices | Per-module styles/symbols/formats and thresholds |
| Interactive editor | Read-only discovery/show/example/synthetic preview; no editor | Interactive editor and live preview | Released TUI with layout/style editing and preview |
| System RAM | Built-in native pressure plus process scopes | Built-in Memory Usage widget | No corresponding module found in released config model |
| Disk | Built-in capacity/free-space fields | No built-in disk widget found in the inspected catalog; Custom Command can supply it | No corresponding module found in released config model |
| Timed host refresh | Not managed by our installer | Supports native refresh interval | Not assessed in this comparison |

Memory is therefore not unique to this package. Built-in disk and session-aware
process/memory integration distinguish the inspected defaults, but arbitrary
command widgets can reproduce individual metrics. A widget count is not evidence
of accounting accuracy. Our local-only runtime, stdlib dependency boundary,
collection-independent visibility, session isolation and attributable rolling
ledger are product commitments; no competitor-wide superiority is established.
The Rust TUI was verified in
[released command handling](https://github.com/scottlz0310/agent-statusline/blob/v0.5.0/src/main.rs)
and [configuration storage](https://github.com/scottlz0310/agent-statusline/blob/v0.5.0/src/tui/storage.rs),
rather than inferred from an inconsistent README implementation-status sentence.
Its configuration model is in
[engine/config.rs](https://github.com/scottlz0310/agent-statusline/blob/v0.5.0/src/engine/config.rs).

Anthropic's current [status-line reference](https://code.claude.com/docs/en/statusline#when-the-status-line-updates)
documents assistant-message/event updates and an optional timer, not only one
invocation per user turn. `statusLine.refreshInterval` accepts at least one
second and can run while idle. Events are debounced at 300 ms; another update
can cancel an unfinished invocation. ccstatusline's released guide identifies
Claude Code 2.1.97 as the refresh minimum, recommends 10 seconds on supported
fresh installs, and preserves an existing interval on reinstall. Verify the
current host minimum again when implementing our installer option.

A timer refreshes local observations and time-derived displays; it does not
guarantee fresh host account data or per-token streaming. Our next implementation
must prove repeated-payload accounting idempotence, session identity and cached
probe behavior. Compare installed commands under equivalent synthetic workloads
before making performance claims. The approved
[customization design](CUSTOMIZATION_DESIGN.md) and
[release sequence](ROADMAP.md#next-release-and-milestones) turn these findings
into focused work without adding profiles, alternate config locations,
runtime networking or a daemon.
