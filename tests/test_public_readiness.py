import subprocess
import sys
from pathlib import Path

import pytest

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
        run: |
          if git diff --quiet "${{BASE_SHA}}" HEAD -- .; then
            echo "full=false" >> "${{GITHUB_OUTPUT}}"
          else
            echo "full=true" >> "${{GITHUB_OUTPUT}}"
          fi
  test:
    needs: checks
    if: needs.checks.outputs.full == 'true'
  macos:
    needs: checks
    if: needs.checks.outputs.full == 'true'
    runs-on: macos-latest
    steps:
      - run: python -m pytest tests -v
      - name: the macOS-specific probes actually return data
        run: |
          mem = probes.memory()
  required:
    if: always()
    needs: [checks, test, macos]
    steps:
      - name: enforce the complete required CI result
        env:
          CHECKS_RESULT: ${{{{ needs.checks.result }}}}
          TEST_RESULT: ${{{{ needs.test.result }}}}
          MACOS_RESULT: ${{{{ needs.macos.result }}}}
          FULL_RUN: ${{{{ needs.checks.outputs.full }}}}
        run: |
          set -eu
          test "${{CHECKS_RESULT}}" = "success"
          if [ "${{FULL_RUN}}" = "true" ]; then
            test "${{TEST_RESULT}}" = "success"
            test "${{MACOS_RESULT}}" = "success"
          elif [ "${{FULL_RUN}}" = "false" ]; then
            test "${{TEST_RESULT}}" = "skipped"
            test "${{MACOS_RESULT}}" = "skipped"
          else
            echo "invalid full-scope result: ${{FULL_RUN}}" >&2
            exit 1
          fi
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


def workflow_step_script(path, name):
    lines = path.read_text(encoding="utf-8").splitlines()
    marker = f"      - name: {name}"
    start = lines.index(marker)
    run = lines.index("        run: |", start) + 1
    body = []
    for line in lines[run:]:
        if line and not line.startswith("          "):
            break
        body.append(line[10:] if line else "")
    return "\n".join(body)


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


