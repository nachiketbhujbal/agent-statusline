#!/usr/bin/env python3
"""Report isolated renderer timings without turning wall time into a gate."""

import argparse
import os
import statistics
import subprocess
import sys
import tempfile
import time

PAYLOAD = b"{}\n"


def _positive(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _elapsed(command, root, env=None, payload=None):
    started = time.perf_counter_ns()
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        input=payload,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"benchmark child exited {completed.returncode}")
    return (time.perf_counter_ns() - started) / 1_000_000


def _report(name, samples):
    print(
        f"{name:<12} median={statistics.median(samples):8.3f} ms  "
        f"range={min(samples):8.3f}..{max(samples):8.3f} ms  n={len(samples)}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=_positive, default=40)
    parser.add_argument("--cold-runs", type=_positive, default=12)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="agent-statusline-benchmark-") as root:
        home = os.path.join(root, "home")
        os.mkdir(home, 0o700)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("COV_CORE_") and key != "COVERAGE_PROCESS_START"
        }
        env = dict(
            environment,
            HOME=home,
            CLAUDE_CONFIG_DIR=os.path.join(home, ".claude"),
            AGENT_STATUSLINE_STATE=os.path.join(root, "warm-state"),
            COLUMNS="180",
        )
        isolated = [sys.executable, "-I"]
        render = [*isolated, "-m", "agent_statusline"]

        interpreter = [_elapsed([*isolated, "-c", "pass"], root) for _ in range(args.runs)]
        imports = [
            _elapsed([*isolated, "-c", "import agent_statusline.statusline"], root)
            for _ in range(args.runs)
        ]

        _elapsed(render, root, env=env, payload=PAYLOAD)
        warm = [_elapsed(render, root, env=env, payload=PAYLOAD) for _ in range(args.runs)]

        cold = []
        for index in range(args.cold_runs):
            cold_env = dict(
                env,
                AGENT_STATUSLINE_STATE=os.path.join(root, f"cold-state-{index}"),
            )
            cold.append(_elapsed(render, root, env=cold_env, payload=PAYLOAD))

    _report("interpreter", interpreter)
    _report("import-only", imports)
    _report("warm-render", warm)
    _report("cold-render", cold)
    print(f"warm/interpreter={statistics.median(warm) / statistics.median(interpreter):.3f}x")
    print("informational only; elapsed time is not a gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
