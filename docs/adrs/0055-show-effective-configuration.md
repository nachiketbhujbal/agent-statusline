# ADR 0055: Show effective configuration

- Status: Accepted
- Date: 2026-11-06
- Extends: [ADR 0052](0052-add-opt-in-toml-configuration-at-v0-5.md)

## Decision

Provide read-only `agent-statusline config show`. Report resolved settings
and the source of each value. An explicit TOML value is marked as TOML even
when it matches the built-in default. An environment override is marked with
the name of the variable.

Read the file once and use the existing validators and environment resolution.
Report absent or invalid TOML and reflect the normal fallback. If invalid
environment values disable the context guard, report that state with the
existing safe diagnostic. Report the source of a custom warning message
without printing its text.

The command inspects configuration only. `config check` remains the strict
file validation command.
