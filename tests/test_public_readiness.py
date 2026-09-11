import subprocess
import sys
from pathlib import Path

VERIFY = Path(__file__).parents[1] / "scripts" / "verify_public_readiness.py"
PIN = "a" * 40
NO_REPLY = "17068914+nachiketbhujbal@users.noreply.github.com"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def valid_repository(tmp_path):
    write(tmp_path / ".gitignore", "/.claude/\n/.pvt/\n/.worktrees/\n")
    write(
        tmp_path / ".github" / "workflows" / "ci.yml",
        f"""name: CI
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
    inputs:
      hosted_macos:
        type: boolean
permissions:
  contents: read
jobs:
  checks:
    outputs:
      full: ${{{{ steps.scope.outputs.full }}}}
    steps:
      - uses: actions/checkout@{PIN} # v7.0.1
        with:
          fetch-depth: 0
      - run: python scripts/audit_reachable_history.py --ref HEAD
      - id: scope
        run: git diff --quiet "${{BASE_SHA}}" HEAD -- .
  test:
    needs: checks
    if: needs.checks.outputs.full == 'true'
  macos:
    if: github.event_name == 'workflow_dispatch' && inputs.hosted_macos
""",
    )
    write(
        tmp_path / ".github" / "workflows" / "release.yml",
        f"""name: Release
on:
  push:
    tags: ["v*"]
permissions:
  contents: write
jobs:
  release:
    steps:
      - uses: actions/checkout@{PIN} # v7
        with:
          fetch-depth: 0
      - run: python scripts/audit_reachable_history.py --ref HEAD
""",
    )
    write(
        tmp_path / "docs" / "adrs" / "0018-budget-hosted-ci.md",
        "# ADR 0018\n\nExact account measurements remain private.\n",
    )
    return tmp_path


def run_policy(root, *args):
    return subprocess.run(
        [sys.executable, str(VERIFY), *args, str(root)],
        capture_output=True,
        text=True,
    )


def git(root, *args):
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def commit_repository(root, email=NO_REPLY):
    git(root, "init")
    git(root, "config", "user.name", "Release Maintainer")
    git(root, "config", "user.email", email)
    git(root, "add", ".")
    git(root, "commit", "-m", "candidate")


def test_public_readiness_policy_accepts_static_boundaries(tmp_path):
    result = run_policy(valid_repository(tmp_path))

    assert result.returncode == 0, result.stderr


def test_public_readiness_policy_rejects_moving_action_tag(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text().replace(f"@{PIN}", "@v7", 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert "not pinned to a full SHA" in result.stderr


def test_public_readiness_policy_rejects_missing_version_comment(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text().replace(" # v7.0.1", "", 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert "lacks a readable version comment" in result.stderr


def test_public_readiness_policy_rejects_missing_private_boundary(tmp_path):
    root = valid_repository(tmp_path)
    write(root / ".gitignore", "/.claude/\n/.worktrees/\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing root private boundary /.pvt/" in result.stderr


def test_public_readiness_policy_rejects_undefined_dependency_prefix(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text() + "\nrun: RENDER_HOME=/tmp python -c pass\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert "undefined RENDER_HOME prefix" in result.stderr


def test_public_readiness_policy_rejects_exact_private_billing(tmp_path):
    root = valid_repository(tmp_path)
    private_measurement = "The run used " + "12.5 percent" + " of the allowance.\n"
    write(
        root / "docs" / "adrs" / "0018-budget-hosted-ci.md",
        "# ADR 0018\n\n" + private_measurement,
    )

    result = run_policy(root)

    assert result.returncode == 1
    assert "exact private billing data" in result.stderr


def test_public_readiness_policy_rejects_path_skipped_ancestry_audit(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text() + '\npaths-ignore: ["docs/**"]\n')

    result = run_policy(root)

    assert result.returncode == 1
    assert "ancestry audit must not skip documentation-only refs" in result.stderr


def test_public_readiness_policy_requires_ci_ancestry_audit(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(
        workflow,
        workflow.read_text().replace(
            "python scripts/audit_reachable_history.py --ref HEAD", "python -c pass", 1
        ),
    )

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing lean-policy fragment" in result.stderr


def test_public_readiness_policy_requires_release_ancestry_audit(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "release.yml"
    write(
        workflow,
        workflow.read_text().replace(
            "python scripts/audit_reachable_history.py --ref HEAD", "python -c pass"
        ),
    )

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing release-policy fragment" in result.stderr


def test_public_readiness_policy_accepts_release_commit_no_reply_identity(tmp_path):
    root = valid_repository(tmp_path)
    commit_repository(root)

    result = run_policy(root, "--release-commit", "HEAD")

    assert result.returncode == 0, result.stderr
    assert "release commit identity" in result.stdout


def test_public_readiness_policy_rejects_release_commit_personal_identity(tmp_path):
    root = valid_repository(tmp_path)
    commit_repository(root, "maintainer@example.com")

    result = run_policy(root, "--release-commit", "HEAD")

    assert result.returncode == 1
    assert "does not use the maintainer no-reply author" in result.stderr


def test_public_readiness_policy_accepts_annotated_release_tag_no_reply_identity(tmp_path):
    root = valid_repository(tmp_path)
    commit_repository(root)
    git(root, "tag", "-a", "v0.2.12", "-m", "release")

    result = run_policy(root, "--release-tag", "v0.2.12")

    assert result.returncode == 0, result.stderr
    assert "annotated release identity" in result.stdout


def test_public_readiness_policy_rejects_lightweight_release_tag(tmp_path):
    root = valid_repository(tmp_path)
    commit_repository(root)
    git(root, "tag", "v0.2.12")

    result = run_policy(root, "--release-tag", "v0.2.12")

    assert result.returncode == 1
    assert "is not an annotated tag" in result.stderr


def test_public_readiness_policy_rejects_personal_release_tagger(tmp_path):
    root = valid_repository(tmp_path)
    commit_repository(root)
    git(root, "config", "user.email", "maintainer@example.com")
    git(root, "tag", "-a", "v0.2.12", "-m", "release")

    result = run_policy(root, "--release-tag", "v0.2.12")

    assert result.returncode == 1
    assert "does not use the maintainer no-reply tagger" in result.stderr
