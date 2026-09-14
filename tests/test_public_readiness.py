import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

VERIFY = Path(__file__).parents[1] / "scripts" / "verify_public_readiness.py"
PIN = "a" * 40
NO_REPLY = "17068914+nachiketbhujbal@users.noreply.github.com"
SCOPE_CONDITION = (
    'git diff --quiet "${BASE_SHA}" HEAD -- . '
    "':(exclude)docs/**' ':(exclude)**/*.md' "
    "':(top,glob,exclude)*.md' ':(exclude)LICENSE'"
)
BASE_SHA_EXPRESSION = (
    "${{ github.event_name == 'pull_request' "
    "&& github.event.pull_request.base.sha || github.event.before }}"
)


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
    runs-on: ubuntu-latest
    timeout-minutes: 10
    outputs:
      full: ${{{{ steps.scope.outputs.full }}}}
    steps:
      - uses: actions/checkout@{PIN} # v7.0.1
        with:
          fetch-depth: 0
      - run: python scripts/audit_reachable_history.py --ref HEAD
      - name: preserve the documentation-only compute boundary
        id: scope
        env:
          BASE_SHA: {BASE_SHA_EXPRESSION}
        run: |
          if [ "${{GITHUB_EVENT_NAME}}" = "workflow_dispatch" ]; then
            echo "full=true" >> "${{GITHUB_OUTPUT}}"
          elif {SCOPE_CONDITION}; then
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
        rf"""name: Release
on:
  push:
    tags: ["v*"]
permissions:
  contents: read
concurrency:
  group: release-${{{{ github.ref }}}}
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    outputs:
      artifact_name: ${{{{ steps.identity.outputs.artifact_name }}}}
      version: ${{{{ steps.identity.outputs.version }}}}
      wheel_name: ${{{{ steps.identity.outputs.wheel_name }}}}
      wheel_sha256: ${{{{ steps.identity.outputs.wheel_sha256 }}}}
      sdist_name: ${{{{ steps.identity.outputs.sdist_name }}}}
      sdist_sha256: ${{{{ steps.identity.outputs.sdist_sha256 }}}}
    steps:
      - uses: actions/checkout@{PIN} # v7
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@{PIN} # v7
      - uses: astral-sh/setup-uv@{PIN} # v10.1.0
        with:
          version: "0.12.5"
      - run: uv sync --locked --group dev --group release --no-install-project
      - run: uv run --no-sync python scripts/audit_reachable_history.py --ref HEAD
      - run: |
          uv run --no-sync python scripts/verify_docs.py
          uv run --no-sync python scripts/verify_public_readiness.py
      - run: uv run --no-sync pytest tests
      - run: uv build --no-build-isolation --out-dir release-dist
      - run: rm release-dist/.gitignore
      - run: uv run --no-sync python scripts/verify_artifacts.py release-dist/*
      - run: uv run --no-sync twine check --strict release-dist/*
      - id: identity
        env:
          ARTIFACT_NAME: release-distributions-${{{{ github.sha }}}}
        run: |
          uv run --no-sync python scripts/release_artifacts.py prepare \
            --artifact-name "${{ARTIFACT_NAME}}"
      - uses: actions/upload-artifact@{PIN} # v7
        with:
          name: ${{{{ steps.identity.outputs.artifact_name }}}}
          path: release-dist
          if-no-files-found: error
          include-hidden-files: false
  github-release:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@{PIN} # v7
        with:
          persist-credentials: false
      - uses: actions/setup-python@{PIN} # v7
      - uses: actions/download-artifact@{PIN} # v8.0.1
        with:
          name: ${{{{ needs.build.outputs.artifact_name }}}}
          path: release-dist
      - env:
          WHEEL_NAME: ${{{{ needs.build.outputs.wheel_name }}}}
          WHEEL_SHA256: ${{{{ needs.build.outputs.wheel_sha256 }}}}
          SDIST_NAME: ${{{{ needs.build.outputs.sdist_name }}}}
          SDIST_SHA256: ${{{{ needs.build.outputs.sdist_sha256 }}}}
        run: python scripts/release_artifacts.py verify
      - uses: softprops/action-gh-release@{PIN} # v3.0.3
        with:
          files: |
            release-dist/${{{{ needs.build.outputs.wheel_name }}}}
            release-dist/${{{{ needs.build.outputs.sdist_name }}}}
          generate_release_notes: true
  testpypi-publish:
    needs: [build, github-release]
    runs-on: ubuntu-latest
    timeout-minutes: 5
    environment:
      name: testpypi
      url: https://test.pypi.org/p/agent-statusline/
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
        with:
          name: ${{{{ needs.build.outputs.artifact_name }}}}
          path: release-dist
      - name: publish the exact artifacts to TestPyPI
        uses: pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33 # v1.14.2
        with:
          packages-dir: release-dist/
          repository-url: https://test.pypi.org/legacy/
  testpypi-verify:
    needs: [build, testpypi-publish]
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@{PIN} # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-python@{PIN} # v7.0.0
        with:
          python-version: "3.9"
      - env:
          VERSION: ${{{{ needs.build.outputs.version }}}}
          WHEEL_NAME: ${{{{ needs.build.outputs.wheel_name }}}}
          WHEEL_SHA256: ${{{{ needs.build.outputs.wheel_sha256 }}}}
          SDIST_NAME: ${{{{ needs.build.outputs.sdist_name }}}}
          SDIST_SHA256: ${{{{ needs.build.outputs.sdist_sha256 }}}}
        run: |
          python scripts/verify_package_index.py \
            --index testpypi \
            --project agent-statusline \
            --version "${{VERSION}}" \
            --wheel-name "${{WHEEL_NAME}}" \
            --wheel-sha256 "${{WHEEL_SHA256}}" \
            --sdist-name "${{SDIST_NAME}}" \
            --sdist-sha256 "${{SDIST_SHA256}}" \
            --attempts 12 \
            --delay-seconds 5 \
            --timeout-seconds 10
      - env:
          VERSION: ${{{{ needs.build.outputs.version }}}}
          AGENT_STATUSLINE_STATE: ${{{{ runner.temp }}}}/agent-statusline-testpypi-state
        run: |
          python -m venv testpypi-venv
          testpypi-venv/bin/python -m pip install \
            --disable-pip-version-check \
            --no-cache-dir \
            --no-deps \
            --only-binary=:all: \
            --index-url https://test.pypi.org/simple/ \
            --retries 4 \
            --timeout 10 \
            "agent-statusline==${{VERSION}}"
          test "$(testpypi-venv/bin/agent-statusline --version)" = "${{VERSION}}"
          testpypi-venv/bin/agent-statusline selftest
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
    ("fragment", "replacement"),
    (
        (
            BASE_SHA_EXPRESSION,
            "${{ github.sha }}",
        ),
        (
            "          fi\n",
            '          fi\n          echo "full=false" >> "${GITHUB_OUTPUT}"\n',
        ),
        (" ':(top,glob,exclude)*.md'", ""),
    ),
)
def test_public_readiness_policy_requires_exact_scope_classifier(tmp_path, fragment, replacement):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text()
    assert fragment in text
    write(workflow, text.replace(fragment, replacement, 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert "exactly match the reviewed fail-closed classifier" in result.stderr


@pytest.mark.parametrize(
    ("fragment", "replacement", "message"),
    (
        (
            "      full: ${{ steps.scope.outputs.full }}",
            "      full: ${{ 'false' }}",
            "checks outputs must bind exactly to the scope step",
        ),
        (
            "      full: ${{ steps.scope.outputs.full }}",
            "      full: false",
            "checks outputs must bind exactly to the scope step",
        ),
        (
            "      full: ${{ steps.scope.outputs.full }}",
            "      full: ${{ steps.scope.outputs.missing }}",
            "checks outputs must bind exactly to the scope step",
        ),
        (
            "      full: ${{ steps.scope.outputs.full }}",
            "      full: ${{ steps.scope.outputs.full }}\n      full: false",
            "checks outputs must bind exactly to the scope step",
        ),
        (
            "      full: ${{ steps.scope.outputs.full }}",
            "      'full': false",
            "checks outputs must bind exactly to the scope step",
        ),
        (
            "    outputs:\n      full: ${{ steps.scope.outputs.full }}",
            "    outputs:\n      full: ${{ steps.scope.outputs.full }}\n"
            "    outputs:\n      full: false",
            "checks job must use only its canonical direct keys",
        ),
        (
            "  checks:\n    runs-on: ubuntu-latest",
            "  checks:\n    continue-on-error: true\n    runs-on: ubuntu-latest",
            "checks job must use only its canonical direct keys",
        ),
    ),
)
def test_public_readiness_policy_binds_checks_scope_output(
    tmp_path, fragment, replacement, message
):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text()
    assert fragment in text
    write(workflow, text.replace(fragment, replacement, 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize(
    ("relative", "expected"),
    (
        ("README.md", "false"),
        ("HANDOFF.md", "false"),
        ("docs/guide.md", "false"),
        ("src/example.py", "true"),
        (".github/workflows/ci.yml", "true"),
    ),
)
def test_ci_scope_classifies_root_and_nested_documentation(tmp_path, relative, expected):
    root = tmp_path / "repository"
    for path in (
        "README.md",
        "HANDOFF.md",
        "docs/guide.md",
        "src/example.py",
        ".github/workflows/ci.yml",
    ):
        write(root / path, "base\n")
    commit_repository(root)
    base_sha = git(root, "rev-parse", "HEAD").stdout.strip()
    write(root / relative, "changed\n")
    git(root, "add", relative)
    git(root, "commit", "-m", "change")

    output = tmp_path / "scope-output"
    script = workflow_step_script(
        VERIFY.parents[1] / ".github" / "workflows" / "ci.yml",
        "preserve the documentation-only compute boundary",
    )
    result = subprocess.run(
        ["/bin/sh", "-c", script],
        cwd=root,
        env={
            **os.environ,
            "BASE_SHA": base_sha,
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8") == f"full={expected}\n"


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


@pytest.mark.parametrize(
    ("fragment", "replacement", "message"),
    (
        (
            "permissions:\n  contents: read\nconcurrency:",
            "permissions:\n  contents: write\nconcurrency:",
            "workflow permissions must be exactly contents: read",
        ),
        (
            "    permissions:\n      contents: read\n    outputs:",
            "    permissions:\n      contents: write\n    outputs:",
            "build job permissions must be exactly contents: read",
        ),
        (
            "  github-release:\n    needs: build",
            "  github-release:\n    needs: other-job",
            "github-release job must depend exactly on build",
        ),
        (
            "    permissions:\n      contents: write\n    steps:",
            "    permissions:\n      contents: read\n    steps:",
            "github-release permissions must be exactly contents: write",
        ),
        (
            "      - run: uv build --no-build-isolation --out-dir release-dist",
            "      - run: uv build --no-build-isolation --out-dir release-dist\n"
            "      - run: uv build --no-build-isolation --out-dir release-dist",
            "release pipeline must contain exactly once: uv build",
        ),
        (
            "          name: ${{ needs.build.outputs.artifact_name }}",
            "          name: release-distributions-unbound",
            "needs.build.outputs.artifact_name",
        ),
        (
            "            release-dist/${{ needs.build.outputs.wheel_name }}",
            "            dist/*",
            "ambient dist wildcard is forbidden",
        ),
        (
            "  contents: read\nconcurrency:",
            "  contents: read\n  id-token: write\nconcurrency:",
            "exactly one job must receive package-index identity permission",
        ),
        (
            "  build:\n    runs-on: ubuntu-latest",
            "  build:\n    continue-on-error: true\n    runs-on: ubuntu-latest",
            "build job must use only its canonical direct keys",
        ),
    ),
)
def test_public_readiness_policy_enforces_build_once_release_topology(
    tmp_path, fragment, replacement, message
):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "release.yml"
    text = workflow.read_text()
    assert fragment in text
    write(workflow, text.replace(fragment, replacement, 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize(
    ("fragment", "replacement", "message"),
    (
        (
            "  testpypi-publish:\n    needs: [build, github-release]",
            "  testpypi-publish:\n    needs: github-release",
            "TestPyPI publish job must use only its canonical direct keys",
        ),
        (
            "      name: testpypi",
            "      name: pypi",
            "TestPyPI publish environment must be exact",
        ),
        (
            "      id-token: write",
            "      contents: write",
            "TestPyPI publish permission must be exactly id-token: write",
        ),
        (
            "          packages-dir: release-dist/",
            "          packages-dir: dist/",
            "TestPyPI publish job must contain exactly once: packages-dir: release-dist/",
        ),
        (
            "          repository-url: https://test.pypi.org/legacy/",
            "          repository-url: https://upload.pypi.org/legacy/",
            "TestPyPI publish job must contain exactly once: repository-url",
        ),
        (
            "  testpypi-verify:\n    needs: [build, testpypi-publish]",
            "  testpypi-verify:\n    needs: testpypi-publish",
            "TestPyPI verification job must use only its canonical direct keys",
        ),
        (
            "            --attempts 12",
            "            --attempts 120",
            "TestPyPI verification job requires exact bounded option: --attempts 12",
        ),
        (
            "            --no-deps",
            "            --deps",
            "TestPyPI verification job is missing: --no-deps",
        ),
        (
            "          AGENT_STATUSLINE_STATE: ${{ runner.temp }}/agent-statusline-testpypi-state",
            "          AGENT_STATUSLINE_STATE: ~/.local/state/agent-statusline",
            "TestPyPI verification job is missing: AGENT_STATUSLINE_STATE",
        ),
        (
            "          testpypi-venv/bin/agent-statusline selftest",
            "          testpypi-venv/bin/agent-statusline --selftest",
            "TestPyPI verification job is missing: testpypi-venv/bin/agent-statusline selftest",
        ),
    ),
)
def test_public_readiness_policy_enforces_testpypi_boundaries(
    tmp_path, fragment, replacement, message
):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "release.yml"
    text = workflow.read_text()
    assert fragment in text
    write(workflow, text.replace(fragment, replacement, 1))

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize(
    ("insertion", "message"),
    (
        (
            "        run: echo bypass\n",
            "TestPyPI publish job must not contain: run:",
        ),
        (
            '        "password": ${{ secrets.TESTPYPI_TOKEN }}\n',
            "stored package-index credentials are forbidden",
        ),
        (
            "        skip_existing: true\n",
            "TestPyPI publishing action step must be exact",
        ),
    ),
)
def test_public_readiness_policy_rejects_testpypi_publish_bypasses(tmp_path, insertion, message):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "release.yml"
    marker = "        uses: pypa/gh-action-pypi-publish@"
    text = workflow.read_text()
    index = text.index(marker)
    line_end = text.index("\n", index) + 1
    write(workflow, text[:line_end] + insertion + text[line_end:])

    result = run_policy(root)

    assert result.returncode == 1
    assert message in result.stderr


@pytest.mark.parametrize(
    "extra_input",
    (
        "          repository: other/project\n",
        "          run-id: 1234\n",
        "          github-token: ${{ github.token }}\n",
    ),
)
def test_public_readiness_policy_rejects_cross_run_artifact_sources(tmp_path, extra_input):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "release.yml"
    text = workflow.read_text()
    before, publish = text.split("  testpypi-publish:", 1)
    marker = "          path: release-dist\n"
    assert marker in publish
    write(
        workflow, before + "  testpypi-publish:" + publish.replace(marker, marker + extra_input, 1)
    )

    result = run_policy(root)

    assert result.returncode == 1
    assert "TestPyPI download inputs must bind only the current build artifact" in result.stderr


def test_testpypi_workflow_selftest_command_matches_the_real_cli(tmp_path):
    script = workflow_step_script(
        VERIFY.parents[1] / ".github" / "workflows" / "release.yml",
        "install the exact TestPyPI wheel and run its isolated self-test",
    )
    selftest_line = script.splitlines()[-1]
    assert selftest_line == "testpypi-venv/bin/agent-statusline selftest"
    command = selftest_line.replace(
        "testpypi-venv/bin/agent-statusline",
        f"{shlex.quote(sys.executable)} -m agent_statusline",
    )
    env = os.environ.copy()
    env["AGENT_STATUSLINE_STATE"] = str(tmp_path / "state")
    env["PYTHONPATH"] = str(VERIFY.parents[1] / "src")

    result = subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "selftest ok" in result.stdout


@pytest.mark.parametrize(
    "key",
    (
        "if: false",
        "if : false",
        "'if': false",
        r'"\u0069f": false',
        "continue-on-error: true",
        "continue-on-error : true",
        "'continue-on-error': true",
        r'"continue-on-\u0065rror": true',
    ),
)
def test_public_readiness_policy_rejects_conditional_release_evidence(tmp_path, key):
    root = valid_repository(tmp_path)
    workflow = root / ".github" / "workflows" / "release.yml"
    marker = "      - run: uv run --no-sync pytest tests"
    write(workflow, workflow.read_text().replace(marker, f"{marker}\n        {key}"))

    result = run_policy(root)

    assert result.returncode == 1
    assert "release evidence may not be conditional or nonblocking" in result.stderr


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
