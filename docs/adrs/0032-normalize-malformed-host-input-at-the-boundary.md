# ADR 0032: Normalize malformed host input at the boundary

- Status: Accepted
- Date: 2026-08-29

## Context

The status line consumes JSON from a host process and incrementally reads JSONL
transcripts. Successful JSON decoding proves syntax, not shape or numeric
fitness. A valid array at the payload root or transcript row, a non-finite
number, an oversized integer, or an unexpected nested container could reach a
direct `.get()`, `int()`, `float()`, time conversion, or formatter and remove
the complete status line for that redraw.

The renderer must remain small, local-only, dependency-free, and compatible
with the valid numeric strings already accepted by the released tool. A broad
schema framework would add more machinery than this narrow boundary requires.

## Decision

Require the decoded payload root and every consumed transcript row to be a
mapping before field access. Unsupported top-level payload shapes use the
existing minimal fallback; unsupported transcript rows are ignored without
preventing later valid rows from contributing.

Fields passed to path, mapping-key, or sequence operations are also accepted
only in the narrow shape that operation requires. Unsupported transcript paths,
workspace paths, permission modes, added-directory lists, and session identifiers
fall back or are omitted rather than reaching filesystem or container APIs.
Transcript conversation identifiers and tool names likewise require non-empty
strings; unsupported values cannot poison incremental or accounting state, and
previously cached unsupported conversation roots are ignored.

Use a dependency-free `coerce.py` leaf module for bounded finite-number and
finite-integer conversion. The helpers reject booleans, invalid strings,
non-finite values, and values beyond the practical display bound while
preserving exact integers, fractional measurements, and the numeric-string
forms the prior implementation accepted. Formatter, transcript, and payload
boundaries use the helper appropriate to their domain.

Absence remains a domain decision, not a numeric default. In particular, an
absent payload cost remains `None` and is not converted into a real zero-cost
observation. Reset timestamps are also checked by the platform time conversion
before they are displayed.

This is targeted boundary normalization, not a complete host schema, runtime
dependency, telemetry path, or hostile-process defense.

## Consequences

Malformed but parseable host values degrade deterministically instead of
raising or emitting `nan`/`inf`. Later valid transcript rows still count, valid
formatting and fractional precision remain unchanged, and all ten row labels
and their order remain the display contract.

New host numeric fields must choose explicitly between finite fractional,
finite integral, and absent-value semantics. Tests cover accepted forms and
representative unsupported values at the helper, formatter, transcript, and
end-to-end payload boundaries.
