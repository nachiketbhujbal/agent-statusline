# Changelog

This project follows semantic versioning. Versions come from immutable Git tags.

## Unreleased — 0.3.0

- Preserve unrelated Claude Code hooks and fail closed on malformed settings.
- Serialize and atomically publish private runtime state.
- Preserve the 24h, 7d, and 30d cost fields while replacing lifetime-row
  attribution with timestamped deltas, seed-aware migration, and exact
  lower-bound markers.
- Establish a locked uv, pre-commit, lint, format, typing, coverage, and build
  gate.
- Isolate each concurrent session's process metrics and bound retained probe
  cache state.
- Bound transcript and rate-limit observation state without adding a full-file
  scan to normal redraws.

## 0.2.0

- Package the status line as an installable Python tool while retaining the
  checkout development path.
- Introduce numbered ADRs and the current ten-row, width-aware renderer.
