# ADR 0011: Treat row order as data, not as code

- Status: Accepted
- Date: 2026-08-26

## Context

Rows were emitted in the order `main()` happened to build them, so reordering
meant moving blocks of rendering code and risking their dependencies. Row order
is also the thing most likely to differ between people.

## Decision

`main()` builds rows into a dict keyed by name and emits them in the sequence
given by `ORDER`. Rows are ordered by how often they answer a question worth
asking, with `PROJECT` first. Rate limits sit on their own row rather than
beside the context bar, because context describes one conversation while the
limit windows are account-wide.

## Consequences

Reordering is a one-line edit. A row with nothing to say is simply absent from
the dict rather than rendering empty. Segment order within a row remains a
design decision, since the last segment is the first one a narrow terminal
loses.
