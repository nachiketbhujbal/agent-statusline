# ADR 0057: Preview a synthetic status line

- Status: Accepted
- Date: 2026-11-06
- Extends: [ADR 0052](0052-add-opt-in-toml-configuration-at-v0-5.md)

## Decision

Provide `agent-statusline config preview [--width CELLS]`. It renders a built-in
synthetic session with the ordinary status-line formatter and the effective
row, field, and color settings. A positive width overrides terminal detection.
Every displayed metric, process detail, and cost belongs to the sample.

The formatter accepts evidence providers for probes and accounting. Normal
rendering uses the existing live providers. The preview supplies only
synthetic facts, uses no transcript, and never invokes runtime collection or
reads or writes Claude settings or state.
