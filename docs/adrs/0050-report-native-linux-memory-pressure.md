# ADR 0050: Report native Linux and WSL memory pressure

- Status: Accepted
- Date: 2026-09-15

## Context

The product supports macOS and Linux, but its whole-system memory probe used
only macOS `sysctl` and `vm_stat`. Linux therefore retained process RSS and
filesystem pressure on the `SYSTEM` row while omitting total RAM, Claude's RAM
share, and the RAM pressure bar. This was graceful degradation rather than a
rendering failure, but it left the supported Linux display incomplete.

Linux exposes an authoritative kernel view in `/proc/meminfo`. `MemFree` alone
is not a useful pressure measure because reclaimable caches are intentionally
used for performance; `MemAvailable` estimates memory available for new work
without swapping. Under WSL these values describe the Linux environment's
assigned capacity, which is the relevant boundary for processes running there.

## Decision

Dispatch the dependency-free memory probe by runtime platform. Preserve the
existing macOS calculation from total capacity plus active, wired, and
compressed pages. On Linux, read `/proc/meminfo`, require valid non-negative
`MemTotal` and `MemAvailable` values in kernel-reported kibibytes, and calculate
used pressure as `MemTotal - MemAvailable`, bounded to the reported capacity.

Normalize both paths to the existing `total`, `used`, and `pct` fields so the
renderer and approved ten-row display remain unchanged. Keep the `compressed`
segment macOS-only. Missing or malformed required evidence retains the existing
graceful omission rather than inventing a percentage. Certify both native paths
in hosted CI and cover parsing and degradation with synthetic tests.

## Consequences

Linux and WSL users receive the RAM bar, total capacity, and Claude-process RAM
share already shown on macOS. WSL reports pressure against the capacity visible
to its Linux environment, not total Windows-host RAM. Percentages remain useful
host-native pressure signals rather than claims that macOS and Linux classify
every memory page identically. No dependency, network access, state format,
installer behavior, cost accounting, or display field changes.
