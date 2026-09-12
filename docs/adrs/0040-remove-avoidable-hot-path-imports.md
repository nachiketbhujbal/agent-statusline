# ADR 0040: Remove avoidable hot-path imports and record non-gating benchmarks

- Status: Accepted
- Date: 2026-09-12

## Context

The status line is a fresh Python process on every redraw, so imports are a
large fraction of warm latency. A repeatable v0.3.0 baseline on the reference
ARM64 macOS machine found that a fresh renderer import loaded `argparse`,
`subprocess`, and `shutil` even though argument parsing and child processes are
needed only by colder paths. `shutil` also arrived transitively through
`tempfile`, which the locked storage service used only to create a same-directory
publication temporary.

Elapsed time varies materially with interpreter, environment, machine load, and
runner virtualization. A fixed millisecond threshold would turn useful evidence
into a flaky release gate.

## Decision

Import `argparse` only when the ledger CLI runs and `subprocess` only when a
probe cache miss executes a child. Preserve ordinary terminal-width behavior
with direct `COLUMNS` parsing, `os.get_terminal_size`, and the existing fallback
rather than importing `shutil`. Consistently treat a successful zero-column
terminal result as unusable and select that fallback on every supported Python
version. This deliberately replaces Python 3.9's old zero result with the safe
behavior already provided by newer Python versions.

Replace `tempfile.mkstemp` in the storage publication path with an equivalent
same-directory private file opened through `O_CREAT | O_EXCL`, a process and
random token, and a bounded collision retry. Continue to validate regular
entries, set mode 0600, flush and fsync, atomically replace the destination,
clean failed temporaries, and hold the existing transaction lock. This removes
the transitive `shutil` import without weakening state publication.

Gate the deterministic fact that a fresh renderer import does not load
`argparse`, `subprocess`, or `shutil`. Add a standard-library benchmark command
that uses private temporary home, configuration, state, and working directories
and reports interpreter, import-only, warm-render, cold-render, median, range,
and warm-to-interpreter ratio. Treat every timing as informational evidence;
do not fail CI based on elapsed time.

## Consequences

Warm renderer processes avoid modules used only by the ledger CLI, cold probes,
or generic temporary-file helpers. Probe misses, ledger commands, atomic state
publication, ordinary terminal-width selection, and every approved row and
field retain their behavior. The only output edge change is that an unusable
zero-column terminal result now selects the existing fallback consistently. The
new explicit temporary-name routine needs collision, failure-cleanup,
permission, atomicity, and concurrency coverage.

The benchmark can reveal regressions and machine differences without claiming
a cross-platform latency guarantee. A daemon, compiled rewrite, native helper,
or elapsed-time gate still requires separate evidence and a new decision.
