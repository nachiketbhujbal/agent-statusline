# ADR 0061: Label host cost estimates

Status: Accepted for v0.5.10. Clarifies the source assumption in
[ADR 0001](0001-exactly-accountable-money.md) and the lower-bound semantics in
[ADR 0022](0022-account-rolling-costs-with-timestamped-deltas.md).

Claude Code describes `cost.total_cost_usd` as a client estimate based on list
prices or configured model pricing. The ledger can account for the values it
received. The provider determines actual billing independently.
[Claude Code status line reference](https://code.claude.com/docs/en/statusline#available-data)

Mark each currency amount in the renderer and human-readable ledger listing
with `~$`. Use `≥~$` for a rolling window with incomplete attribution. The
prefix applies to each value so a selected field or wrapped line retains its
meaning. The ledger schema, accumulation, coverage of rolling windows and
numeric session metrics API retain their existing semantics.
