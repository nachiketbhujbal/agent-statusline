# ADR 0065: Make the cost estimate marker optional

Status: Accepted for v0.5.14. Supersedes the display-marker decision in
[ADR 0061](0061-label-host-cost-estimates.md).

Cost amounts are Claude Code's estimates, as documented in the field and
configuration guides. Show plain dollar amounts by default. A user can set
`show_cost_estimate_marker = true` in the existing TOML `[display]` table to
prefix each amount with `~` in the renderer and `ledger show`.

The `≥` prefix continues to identify an incomplete rolling window. With the
setting enabled it appears as `≥~$`. The calculation, ledger schema and
numeric metrics are independent of the display choice.

[Claude Code status line reference](https://code.claude.com/docs/en/statusline#available-data)
