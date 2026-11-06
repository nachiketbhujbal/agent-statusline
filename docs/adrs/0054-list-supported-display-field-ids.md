# ADR 0054: List supported display field IDs

- Status: Accepted
- Date: 2026-11-06
- Extends: [ADR 0053](0053-select-existing-display-field-groups.md)

## Decision

Provide `agent-statusline config fields [ROW]`. With no argument, print every
row in display order, followed by its stable field IDs and descriptions.
A canonical row ID narrows the result to that row. An unknown row or extra
argument is a usage error.

Validation and discovery share one catalog. The command lists what the
installed version supports without reading TOML, Claude settings, or runtime
state. Current field availability, effective settings, and configuration
validation remain separate.
