"""Materialize and verify hermetic installed-renderer evidence."""

import argparse
import datetime
import json
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

FIXTURE_DIR = Path(__file__).parent / "fixtures"
PAYLOAD_TEMPLATE = FIXTURE_DIR / "statusline-payload.json"
TRANSCRIPT_TEMPLATE = FIXTURE_DIR / "statusline-transcript.jsonl"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TRANSCRIPT_EVIDENCE = {
    "CACHE": ("1h ttl", "writes 200 1h"),
    "TOKENS": ("total 2k reused", "200 written", "20 uncached"),
    "TOOLS": ("2 calls", "Read1", "Edit1"),
    "TIMING": ("turn 1s last", "hooks 1 runs", "12ms median"),
}


def _timestamp(now: float) -> str:
    return datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()


def _workspace_path(value: object, workspace: Path) -> Path:
    prefix = "__WORKSPACE__/"
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError(f"fixture path must start with {prefix!r}")
    relative = Path(value[len(prefix) :])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("fixture path must stay inside the materialized workspace")
    return workspace / relative


def materialize_payload(workspace: Path, now: Optional[float] = None) -> dict:
    """Resolve host-dependent template paths and clocks into ``workspace``."""
    current = time.time() if now is None else now
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    transcript = workspace / "statusline-transcript.jsonl"
    entries = []
    for line in TRANSCRIPT_TEMPLATE.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("type") == "assistant":
            entry["timestamp"] = _timestamp(current)
            for block in entry.get("message", {}).get("content", []):
                tool_input = block.get("input", {})
                if isinstance(tool_input, dict) and "file_path" in tool_input:
                    tool_input["file_path"] = str(
                        _workspace_path(tool_input["file_path"], workspace)
                    )
        entries.append(entry)
    transcript.write_text(
        "".join(json.dumps(entry, separators=(",", ":")) + "\n" for entry in entries),
        encoding="utf-8",
    )

    payload = json.loads(PAYLOAD_TEMPLATE.read_text(encoding="utf-8"))
    payload["transcript_path"] = str(transcript)
    payload["cwd"] = str(workspace)
    payload["workspace"] = {
        "current_dir": str(workspace),
        "project_dir": str(workspace),
        "added_dirs": [],
    }
    payload["rate_limits"]["five_hour"]["resets_at"] = current + 4 * 3600
    payload["rate_limits"]["seven_day"]["resets_at"] = current + 5 * 86400
    return payload


def rendered_rows(output: str) -> tuple[list[str], dict[str, str]]:
    """Return ordered labels and logical rows from ANSI-styled output."""
    labels = []
    rows = {}
    current = None
    for physical in (ANSI.sub("", line) for line in output.splitlines()):
        if not physical.strip():
            continue
        if not physical.startswith(" "):
            current, _, content = physical.partition(" ")
            labels.append(current)
            rows[current] = content.strip()
        elif current is not None:
            rows[current] += " " + physical.strip()
    return labels, rows


def verify_render_contract(output: str, order: Sequence[str]) -> None:
    """Require the exact row contract and evidence sourced from the transcript."""
    labels, rows = rendered_rows(output)
    expected = list(order)
    assert labels == expected, (labels, expected)
    for label, markers in TRANSCRIPT_EVIDENCE.items():
        for marker in markers:
            row = rows.get(label, "")
            assert marker in row, (label, marker, row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = materialize_payload(args.workspace)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
