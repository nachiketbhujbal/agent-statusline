# ADR 0053: Select existing display field groups

- Status: Accepted
- Date: 2026-11-06
- Extends: [ADR 0052](0052-add-opt-in-toml-configuration-at-v0-5.md)

## Decision

Add the optional `[display.fields]` table to schema 1. Each key is a
canonical row ID and each value is a nonempty list of that row's stable field
group IDs. The [field reference](../FIELDS.md#configurable-field-groups)
defines those IDs at the existing renderer segment boundaries.

Omit a list to retain all groups for its row. Reject duplicate or unknown
IDs through the existing file validation. A hidden row stays hidden.
Apply selection before width fitting, preserve existing row and field
priority, and omit groups without displayable evidence. If none of the
selected groups is available, omit the row.

## Consequences

The default display, probes, warning behavior, state, cost accounting,
and environment precedence keep their existing behavior. Existing TOML
files require no changes. v0.5.0 rejects files using the new table, so remove
that table if downgrading. Discovery and other configuration commands follow
in separate patches.
