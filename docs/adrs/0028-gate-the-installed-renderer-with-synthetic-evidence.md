# ADR 0028: Gate the installed renderer with synthetic evidence

- Status: Accepted
- Date: 2026-09-11

## Context

The source test suite assembled a realistic payload in Python, but the
installed-package CI smoke passed an empty JSON object to the renderer. That
proved entry-point discovery without proving the approved ten-row display,
incremental transcript parsing, state writes, or the artifact users install.
Using a captured real payload or transcript would create an avoidable privacy
risk and make repeatability depend on one machine's paths, clocks, and state.

## Decision

Commit privacy-neutral payload and transcript templates under `tests/fixtures/`.
One shared materializer resolves transcript, project, and tool paths plus the
assistant and rate-limit reset clocks into a caller-owned temporary workspace.
Pytest and the installed-wheel smoke both consume its output and use one shared
verifier to require all ten row labels in declared `ORDER` plus transcript-
derived `CACHE`, `TOKENS`, `TOOLS`, and `TIMING` facts.

Tests redirect both `HOME` and `AGENT_STATUSLINE_STATE` before importing the
package. The hosted smoke likewise uses a disposable home and state directory,
installs the already-built wheel without dependencies, and renders from an
unrelated working directory. This keeps account probes, accounting state,
repository discovery, and transcript reads independent of the developer or
runner host.

The source distribution must carry the templates and materializer so its test
suite remains complete. The runtime wheel must exclude them. The existing
artifact verifier enforces both placement rules together with the repository's
privacy exclusions.

## Consequences

- Packaging smoke proves meaningful installed rendering rather than startup.
- Pytest and CI cannot silently drift to different payload or output contracts.
- No real session identifiers, filesystem paths, transcript content, or spend
  figures enter the repository.
- Runtime code and dependencies remain unchanged; all new machinery is test and
  workflow evidence.

## Evidence

Materializer regressions require absolute disposable paths, current transcript
evidence, realistic reset windows, and no unresolved placeholders. End-to-end
pytest requires the exact transcript-backed contract from an unrelated working
directory. Artifact-policy regressions reject a source archive missing the
evidence and a wheel containing it. The hosted smoke installs `dist/*.whl` and
runs the same materializer and verifier outside the checkout.
