"""Deterministic hot-path import and non-gating benchmark evidence."""

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def isolated_env(tmp_path):
    home = tmp_path / "home"
    state = tmp_path / "state"
    home.mkdir(mode=0o700)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COV_CORE_") and key != "COVERAGE_PROCESS_START"
    }
    return dict(
        environment,
        HOME=str(home),
        CLAUDE_CONFIG_DIR=str(home / ".claude"),
        AGENT_STATUSLINE_STATE=str(state),
        COLUMNS="180",
    )


def test_renderer_import_excludes_cold_and_cli_modules(tmp_path):
    code = f"""
import sys
sys.path.insert(0, {str(ROOT / "src")!r})
import agent_statusline.statusline
print(','.join(name for name in ('argparse', 'subprocess', 'shutil') if name in sys.modules))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code],
        cwd=tmp_path,
        env=isolated_env(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.strip() == ""


def test_benchmark_command_reports_every_non_gating_boundary(tmp_path):
    clean_python = tmp_path / "clean-python"
    venv.EnvBuilder(with_pip=False).create(clean_python)
    completed = subprocess.run(
        [
            str(clean_python / "bin" / "python"),
            str(ROOT / "scripts" / "benchmark_renderer.py"),
            "--runs",
            "1",
            "--cold-runs",
            "1",
        ],
        cwd=tmp_path,
        env=isolated_env(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )

    assert "interpreter" in completed.stdout
    assert "import-only" in completed.stdout
    assert "warm-render" in completed.stdout
    assert "cold-render" in completed.stdout
    assert "warm/interpreter=" in completed.stdout
    assert "informational only; elapsed time is not a gate" in completed.stdout