def test_public_readiness_policy_requires_aggregate_ci_gate(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(
        workflow,
        workflow.read_text().replace("needs: [checks, test, macos]", "needs: checks"),
    )

    result = run_policy(root)

    assert result.returncode == 1
    assert "missing lean-policy fragment: needs: [checks, test, macos]" in result.stderr


@pytest.mark.parametrize(
    ("fragment", "replacement", "message"),
    (
        (
            "    needs: checks\n    if: needs.checks.outputs.full == 'true'\n"
            "    runs-on: macos-latest",
            "    needs: checks\n    if: false\n    runs-on: macos-latest",
            "macos job must declare exactly: if: needs.checks.outputs.full == 'true'",
        ),
        (
            "    runs-on: macos-latest",
            "    runs-on: ubuntu-latest",
            "macos job must declare exactly: runs-on: macos-latest",
        ),
        (
            "  macos:",
            "  macos:\n    continue-on-error: true",
            "macos job must use only its canonical direct keys",
        ),
    ),
)
def test_public_readiness_policy_requires_automatic_blocking_macos(
    tmp_path, fragment, replacement, message
):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text()
    if fragment.startswith("    needs: checks"):
        text = text.replace(fragment, replacement, 1)
        text = text.replace(fragment, replacement, 1)
    else:
        text = text.replace(fragment, replacement)
    write(workflow, text)

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


def test_public_readiness_policy_rejects_dispatch_gated_macos(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text() + "\nhosted_macos: false\n")

    result = run_policy(root)

    assert result.returncode == 1
    assert "public full-scope macos must not be dispatch-gated" in result.stderr


@pytest.mark.parametrize(
    ("marker", "key", "message"),
    (
        (
            "      - run: python -m pytest tests -v",
            "if: false",
            "macos test step must be exact and unconditional",
        ),
        (
            "      - run: python -m pytest tests -v",
            "continue-on-error: true",
            "macos test step must be exact and unconditional",
        ),
        (
            "      - name: the macOS-specific probes actually return data",
            "'if': false",
            "macos probe step must be exact and unconditional",
        ),
        (
            "      - name: the macOS-specific probes actually return data",
            r'"sh\u0065ll": bash {0}',
            "macos probe step must be exact and unconditional",
        ),
    ),
)
def test_public_readiness_policy_rejects_skippable_macos_evidence(tmp_path, marker, key, message):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text().replace(marker, f"{marker}\n        {key}"))

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize(
    ("checks_result", "full_run", "test_result", "macos_result", "expected"),
    (
        ("success", "true", "success", "success", 0),
        ("success", "false", "skipped", "skipped", 0),
        ("success", "", "skipped", "skipped", 1),
        ("success", "documentation", "skipped", "skipped", 1),
        ("failure", "true", "success", "success", 1),
        ("success", "true", "failure", "success", 1),
        ("success", "true", "success", "failure", 1),
        ("success", "false", "skipped", "success", 1),
    ),
)
def test_required_ci_gate_fails_closed(
    checks_result, full_run, test_result, macos_result, expected
):
    script = workflow_step_script(
        VERIFY.parents[1] / ".github" / "workflows" / "ci.yml",
        "enforce the complete required CI result",
    )

    result = subprocess.run(
        ["/bin/sh", "-c", script],
        env={
            "CHECKS_RESULT": checks_result,
            "TEST_RESULT": test_result,
            "MACOS_RESULT": macos_result,
            "FULL_RUN": full_run,
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == expected, result.stderr


@pytest.mark.parametrize(
    "key",
    (
        "MACOS_RESULT: success",
        "MACOS_RESULT : success",
        "'MACOS_RESULT': success",
        r'"MACOS_\u0052ESULT": success',
    ),
)
def test_public_readiness_policy_rejects_aggregate_result_override(tmp_path, key):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    marker = "      - name: enforce the complete required CI result\n        env:"
    write(workflow, workflow.read_text().replace(marker, f"{marker}\n          {key}"))

    result = run_policy(root)

    assert result.returncode == 1
    assert "aggregate environment must use exactly its canonical result inputs" in result.stderr


@pytest.mark.parametrize(
    ("fragment", "replacement"),
    (
        (
            'test "${CHECKS_RESULT}" = "success"',
            'test "${CHECKS_RESULT}" = "failure"',
        ),
        (
            'if [ "${FULL_RUN}" = "true" ]; then',
            'if [ "${FULL_RUN}" = "false" ]; then',
        ),
        (
            'elif [ "${FULL_RUN}" = "false" ]; then',
            'elif [ "${FULL_RUN}" = "unknown" ]; then',
        ),
        (
            'test "${TEST_RESULT}" = "success"',
            'test "${TEST_RESULT}" = "failure"',
        ),
        (
            'test "${TEST_RESULT}" = "skipped"',
            'test "${TEST_RESULT}" = "success"',
        ),
        (
            'test "${MACOS_RESULT}" = "success"',
            'test "${MACOS_RESULT}" = "failure"',
        ),
        (
            'test "${MACOS_RESULT}" = "skipped"',
            'test "${MACOS_RESULT}" = "success"',
        ),
    ),
)
def test_public_readiness_policy_requires_aggregate_ci_enforcement(tmp_path, fragment, replacement):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text().replace(fragment, replacement))

    result = run_policy(root)

    assert result.returncode == 1
    assert f"missing lean-policy fragment: {fragment}" in result.stderr


@pytest.mark.parametrize(
    "key",
    (
        "if: false",
        "'if': false",
        r'"\u0069f": false',
        "continue-on-error: true",
        "continue-on-error : true",
        "'continue-on-error': true",
        r'"continue-on-\u0065rror": true',
        "shell: bash {0}",
        "'shell': bash {0}",
        r'"sh\u0065ll": bash {0}',
    ),
)
def test_public_readiness_policy_rejects_skippable_aggregate_enforcement(tmp_path, key):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    marker = "      - name: enforce the complete required CI result"
    write(workflow, workflow.read_text().replace(marker, f"{marker}\n        {key}"))

    result = run_policy(root)

    assert result.returncode == 1
    assert "aggregate enforcement step must use only its canonical direct keys" in result.stderr


@pytest.mark.parametrize(
    "key",
    (
        "continue-on-error: true",
        "continue-on-error : true",
        "'continue-on-error': true",
        r'"continue-on-\u0065rror": true',
    ),
)
def test_public_readiness_policy_rejects_nonblocking_aggregate_job(tmp_path, key):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    marker = "  required:"
    write(workflow, workflow.read_text().replace(marker, f"{marker}\n    {key}"))

    result = run_policy(root)

    assert result.returncode == 1
    assert "aggregate job must use only its canonical direct keys" in result.stderr


@pytest.mark.parametrize(
    ("marker", "key", "message"),
    (
        (
            "  required:",
            "if: always()",
            "aggregate job must use only its canonical direct keys",
        ),
        (
            "      - name: enforce the complete required CI result",
            "run: echo bypass",
            "aggregate enforcement step must use only its canonical direct keys",
        ),
    ),
)
def test_public_readiness_policy_rejects_duplicate_aggregate_keys(tmp_path, marker, key, message):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    indent = "    " if marker == "  required:" else "        "
    write(workflow, workflow.read_text().replace(marker, f"{marker}\n{indent}{key}"))

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


def test_public_readiness_policy_requires_exact_aggregate_job_condition(tmp_path):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text().replace("    if: always()", "    if: always() && false"))

    result = run_policy(root)

    assert result.returncode == 1
    assert "aggregate job must declare exactly: if: always()" in result.stderr


@pytest.mark.parametrize(
    "output",
    (
        'echo "full=true" >> "${GITHUB_OUTPUT}"',
        'echo "full=false" >> "${GITHUB_OUTPUT}"',
    ),
)
def test_public_readiness_policy_requires_both_scope_outputs(tmp_path, output):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    write(workflow, workflow.read_text().replace(output, "echo invalid"))

    result = run_policy(root)

    assert result.returncode == 1
    assert f"scope step must emit: {output}" in result.stderr


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
