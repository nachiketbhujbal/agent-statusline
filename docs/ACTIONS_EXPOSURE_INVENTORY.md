# Historical Actions exposure inventory

This public-safe record inventories the GitHub Actions surface retained before
repository visibility can change. It records identifiers and categories, never
the private values that triggered a match.

## Method

At 2026-09-11T19:18:25Z, the authenticated GitHub API reported 41 workflow runs
and 26 unexpired artifacts. Every run-log archive was downloaded and every text
entry was scanned for the personal-provider email and private billing patterns
used by the repository policy. Every artifact was downloaded, recursively
opened through its outer artifact archive and inner wheel or source archive,
and checked for private paths, personal-provider email, private billing
evidence, and members above the two-MiB audit boundary.

The first pass found no matching run log. It found the superseded ADR 0018
billing phrase in the source distribution inside each artifact below:

| Artifact ID | Workflow run ID |
| --- | --- |
| `10182553023` | `34555947827` |
| `10184350659` | `34561155649` |
| `10184366510` | `34561213302` |
| `10185317588` | `34563964744` |
| `10185337583` | `34564023511` |
| `10185936009` | `34565747191` |
| `10185954867` | `34565803226` |
| `10186700274` | `34567959880` |
| `10186730316` | `34568055955` |
| `10187653749` | `34570718665` |
| `10187672444` | `34570771590` |
| `10188481916` | `34572971872` |
| `10188519132` | `34573060459` |
| `10190053406` | `34577055928` |
| `10190368422` | `34577894293` |
| `10190411583` | `34578002044` |

## Disposition and verification

The maintainer explicitly authorized deletion of exactly those 16 unsafe
Actions artifacts. All deletions succeeded. Workflow runs and their logs,
GitHub Releases and release assets, Git refs and tags, and the ten clean Actions
artifacts were left intact.

A complete post-deletion pass again downloaded all 41 retained log archives;
all were available and no match remained. It downloaded all ten remaining
artifacts; all were available and no private path, personal-provider email,
private billing evidence, or oversized member remained.

This inventory does not alter or expand the accepted twelve historical pull
refs in ADR 0035. Unreachable objects, provider caches, visibility, and
post-conversion repository protection remain separate boundaries.
