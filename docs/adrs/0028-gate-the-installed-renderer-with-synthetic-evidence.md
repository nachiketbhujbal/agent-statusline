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

Commit privacy-neutral payload and transcript templates under `tests/fixtures/`.
One shared materializer resolves the transcript, project directory, assistant
timestamp, and rate-limit reset clocks into a caller-owned temporary workspace.
Pytest and the installed-package smoke must both consume its output and require
all ten row labels in the declared `ORDER` sequence.

Tests redirect both `HOME` and `AGENT_STATUSLINE_STATE` before importing the
package. The hosted smoke likewise renders with a disposable home and state
directory. This prevents account probes, accounting state, repository
discovery, and transcript reads from depending on a developer or runner host.

## Consequences

- Packaging smoke now proves meaningful rendering rather than only process
  startup.
- Test and CI payload shape and materialization cannot silently drift because
  they share one committed source and one resolver.
- No real session identifiers, filesystem paths, transcript content, or spend
  figures enter the repository.
- Host schema changes that remove an approved field become visible in one
  synthetic fixture that is straightforward to review.

## Evidence

Materializer regressions require absolute disposable paths, current transcript
evidence, and realistic reset windows. The end-to-end pytest requires the exact
`ORDER` sequence from an unrelated working directory, and the installed-shape
workflow imports that same sequence after installing the package.
