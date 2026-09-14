# ADR 0046: Separate host acquisition from presentation

- Status: Accepted
- Date: 2026-09-14

## Context

The existing process is both a Claude Code acquisition client and a terminal
renderer. Claude Code invokes an arbitrary command, supplies a structured JSON
payload, and identifies a transcript. That makes acquisition and presentation
look like one interface even though they are separate responsibilities.

Codex has a different boundary. Its `tui.status_line` setting remains an
ordered list of built-in footer identifiers, not an arbitrary command. The
installed Codex CLI does, however, expose stable lifecycle hooks. Their common
input includes a session identifier, current directory, event name, model, and
transcript path. The official hook documentation explicitly says the transcript
format is not a stable hook interface.

A bounded 2026-09-14 inspection of local Codex rollouts found exact token
counters, session and turn identifiers, context-window size, and rate-limit
metadata across several installed CLI versions. It found no exact cost or USD
field. Codex's native `estimated-thread-cost` footer item is presentation owned
by Codex, not an attributable value supplied to this package.

Treating the rollout as a stable payload, treating a hook as a rendering
surface, or reconstructing dollars from tokens and a price table would make
unsupported claims and violate ADR 0001.

## Decision

Define host acquisition independently from host presentation.

An acquisition adapter may emit only normalized facts that its host evidence
actually supplies. The internal boundary groups facts by identity, workspace,
model, context, tokens, limits, activity, and exact money. Missing groups stay
absent; adapters must not manufacture parity with another host.

Every currency value entering the shared ledger must be an exact cumulative
host value with attributable session identity and lifecycle semantics. Token
counts, a native estimated-cost widget, or a locally maintained price table do
not satisfy that contract. Until Codex exposes such a value, a Codex adapter
must omit exact money and cannot update the currency ledger.

Presentation is a separate capability decision:

- a command-backed host may use the existing renderer after its normalized
  facts are mapped to the approved rows;
- a widget-backed host may use its native widgets, while an acquisition hook or
  query command records or reports additional local facts separately;
- acquisition support does not imply that this renderer runs in that host.

Codex hook support, if implemented, will be explicit and opt-in. It will own
only package-managed hook entries, preserve unrelated configuration, perform no
networking, and write through the existing private locked storage boundary.
Rollout parsing will be incremental and shape-tolerant, treat unknown records as
unsupported evidence, and never publish or retain prompt, response, reasoning,
tool-input, path, or identifier contents beyond the minimum opaque keys needed
for local attribution.

All Codex parser and lifecycle tests will use privacy-neutral synthetic JSONL
fixtures covering supported shapes, malformed rows, partial trailing records,
resume/session boundaries, duplicate observations, and unknown future records.
Live rollouts are research evidence only and never test fixtures.

## Consequences

The Claude Code display, installer, hooks, ledger arithmetic, and runtime
behavior remain unchanged in v0.4.0. This ADR authorizes architecture, not a
Codex adapter or configuration mutation.

Future work can proceed in small patches: introduce normalized acquisition
types while preserving Claude behavior; add a read-only Codex rollout parser
with synthetic evidence; then consider an opt-in hook collector and local query
surface. A Codex renderer integration remains blocked on an arbitrary-command
footer interface, and Codex currency accounting remains blocked on an exact
host-supplied cost contract.
