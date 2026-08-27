# Research

These findings are durable evidence and open questions, not implementation
commitments. Measurements are dated and should be repeated before they support
a new decision.

## Renderer performance

Measurements on a reference ARM64 macOS system on 2026-08-26, using medians of
12–40 isolated subprocess runs, decomposed the current warm renderer as:

| Boundary | Median | Share of Python render |
| --- | ---: | ---: |
| Interpreter startup | 14.7 ms | 42.3% |
| Project imports | 13.7 ms | 39.4% |
| Parsing, state, calculation, and rendering | 6.4 ms | 18.3% |
| Complete warm render | 34.7 ms | 100% |

A trivial compiled C executable measured 2.29 ms; adding equivalent file I/O
raised it to 2.53 ms. File I/O is therefore not the meaningful bottleneck.
Python import hygiene is the low-risk next step and is promoted to 0.3.1.

`subprocess`, `shutil`, and `argparse` were measured as material avoidable
top-level imports. An import-budget test is deterministic and may gate; elapsed
time on shared runners is noisy and should initially be recorded, not gated.
Comparing render time to the interpreter floor is more portable than asserting
an absolute millisecond threshold.

### Compiled implementation

A compiled one-shot could approach a roughly 2.5 ms warm floor and could replace
`ps` and Git subprocesses with native APIs. That is substantial headroom, but
the current renderer remains below the previously observed visible-flicker
boundary. A rewrite would introduce platform wheels, a native toolchain, a
larger release matrix, and fallback obligations.

If that boundary is revisited, Rust is the leading candidate because its
memory-safe JSON handling and maturin wheel path fit this workload. Cython is
not a useful shortcut: it can affect only the 18.3% computation portion while
retaining Python startup and imports. SQLite is also rejected at current scale;
its import and query overhead exceeded loading the small locked JSON ledger.

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

Codex CLI 0.149.1 accepts only a declarative list of built-in status widgets and
rejects unknown identifiers. The Python renderer therefore cannot run inside
that interface today. The safest current adaptation is the native widget preset
documented in `PORTING.md`; re-check after Codex upgrades.

As of 2026-08-26, OpenAI's command-backed status-line request
[`openai/codex#17827`](https://github.com/openai/codex/issues/17827) remained
open with substantial consolidated demand and no committed implementation
timeline. Treat it as a tracked external boundary, not an expected release.
Project-local configuration must never be allowed to register an executable
status command if such support arrives.

GitHub Copilot CLI has an experimental command-backed status line with JSON on
stdin and rendered stdout, and its payload overlaps the current project,
session, model, context, cost, duration, and token inputs. That validates an
adapter seam but does not justify speculative implementation.

Before sharing one monetary ledger across hosts, prove from an official or
isolated measured contract that the host supplies exact cost. Never infer
currency from tokens or a drifting price table.

## Repository visibility and CI

For a personal GitHub Free account, measured API responses showed that branch
protection and rulesets are unavailable while this repository is private but
become available if it is public. Standard hosted Actions are free for public
repositories. The trade is materially one-way: public forks cannot be recalled
by returning the source repository to private, and existing Actions logs become
public.

Repository visibility remains a maintainer decision. Before any public change,
audit historical workflow logs and the sanitized Git history directly. Do not
register a persistent self-hosted runner on a public repository that executes
untrusted pull-request code.

The existing cost-controlled workflow design intentionally tests Python
3.9–3.13 on hosted Linux, combines work that gains no safety from separate jobs,
skips documentation-only changes, keeps tags immutable, and makes hosted macOS
deliberate. It has not yet executed in its redesigned form, so syntax and local
equivalence are not hosted proof.

## Self-hosted runner boundary

GitHub permits self-hosted runners on physical machines, virtual machines, and
containers. `actions/runner-images` contains build definitions rather than a
registry of ready-to-pull images. It includes a real Ubuntu-slim Dockerfile and
macOS Packer templates with Anka and SSH-based provisioning paths.

A Linux ARM64 runner can operate inside Docker Desktop on Apple Silicon, but
container jobs require an explicit Docker-socket or Docker-in-Docker security
policy. Native macOS evidence requires a macOS runner rather than a Docker
container. Provisioning scripts intended for clean images must not be run on a
working desktop without a dedicated VM and an independent destructive-change
audit.

For this repository, routine hosted Linux is currently cheaper and simpler than
self-hosting it. A macOS runner has value only for deliberate platform
certification and must use a dedicated non-administrator account, repository
scope, no Full Disk Access, no personal credentials, and verified inability to
read unrelated workspaces or mounted media.
