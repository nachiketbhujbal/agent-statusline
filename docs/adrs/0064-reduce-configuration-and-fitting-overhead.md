# ADR 0064: Reduce configuration and width-fitting overhead

Status: Accepted for v0.5.13. Extends
[ADR 0040](0040-remove-avoidable-hot-path-imports.md).

Each redraw starts a fresh Python process. Keep the immutable configuration
values in a standard-library named tuple. The renderer resolves the config
filename with the same XDG and home rules using `os.path`. Commands that
need a `Path` import it when requested. A present TOML file follows the
same bounded read, validation and fallback rules.

Sanitize untrusted text at the existing boundaries. When fitting a row,
reuse already sanitized segments and measure printable ASCII by length.
Unicode still uses the cell-width calculation. The deterministic import
test, control-sequence tests, and full renderer suite cover these boundaries.

Measure paired installed versions with isolated synthetic state. Include
configured and hidden views, cold transcripts, six concurrent sessions and
optional timed redraws. Record timings as evidence without enforcing a
wall-clock limit in CI.
