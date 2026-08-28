# Changelog

This project follows semantic versioning. Versions come from immutable Git tags.

## Unreleased — 0.2.1

- Preserve unrelated Claude Code hooks and fail closed on malformed settings.
- Respect the selected Claude configuration directory in checkout installs.
- Remove only package-owned settings and symlinks during uninstall.

The larger hardening branch is an integration source, not one release.
`ROADMAP.md` assigns its remaining work to subsequent small `0.2.x` releases;
each section will move here only when that release branch is prepared.

## 0.2.0

- Package the status line as an installable Python tool while retaining the
  checkout development path.
- Introduce numbered ADRs and the current ten-row, width-aware renderer.
