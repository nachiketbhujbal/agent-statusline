# ADR 0028: Gate the installed renderer with synthetic evidence

- Status: Accepted
- Date: 2026-08-28

## Context

The test suite exercised a realistic payload assembled in Python, but the
installed-package CI smoke passed an empty JSON object to the renderer. That
proved entry-point discovery without proving the approved ten-row display,
incremental transcript parsing, state writes, or packaged end-to-end behavior.
Using a captured real payload or transcript would create an avoidable privacy
risk and make repeatability depend on one machine's state.

## Decision

Commit a privacy-neutral payload and transcript pair under `tests/fixtures/`.
The fixture uses generic synthetic identifiers, paths, costs, tokens, tools,
and timings while exercising every approved row. Use the same fixture as the
default end-to-end pytest payload and in the installed-package smoke. Require
the smoke to find all ten row labels in their approved order set.

The fixture remains static evidence. Tests redirect `AGENT_STATUSLINE_STATE`
before importing the package, and hosted smoke runs set it to a disposable
runner directory, so neither path can read or mutate live accounting state.

## Consequences

- Packaging smoke now proves meaningful rendering rather than only process
  startup.
- Test and CI payload shape cannot silently drift because they share one
  committed source.
- No real session identifiers, filesystem paths, transcript content, or spend
  figures enter the repository.
- Host schema changes that remove an approved field become visible in one
  synthetic fixture that is straightforward to review.

## Evidence

`test_committed_fixture_exercises_every_approved_row` requires the exact
`ORDER` sequence, and the installed-shape workflow checks every row label after
installing the package from the checkout.
