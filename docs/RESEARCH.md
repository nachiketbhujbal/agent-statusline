# Research

These findings are durable but not automatically scheduled work.

## Codex status-line boundary

Codex CLI 0.149.1 accepts a declarative list of fixed built-in widget
identifiers and rejects unknown values. It has no arbitrary-command status-line
surface, so the Claude renderer cannot be installed into Codex. The nearest
safe adaptation is an ordered native widget preset following the Claude row
priority: project, model/mode, context, usage, available cost, run state, then
tokens. Re-check this boundary after Codex upgrades.

An external ledger hook is not approved merely because Codex has hooks. First
establish, from an official contract or measured isolated payload, whether a
hook receives an exact session cost. Never derive currency from token counts.

## Self-hosted runner boundary

GitHub permits self-hosted runners on physical machines, virtual machines, and
containers. The `actions/runner-images` repository contains Packer definitions
for hosted VM images; it is not a registry of pullable Docker images. A Linux
ARM64 runner can run inside Docker Desktop on an Apple Silicon Mac using the
official runner application, but container jobs then require deliberate Docker
socket or Docker-in-Docker policy. Native macOS evidence requires a macOS runner
on the host rather than a Docker container.

For this small project, one repository-scoped runner per operating-system lane
is sufficient; parallel autoscaling infrastructure is not required. Registration,
host isolation, update policy, labels, and cleanup remain deployment decisions,
not package behavior.
