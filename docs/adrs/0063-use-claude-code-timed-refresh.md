# ADR 0063: Use Claude Code timed refresh

Status: Accepted for v0.5.12.

Claude Code 2.1.97 introduced the optional `statusLine.refreshInterval`
setting. Let the host schedule the existing renderer. The installer sets
the interval only after an explicit `--refresh-interval SECONDS` and a
successful supported-version check. `--event-only` removes it. Ordinary
install preserves any previous interval in an owned entry. Dry runs preview
the selection without writing it. The allowed range is 1 to 2,147,483 seconds
so milliseconds fit a signed 32-bit timer.

The package TOML controls the display. The Claude setting controls when the
host invokes the renderer. Repeat redraws reuse incremental transcript and
probe caches. Each redraw can include other sessions' new ledger entries and
preserves its own transcript and cost evidence. Host facts advance when the
host provides newer evidence.

[Claude Code 2.1.97 changelog](https://code.claude.com/docs/en/changelog#2-1-97) ·
[Status line update events](https://code.claude.com/docs/en/statusline#when-the-status-line-updates)
