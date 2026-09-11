import subprocess
import sys
from pathlib import Path

import pytest

VERIFY_DOCS = Path(__file__).parents[1] / "scripts" / "verify_docs.py"
REPOSITORY_ROOT = VERIFY_DOCS.parents[1]


def run_policy(root):
    return subprocess.run(
        [sys.executable, str(VERIFY_DOCS), str(root)],
        capture_output=True,
        text=True,
    )


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def valid_repository(tmp_path):
    write(
        tmp_path / "AGENTS.md",
        """# Instructions

Each release has exactly one branch owner. At most one independent reviewer may be active
at a time. The reviewer does not commit to or check out the owner's worktree. The owner
applies corrections. A correction requires a renewed exact-SHA review.
""",
    )
    write(
        tmp_path / "HANDOFF.md",
        """# Handoff

- Current release target: 0.2.8, governance.
- Preceding release: v0.2.7, immutable base.
- Branch owner: Codex
- Reviewer role: one independent reviewer
""",
    )
    write(
        tmp_path / "docs" / "ROADMAP.md",
        """# Roadmap

| Release | Purpose | Status |
| --- | --- | --- |
| 0.2.7 | Prior | **Released** |
| 0.2.8 | Governance | **Current** |
""",
    )
    write(
        tmp_path / "docs" / "CHANGELOG.md",
        """# Changelog

## Unreleased — 0.2.8

Governance.

## 0.2.7

Prior release.
""",
    )
    write(
        tmp_path / "docs" / "CODE_REVIEW.md",
        """# Review

| ID | Severity | Finding | Release | Status |
| --- | --- | --- | --- | --- |
| GOV-001 | Medium | Missing records. | 0.2.8 | Resolved |
""",
    )
    write(tmp_path / "docs" / "RESEARCH.md", "# Research\n\nDated evidence only.\n")

    index_rows = []
    for number in range(1, 27):
        adr_id = f"{number:04d}"
        filename = f"{adr_id}-decision.md"
        if number == 26:
            filename = "0026-coordinate-one-owner-and-one-reviewer.md"
            body = """# ADR 0026

Each release has exactly one branch owner and one independent reviewer. The owner alone
changes the release branch and applies corrections. At most one independent reviewer is
active at a time. The reviewer does not further delegate. A correction requires a renewed
exact-SHA review.
"""
        else:
            body = f"# ADR {adr_id}\n"
        write(tmp_path / "docs" / "adrs" / filename, body)
        index_rows.append(f"| [{adr_id}]({filename}) | Decision |")
    write(
        tmp_path / "docs" / "adrs" / "README.md",
        "# ADR index\n\n| ADR | Decision |\n| --- | --- |\n" + "\n".join(index_rows) + "\n",
    )
    return tmp_path


def test_documentation_policy_accepts_consistent_public_records(tmp_path):
    root = valid_repository(tmp_path)

    result = run_policy(root)

    assert result.returncode == 0, result.stderr


def test_repository_documentation_is_consistent():
    result = run_policy(REPOSITORY_ROOT)

    assert result.returncode == 0, result.stderr


def test_documentation_policy_rejects_broken_relative_link(tmp_path):
    root = valid_repository(tmp_path)
    write(root / "README.md", "[missing](docs/missing.md)\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing relative link target" in result.stderr


def test_documentation_policy_rejects_broken_reference_style_link(tmp_path):
    root = valid_repository(tmp_path)
    write(root / "README.md", "[missing][target]\n\n[target]: docs/missing.md\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing relative link target: docs/missing.md" in result.stderr


def test_documentation_policy_rejects_unindexed_adr(tmp_path):
    root = valid_repository(tmp_path)
    write(root / "docs" / "adrs" / "0027-new-decision.md", "# ADR 0027\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert "ADR 0027 is not indexed" in result.stderr


def test_documentation_policy_rejects_release_version_drift(tmp_path):
    root = valid_repository(tmp_path)
    changelog = root / "docs" / "CHANGELOG.md"
    write(changelog, changelog.read_text(encoding="utf-8").replace("0.2.8", "0.2.9", 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert "Unreleased version must be current release 0.2.8" in result.stderr


def test_documentation_policy_rejects_parallel_review_wording(tmp_path):
    root = valid_repository(tmp_path)
    agents = root / "AGENTS.md"
    write(
        agents,
        agents.read_text(encoding="utf-8").replace(
            "At most one independent reviewer may be active\nat a time.",
            "Several independent reviewers may be active.",
        ),
    )

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing review rule" in result.stderr


@pytest.mark.parametrize(
    ("evidence", "description"),
    [
        ("Evidence: /Users/example/private", "machine home path"),
        ("Evidence: .pvt/private-notes", "private workspace path"),
        ("Evidence: agent-relay/project", "private coordination path"),
        ("session_id = abcdefgh", "concrete session identifier"),
        ("Evidence: 123e4567-e89b-42d3-a456-426614174000", "UUID-shaped private identifier"),
        ("account allowance: 51000", "account value"),
        ("User prompt: private text", "prompt transcript"),
    ],
)
def test_documentation_policy_rejects_private_governance_evidence(tmp_path, evidence, description):
    root = valid_repository(tmp_path)
    handoff = root / "HANDOFF.md"
    write(handoff, handoff.read_text(encoding="utf-8") + f"\n{evidence}\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert description in result.stderr
