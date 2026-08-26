# Deferred ideas

Considered and consciously not built. These are not decisions — see
[adr/](adrs/README.md) for those — and none of them is blocked on effort alone.

## Overage spend, derived from the cost at the crossing point

Usage credits are charged at API rates, so in principle
`overage spend = cost now − cost when used_percentage crossed 100%`.

Four things must be resolved first:

1. **The crossing must be captured exactly.** It is only observable if a render
   happens at that moment. `rate-limit-history.jsonl` records changes but stores
   no cost alongside the reading; adding that is the concrete prerequisite.
2. **Overage is account-wide, a session is not.** Another session, or another
   machine, spends the same credits. One session's delta is a floor, not a total.
3. **The two numbers' scopes do not obviously match.** The web dashboard's
   total and a single session's `total_cost_usd` were observed to disagree by
   roughly a factor of two, and it is not established what each one counts.
4. **It would still be a derived dollar figure**, which
   [ADR 0001](adrs/0001-exactly-accountable-money.md) exists to prevent.

If ever built, it must be labelled an estimate with its anchor timestamp
visible, and must never be presented as a credit balance.

## Smaller ideas

- `+2% over · pinned 12m` — how long the rate-limit figure has been frozen,
  read from `rate-limit-history.jsonl`. Factual and cheap, and it would help
  settle the open question in [ADR 0009](adrs/0009-suppress-derived-rate-limit-figures-in-overage.md).
- Surfacing `server_tool_use` web search and fetch counts on the `TOOLS` row.
- Model mix and per-tool latency.
- **Files touched through Bash**, which are currently invisible: only
  `Edit`, `Write`, `NotebookEdit` and `Read` register, so a session that changed
  plenty can read `0 files edited`.
- Compaction verification, once a real compaction actually occurs.
