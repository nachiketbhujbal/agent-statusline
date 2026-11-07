#!/usr/bin/env python3
"""Measure paired installed renderers with disposable synthetic sessions."""

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from fixture_payload import materialize_payload  # noqa: E402


def report(label, samples):
    p95 = sorted(samples)[math.ceil(0.95 * len(samples)) - 1]
    print(
        f"{label:<16} median={statistics.median(samples):6.2f} ms "
        f"p95={p95:6.2f} ms n={len(samples)}"
    )


def measure(commands, root, timed):
    home = root / "home"
    home.mkdir(mode=0o700)
    payloads = []
    for index in range(6):
        payload = materialize_payload(root / f"session-{index}")
        payload["session_id"] = f"synthetic-benchmark-{index}"
        transcript = Path(payload["transcript_path"])
        fixture = transcript.read_bytes().splitlines(keepends=True)
        # Keep one conversation root and add a representative transcript tail.
        transcript.write_bytes(fixture[0] + b"".join(fixture[1:]) * 100)
        payloads.append(json.dumps(payload).encode())
    print(f"6 sessions, {transcript.stat().st_size} transcript bytes per session, 120 columns")
    base_env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(home),
        "CLAUDE_CONFIG_DIR": str(root / "claude"),
        "COLUMNS": "120",
    }
    for config in ("configured", "hidden"):
        path = root / config / "agent-statusline/config.toml"
        path.parent.mkdir(parents=True)
        text = "schema_version = 1\n"
        if config == "hidden":
            text += '[display.rows]\nCOST = "hide"\nCACHE = "hide"\n'
        path.write_text(text)

    def draw(number, index, state, config):
        env = dict(base_env, AGENT_STATUSLINE_STATE=str(state), XDG_CONFIG_HOME=str(root / config))
        start = time.perf_counter()
        result = subprocess.run(
            [commands[number]],
            input=payloads[index],
            cwd=root,
            env=env,
            capture_output=True,
            check=True,
            timeout=15,
        )
        if b"PROJECT" not in result.stdout or b"TIMING" not in result.stdout:
            raise RuntimeError("installed renderer did not produce the expected synthetic rows")
        return (time.perf_counter() - start) * 1000

    names = ["warm", "configured", "hidden", "cold", "six-redraws"]
    if timed:
        names += ["six-at-1s", "six-at-10s"]
    samples = [{name: [] for name in names} for _ in commands]
    with ThreadPoolExecutor(max_workers=6) as pool:

        def burst(number, state):
            start = time.perf_counter()
            list(pool.map(lambda index: draw(number, index, state, "missing"), range(6)))
            return (time.perf_counter() - start) * 1000

        for number in range(len(commands)):
            burst(number, root / f"warm-{number}")
        for repeat in range(40):
            # Alternate order to reduce shared machine-load and cache bias.
            for number in ((0, 1) if repeat % 2 == 0 else (1, 0)):
                state = root / f"warm-{number}"
                for name, config in (
                    ("warm", "missing"),
                    ("configured", "configured"),
                    ("hidden", "hidden"),
                ):
                    samples[number][name].append(draw(number, repeat % 6, state, config))
                if repeat < 12:
                    samples[number]["cold"].append(
                        draw(number, 0, root / f"cold-{number}-{repeat}", "missing")
                    )
                if repeat < 20:
                    samples[number]["six-redraws"].append(burst(number, state))
        if timed:
            for interval, count in ((1, 8), (10, 4)):
                deadline = time.monotonic()
                for repeat in range(count):
                    time.sleep(max(0.0, deadline - time.monotonic()))
                    for number in ((0, 1) if repeat % 2 == 0 else (1, 0)):
                        state = root / f"timed-{interval}-{number}"
                        elapsed = burst(number, state)
                        if repeat:  # first burst seeds each case
                            samples[number][f"six-at-{interval}s"].append(elapsed)
                    deadline += interval

    for name, command, observations in zip(
        ("baseline", "candidate"), commands, samples, strict=True
    ):
        version = subprocess.check_output(
            [command, "--version"],
            cwd=root,
            env=dict(base_env, AGENT_STATUSLINE_STATE=str(root / "version-state")),
            text=True,
            timeout=15,
        ).strip()
        print(f"{name} {version}")
        for case, values in observations.items():
            report(case, values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="installed baseline agent-statusline command")
    parser.add_argument("candidate", type=Path, help="installed candidate agent-statusline command")
    parser.add_argument(
        "--timed", action="store_true", help="also sample one- and ten-second cadence"
    )
    args = parser.parse_args()
    commands = [str(command.absolute()) for command in (args.baseline, args.candidate)]
    with tempfile.TemporaryDirectory(prefix="statusline-installed-bench-") as directory:
        measure(commands, Path(directory), args.timed)


if __name__ == "__main__":
    main()
