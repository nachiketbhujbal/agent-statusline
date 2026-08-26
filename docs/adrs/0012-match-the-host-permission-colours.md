# ADR 0012: Match the host's own permission-mode colours

- Status: Accepted
- Date: 2026-08-26

## Context

The status line shows the permission mode, and so does Claude Code's own
indicator under the prompt. Inventing a second colour scheme would make the same
fact look like two different facts.

## Decision

Take the mode-to-colour mapping from Claude Code itself and keep it in `MODES`:
`default` grey, `plan` cyan, `acceptEdits` magenta, `auto` yellow, and
`bypassPermissions` and `dontAsk` red. Show the mode in both places
deliberately.

## Consequences

The mapping is version-specific and was read out of the shipped binary; it
should be re-checked after a Claude Code upgrade rather than assumed to hold.
Duplication with the host indicator is intentional, because the status line is
where session state is looked for.
