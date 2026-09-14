# ADR 0044: Keep the README as a product landing page

- Status: Accepted
- Date: 2026-09-13

## Context

The README is both the GitHub landing page and the long description rendered by
package indexes. It had grown to 368 lines and mixed the prospective user's
first-run path with an exhaustive documentation catalog, low-level installer
threat-model details, repository layout, release mechanics, and project history.
Important engineering records were visible, but the product and installation
story were harder to scan and several version-pinned instructions became stale.

The detailed material remains valuable to maintainers and contributors. The
problem is its placement in the primary public entry point, not its existence.

## Decision

Keep the README focused on the public user journey:

1. State what the tool is and show its complete ten-row output.
2. Put the recommended installation and first verification near the top.
3. Summarize the data shown, local privacy boundary, exact-money rule, managed
   installation behavior, common commands, and supported platforms.
4. Keep update, removal, and checkout-development instructions concise.
5. Link only the field reference and the smallest useful contributor entry
   points from the landing page.

Do not use the README as an exhaustive index of handoffs, review findings,
roadmaps, changelogs, research, deferred work, public-readiness evidence, or
individual architecture decisions. Those tracked sources remain available in
the repository and retain their existing authority.

Because the README is also package-index copy, package-name installation may be
staged on an unmerged release branch but must not reach `main` before the same
release is authorized to publish to production PyPI. The preferred command is
`uv tool install agent-statusline`; `pipx` and environment-scoped `pip` remain
documented standard alternatives.

## Consequences

The public landing page becomes shorter, easier to evaluate, and less likely to
lead with internal process or stale tag-specific commands. Detailed evidence is
still preserved and discoverable through the repository rather than deleted or
collapsed into untracked knowledge.

Some internal documents are no longer linked directly from the README. That is
intentional: contributor navigation stays small, while maintainers continue to
use the tracked handoff, roadmap, review ledger, ADR index, and Agent Relay
orientation as their authoritative paths.
