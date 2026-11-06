# ADR 0052: Add opt-in TOML configuration at v0.5

- Status: Accepted; implemented in v0.5.0

## Release boundary

Keep Python 3.9 support and zero runtime dependencies throughout 0.4.x.
No 0.4.x patch is required for configuration. Any independent fix on that
line must remain compatible. Introduce TOML and the Python 3.11 minimum
together in 0.5.0, using standard-library `tomllib`. Do not bundle a parser,
add a runtime dependency, or backport the TOML contract.

## Configuration contract

Read one optional UTF-8 file per invocation:
`$XDG_CONFIG_HOME/agent-statusline/config.toml` when `XDG_CONFIG_HOME` is
absolute, otherwise `~/.config/agent-statusline/config.toml`. The path is
independent of Claude settings and the state directory. Do not discover
workspace configuration or create, edit, or delete the file automatically.
Require integer `schema_version = 1` when a file exists; all other keys
are optional.

```toml
schema_version = 1

[context_guard]
warn_pct = 80
warn_event = "stop"
# Omit warn_message for the built-in warning.
# warn_message = "Context is at {pct}%."

[session_metrics]
enabled = true

[display]
color = "default" # "plain" removes styling, retaining content

[display.rows]
PROJECT = "show"
MODEL   = "show"
CONTEXT = "show"
USAGE   = "show"
COST    = "show"
SYSTEM  = "show"
TOOLS   = "show"
CACHE   = "show"
TOKENS  = "show"
TIMING  = "show"
```

- Resolve built-in defaults, then file values, then existing environment
  overrides per setting. Preserve parsing and behavior for
  `AGENT_STATUSLINE_CONTEXT_WARN_PCT`, `AGENT_STATUSLINE_CONTEXT_WARN_EVENT`,
  `AGENT_STATUSLINE_CONTEXT_WARN_MESSAGE` and
  `AGENT_STATUSLINE_SESSION_METRICS`. Add no new display environment switches.
- Validate a finite numeric threshold from 1 through 100, an event of
  `stop`, `submit` or `both`, and a nonempty custom message containing
  literal `{pct}`. Metrics enablement is a boolean; disabling it suppresses
  new snapshot publication without deleting existing snapshots.
- Accept case-sensitive canonical row IDs and only `show` or `hide`.
  Omitted rows follow existing evidence and width rules. Filter presentation
  after collecting facts. Hiding `COST` does not change the ledger, and
  hiding every row yields empty status-line output without stopping normal
  collection, hooks, snapshot publication or accounting.
- Accept `default` or `plain` for color. Plain removes styling while retaining
  text, Unicode symbols, canonical order, field priorities and width fitting.
  No file and the same environment produce the same output as before.
- Bound the file to 64 KiB. Missing is normal. An unreadable, oversized or
  invalid file, unsupported schema, or unknown key invalidates the entire
  file. Rendering and hooks proceed as if it were absent, preserving the
  existing behavior of environment overrides.
- `agent-statusline config check` validates only the file. It reports the
  missing-file default case and exits successfully; invalid input exits
  nonzero with the setting or location and reason, without echoing values
  or file contents. It does not render, run hooks, or access the live ledger,
  Claude settings or runtime state.

## Future field visibility

Keep row values as strings within schema 1. A later additive slice could
introduce a separate `[display.fields]` table with entries such as
`PROJECT = ["branch", "session_name"]`. Those IDs are illustrative until
the existing display groups have been inventoried, documented and approved.

Each list would allow only stable field group IDs for its row. An omitted
list retains every existing field; empty lists (use row `"hide"` instead),
duplicates and unknown IDs are invalid. A hidden row wins over any field
list. Preserve the existing field priority order regardless of list order
and continue omitting unavailable evidence. Selectors affect presentation
only, with no changes to probes, metrics, storage or currency semantics.

0.5.0 rejects `display.fields` as unknown. Later support can be added
without migrating existing files; no version is assigned. Profiles,
custom themes, templates and layout reordering remain outside this design.

## Acceptance for implementation

Align package metadata, typing, CI, publication verification and install
guidance with the Python 3.11 minimum. Verify the installed artifacts and
the upgrade path from 0.4.x. With disposable home, state and Claude settings,
prove default-output parity, precedence, invalid-file fallback, read-only
validation, unchanged collection with hidden rows, all-hidden output and
terminal-cell fitting in default and plain modes. Preserve installer ownership
and the ledger format.
