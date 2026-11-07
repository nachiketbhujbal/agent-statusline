# ADR 0060: Evolve one config with collection-independent views

- Status: Accepted direction; implementation follows the roadmap
- Date: 2026-11-07
- Extends: [ADR 0052](0052-add-opt-in-toml-configuration-at-v0-5.md),
  [ADR 0053](0053-select-existing-display-field-groups.md)
- Supersedes: indefinite deferral of layout customization in ADR 0052;
  its implemented schema-1 contract remains unchanged

## Decision

Keep one opinionated optional TOML location and no runtime profiles or alternate
config-path switches. Collect and calculate independently from visibility;
display choices never opt out of accounting or observation. Retain the default
ten-row display, existing group IDs and environment precedence.

Use schema 2 for finer display elements in 0.6.0, while accepting unchanged
schema-1 files. Keep row `show`/`hide` and group lists; add separate typed element
controls from a product-owned catalog. New host fields are opt-in. No renderer
automatically migrates or writes a file. Implement the first interactive editor
in 0.6.1 using shared validation and synthetic preview, explicit save, lossless
bounded TOML edits, private atomic writes and concurrent-edit refusal.

Add presentation and conditional controls as focused compatible follow-ups.
Introduce optional layouts as a separate 0.7 milestone, retaining the approved
default. Broader host acquisition remains independent of a host's rendering
capability and cannot invent currency or fill one session from another.

Use host-supported refresh scheduling before considering a daemon. Timed
redraws preserve probe TTLs, accounting idempotence and honest source freshness.
Measure performance under equivalent work rather than using language choice
as a speed or quality claim. Editor code never enters the renderer's import path.

## Consequences

[CUSTOMIZATION_DESIGN.md](../CUSTOMIZATION_DESIGN.md) specifies the proposed
element syntax, visibility precedence, editor behavior, refresh boundaries and
acceptance evidence. It explicitly separates planned from installed features.
[ROADMAP.md](../ROADMAP.md#next-release-and-milestones) assigns single-purpose
slices; defect fixes may consume any next patch number and shift later slots.
Exact formatting keys and new host field IDs require slice-specific decisions
before implementation. v0.5.9 records this plan but implements only the release
verification correction, not schema 2 or the editor.
