# ADR 0056: Print starter TOML

- Status: Accepted
- Date: 2026-11-06
- Extends: [ADR 0052](0052-add-opt-in-toml-configuration-at-v0-5.md)

## Decision

Provide `agent-statusline config example`. Print schema 1 with commented
examples of display, row visibility, field visibility, context warnings, and
session metrics. The printed document passes `config check` as-is. Saving
it with the examples still commented preserves the defaults.

The command prints to standard output. It does not open the user's
configuration, create files, or inspect Claude settings or runtime state.
