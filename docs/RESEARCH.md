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
