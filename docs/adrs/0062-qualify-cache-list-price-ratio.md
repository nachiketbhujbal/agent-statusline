# ADR 0062: Qualify the cache list-price ratio

Status: Accepted for v0.5.11.

Compute the unit-free input ratio from transcript evidence for a single
explicitly supported Claude model. Use published read weights and separate
write weights for the two TTL buckets. Confirm that each request's write
buckets reconcile with its write count. If the model or split is missing,
inconsistent or mixed across models, omit the ratio. This avoids guessing
a cost weighting for input from different models. Native cache warmth and
expiry keep their separate source.

Version 5 of the transcript cache replays original transcript evidence for
the new fields. The ratio describes published list-price input economics.
Actual billing, custom model pricing and output costs are outside that ratio.
The cost ledger uses the host values independently.

[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
