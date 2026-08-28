"""Materialize hermetic renderer evidence from committed synthetic templates."""

import argparse
import datetime
import json
import time
from pathlib import Path
from typing import Optional

FIXTURE_DIR = Path(__file__).parent / "fixtures"
PAYLOAD_TEMPLATE = FIXTURE_DIR / "statusline-payload.json"
TRANSCRIPT_TEMPLATE = FIXTURE_DIR / "statusline-transcript.jsonl"


def _timestamp(now: float) -> str:
    return datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()


def materialize_payload(workspace: Path, now: Optional[float] = None) -> dict:
    """Resolve host-dependent paths and clocks into a disposable workspace."""
    current = time.time() if now is None else now
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    transcript = workspace / "statusline-transcript.jsonl"
    entries = []
    for line in TRANSCRIPT_TEMPLATE.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("type") == "assistant":
            entry["timestamp"] = _timestamp(current)
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = materialize_payload(args.workspace)
    args.output.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
