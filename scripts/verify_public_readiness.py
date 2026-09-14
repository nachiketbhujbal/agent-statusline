#!/usr/bin/env python3
"""Verify static repository boundaries needed before public visibility."""

import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

REQUIRED_PRIVATE_IGNORES = ("/.claude/", "/.pvt/", "/.worktrees/")
ACTION_RE = re.compile(r"^\s*-\s+uses:\s+([^#\s]+)(?:\s+#\s*(.+?))?\s*$", re.MULTILINE)
PINNED_ACTION_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"^v\d+(?:\.\d+){0,2}$")
PRIVATE_BILLING_RE = (
    re.compile(r"\$\s*\d"),
    re.compile(r"\b\d+(?:[.,]\d+)?\s+Linux-equivalent minutes\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s+percent\b", re.IGNORECASE),
    re.compile(r"\babout\s+\d+\s+(?:billed\s+)?minutes\b", re.IGNORECASE),
)
EXPECTED_RELEASE_AUTHOR_EMAIL = "17068914+nachiketbhujbal@users.noreply.github.com"
ALLOWED_RELEASE_COMMITTER_EMAILS = (
    EXPECTED_RELEASE_AUTHOR_EMAIL,
    "noreply@github.com",
)


def _read(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        errors.append(f"{path.as_posix()}: cannot read: {error}")
        return ""


def check_private_ignores(root: Path) -> list[str]:
    errors: list[str] = []
    lines = {line.strip() for line in _read(root / ".gitignore", errors).splitlines()}
    for boundary in REQUIRED_PRIVATE_IGNORES:
        if boundary not in lines:
            errors.append(f".gitignore: missing root private boundary {boundary}")
    return errors


def check_workflows(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_dir = root / ".github" / "workflows"
    paths = sorted((*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")))
    if not paths:
        return [".github/workflows: no workflow files found"]

    action_count = 0
    for path in paths:
        text = _read(path, errors)
        relative = path.relative_to(root).as_posix()
        if "RENDER_HOME" in text:
            errors.append(f"{relative}: undefined RENDER_HOME prefix is forbidden")
        for match in ACTION_RE.finditer(text):
            action, comment = match.groups()
            if action.startswith("./"):
                continue
            action_count += 1
            if not PINNED_ACTION_RE.fullmatch(action):
                errors.append(
                    f"{relative}: third-party action is not pinned to a full SHA: {action}"
                )
            if comment is None or not VERSION_COMMENT_RE.fullmatch(comment.strip()):
                errors.append(f"{relative}: action pin lacks a readable version comment: {action}")

    if not action_count:
        errors.append(".github/workflows: no third-party actions found")
    return errors


def _yaml_block(text: str, header: str, indent: int) -> Optional[str]:
    """Return one exact indentation-delimited YAML block without parsing YAML."""
    lines = text.splitlines()
    wanted = " " * indent + header
    matches = [index for index, line in enumerate(lines) if line == wanted]
    if len(matches) != 1:
        return None
    start = matches[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip(" ")) <= indent:
            end = index
            break
    return "\n".join(lines[start:end])


def _yaml_step_with_id(text: str, step_id: str) -> Optional[str]:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("      - ")]
    matches = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        for index in range(start + 1, end):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip(" ")) <= 4:
                end = index
                break
        block = "\n".join(lines[start:end])
        if re.search(rf"^(?:      - |        )id:\s*{re.escape(step_id)}\s*$", block, re.MULTILINE):
            matches.append(block)
    return matches[0] if len(matches) == 1 else None


def _yaml_step_with_action(text: str, action: str) -> Optional[str]:
    """Return the unique workflow step invoking one exact action."""
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("      - ")]
    matches = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        for index in range(start + 1, end):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip(" ")) <= 4:
                end = index
                break
        block = "\n".join(lines[start:end])
        if re.search(
            rf"^(?:      - |        )uses:\s*{re.escape(action)}(?:\s+#\s*[^\n]+)?$",
            block,
            re.MULTILINE,
        ):
            matches.append(block)
    return matches[0] if len(matches) == 1 else None


def _canonical_yaml_direct_entries(text: str, indent: int) -> Optional[list[tuple[str, str]]]:
    """Return canonical direct mapping entries, or None for ambiguous syntax."""
    padding = " " * indent
    entries = []
    for line in text.splitlines():
        if not line.startswith(padding) or line.startswith(padding + " "):
            continue
        content = line[indent:]
        if not content or content.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):(?:\s+(.*))?", content)
        if match is None:
            return None
        entries.append((match.group(1), match.group(2) or ""))
    return entries


def _exact_mapping(
    text: str,
    *,
    indent: int,
    expected: dict[str, str],
) -> bool:
    entries = _canonical_yaml_direct_entries(text, indent)
    if entries is None:
        return False
    keys = [key for key, _value in entries]
    return len(keys) == len(set(keys)) and dict(entries) == expected


def _has_yaml_key(text: str, expected: str) -> bool:
    """Recognize plain, quoted, spaced, and simple escaped spellings of a key."""
    for line in text.splitlines():
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip().strip("'\"")
        key = key.replace(r"\u0069", "i").replace(r"\u0065", "e")
        if key == expected:
            return True
    return False


def check_release_pipeline(release: str) -> list[str]:
    """Require build-once promotion and least-privilege release topology."""
    path = ".github/workflows/release.yml"
    errors: list[str] = []

    permissions = _yaml_block(release, "permissions:", indent=0)
    if permissions is None or not _exact_mapping(
        permissions, indent=2, expected={"contents": "read"}
    ):
        errors.append(f"{path}: workflow permissions must be exactly contents: read")

    concurrency = _yaml_block(release, "concurrency:", indent=0)
    expected_concurrency = {
        "group": "release-${{ github.ref }}",
        "cancel-in-progress": "false",
    }
    if concurrency is None or not _exact_mapping(
        concurrency, indent=2, expected=expected_concurrency
    ):
        errors.append(f"{path}: release concurrency must bind one immutable tag ref")

    jobs = _yaml_block(release, "jobs:", indent=0)
    if jobs is None or not _exact_mapping(
        jobs,
        indent=2,
        expected={
            "build": "",
            "github-release": "",
        },
    ):
        errors.append(f"{path}: release workflow must contain exactly the two reviewed jobs")

    build = _yaml_block(release, "build:", indent=2)
    expected_build = {
        "runs-on": "ubuntu-latest",
        "timeout-minutes": "10",
        "permissions": "",
        "outputs": "",
        "steps": "",
    }
    if build is None or not _exact_mapping(build, indent=4, expected=expected_build):
        errors.append(f"{path}: build job must use only its canonical direct keys")
        build = ""

    build_permissions = _yaml_block(build, "permissions:", indent=4)
    if build_permissions is None or not _exact_mapping(
        build_permissions, indent=6, expected={"contents": "read"}
    ):
        errors.append(f"{path}: build job permissions must be exactly contents: read")

    expected_outputs = {
        "artifact_name": "${{ steps.identity.outputs.artifact_name }}",
        "version": "${{ steps.identity.outputs.version }}",
        "wheel_name": "${{ steps.identity.outputs.wheel_name }}",
        "wheel_sha256": "${{ steps.identity.outputs.wheel_sha256 }}",
        "sdist_name": "${{ steps.identity.outputs.sdist_name }}",
        "sdist_sha256": "${{ steps.identity.outputs.sdist_sha256 }}",
    }
    outputs = _yaml_block(build, "outputs:", indent=4)
    if outputs is None or not _exact_mapping(outputs, indent=6, expected=expected_outputs):
        errors.append(f"{path}: build outputs must expose exactly the bound artifact identities")

    publish = _yaml_block(release, "github-release:", indent=2)
    expected_publish = {
        "needs": "build",
        "runs-on": "ubuntu-latest",
        "timeout-minutes": "5",
        "permissions": "",
        "steps": "",
    }
    if publish is None or not _exact_mapping(publish, indent=4, expected=expected_publish):
        errors.append(f"{path}: github-release job must depend exactly on build")
        publish = ""

    publish_permissions = _yaml_block(publish, "permissions:", indent=4)
    if publish_permissions is None or not _exact_mapping(
        publish_permissions, indent=6, expected={"contents": "write"}
    ):
        errors.append(f"{path}: github-release permissions must be exactly contents: write")

    required_once = (
        "uv sync --locked --group dev --group release --no-install-project",
        "uv build --no-build-isolation --out-dir release-dist",
        "rm release-dist/.gitignore",
        "twine check --strict release-dist/*",
        "scripts/release_artifacts.py prepare",
        '--artifact-name "${ARTIFACT_NAME}"',
        "          name: ${{ steps.identity.outputs.artifact_name }}",
        "scripts/release_artifacts.py verify",
        "release-dist/${{ needs.build.outputs.wheel_name }}",
        "release-dist/${{ needs.build.outputs.sdist_name }}",
    )
    for fragment in required_once:
        if release.count(fragment) != 1:
            errors.append(f"{path}: release pipeline must contain exactly once: {fragment}")

    required_build = (
        "actions/checkout@",
        "actions/setup-python@",
        "astral-sh/setup-uv@",
        "actions/upload-artifact@",
        'version: "0.12.5"',
        "persist-credentials: false",
        "uv run --no-sync python scripts/audit_reachable_history.py --ref HEAD",
        "uv run --no-sync python scripts/verify_docs.py",
        "uv run --no-sync python scripts/verify_public_readiness.py",
        "uv run --no-sync pytest tests",
        "uv run --no-sync python scripts/verify_artifacts.py release-dist/*",
        "ARTIFACT_NAME: release-distributions-${{ github.sha }}",
        "path: release-dist",
        "if-no-files-found: error",
        "include-hidden-files: false",
    )
    for fragment in required_build:
        if fragment not in build:
            errors.append(f"{path}: build job is missing: {fragment}")

    required_publish = (
        "actions/checkout@",
        "actions/setup-python@",
        "actions/download-artifact@",
        "name: ${{ needs.build.outputs.artifact_name }}",
        "path: release-dist",
        "persist-credentials: false",
        "WHEEL_NAME: ${{ needs.build.outputs.wheel_name }}",
        "WHEEL_SHA256: ${{ needs.build.outputs.wheel_sha256 }}",
        "SDIST_NAME: ${{ needs.build.outputs.sdist_name }}",
        "SDIST_SHA256: ${{ needs.build.outputs.sdist_sha256 }}",
        "softprops/action-gh-release@",
        "generate_release_notes: true",
    )
    for fragment in required_publish:
        if fragment not in publish:
            errors.append(f"{path}: github-release job is missing: {fragment}")

    if re.search(r"^\s*id-token\s*:", release, re.MULTILINE):
        errors.append(f"{path}: release workflow must not receive package-index identity")
    if (
        any(
            _has_yaml_key(release, key)
            for key in ("password", "user", "username", "api-token", "secrets")
        )
        or "${{ secrets." in release
    ):
        errors.append(f"{path}: stored package-index credentials are forbidden")
    if re.search(r"(?:^|\s)dist/\*", release):
        errors.append(f"{path}: ambient dist wildcard is forbidden")
    if "python -m build" in release:
        errors.append(f"{path}: unbounded Python build command is forbidden")
    if _has_yaml_key(release, "continue-on-error") or _has_yaml_key(release, "if"):
        errors.append(f"{path}: release evidence may not be conditional or nonblocking")
    return errors


def check_package_publish_pipeline(workflow: str, *, index: str) -> list[str]:
    """Require manual, exact-release promotion with one OIDC-only authority job."""
    settings = {
        "testpypi": {
            "name": "Publish to TestPyPI",
            "label": "TestPyPI",
            "environment_url": "https://test.pypi.org/p/agent-statusline/",
            "json_index": "testpypi",
            "simple_url": "https://test.pypi.org/simple/",
            "venv": "testpypi-venv",
            "state": "agent-statusline-testpypi-state",
            "publish_inputs": {
                "packages-dir": "release-dist/",
                "repository-url": "https://test.pypi.org/legacy/",
            },
            "prepare_sha256": "370b854a656c05caccb8f0938a16d206f2d87a08851fe37b804f3322d3b224c8",
            "verify_sha256": "441f514e889f635572002eab0a8d0dc64b2ed1c086f34d5beda9fc332cb04d96",
        },
        "pypi": {
            "name": "Publish to PyPI",
            "label": "PyPI",
            "environment_url": "https://pypi.org/p/agent-statusline/",
            "json_index": "pypi",
            "simple_url": "https://pypi.org/simple/",
            "venv": "pypi-venv",
            "state": "agent-statusline-pypi-state",
            "publish_inputs": {"packages-dir": "release-dist/"},
            "prepare_sha256": "e130d9658be8ec7269327f2afe75dd698691f0fe45a9396075bc82844ef005bb",
            "verify_sha256": "caf6f9cf713d6911955b4b0df450759e95acfd3e12c448c9c9b3a1a592323e7f",
        },
    }
    if index not in settings:
        raise ValueError(f"unsupported package index: {index}")
    config = settings[index]
    label = str(config["label"])
    path = f".github/workflows/publish-{index}.yml"
    errors: list[str] = []

    if not _exact_mapping(
        workflow,
        indent=0,
        expected={
            "name": str(config["name"]),
            "on": "",
            "permissions": "",
            "concurrency": "",
            "jobs": "",
        },
    ):
        errors.append(f"{path}: workflow must use only its canonical top-level keys")

    trigger = _yaml_block(workflow, "on:", indent=0)
    dispatch = _yaml_block(trigger or "", "workflow_dispatch:", indent=2)
    inputs = _yaml_block(dispatch or "", "inputs:", indent=4)
    tag = _yaml_block(inputs or "", "tag:", indent=6)
    if trigger is None or not _exact_mapping(trigger, indent=2, expected={"workflow_dispatch": ""}):
        errors.append(f"{path}: publishing trigger must be exactly workflow_dispatch")
    if dispatch is None or not _exact_mapping(dispatch, indent=4, expected={"inputs": ""}):
        errors.append(f"{path}: workflow dispatch must expose exactly one inputs mapping")
    if inputs is None or not _exact_mapping(inputs, indent=6, expected={"tag": ""}):
        errors.append(f"{path}: workflow dispatch input must be exactly tag")
    if tag is None or not _exact_mapping(
        tag,
        indent=8,
        expected={
            "description": "Exact published release tag (vMAJOR.MINOR.PATCH)",
            "required": "true",
            "type": "string",
        },
    ):
        errors.append(f"{path}: tag input contract must be exact")

    permissions = _yaml_block(workflow, "permissions:", indent=0)
    if permissions is None or not _exact_mapping(
        permissions, indent=2, expected={"contents": "read"}
    ):
        errors.append(f"{path}: workflow permissions must be exactly contents: read")
    concurrency = _yaml_block(workflow, "concurrency:", indent=0)
    if concurrency is None or not _exact_mapping(
        concurrency,
        indent=2,
        expected={
            "group": f"publish-{index}-${{{{ inputs.tag }}}}",
            "cancel-in-progress": "false",
        },
    ):
        errors.append(f"{path}: concurrency must bind the selected immutable tag")

    jobs = _yaml_block(workflow, "jobs:", indent=0)
    if jobs is None or not _exact_mapping(
        jobs, indent=2, expected={"prepare": "", "publish": "", "verify": ""}
    ):
        errors.append(f"{path}: workflow must contain exactly prepare, publish, and verify jobs")

    prepare = _yaml_block(workflow, "prepare:", indent=2) or ""
    if hashlib.sha256(prepare.encode()).hexdigest() != config["prepare_sha256"]:
        errors.append(f"{path}: prepare steps must match the exact reviewed sequence")
    if not _exact_mapping(
        prepare,
        indent=4,
        expected={
            "runs-on": "ubuntu-latest",
            "timeout-minutes": "10",
            "permissions": "",
            "outputs": "",
            "steps": "",
        },
    ):
        errors.append(f"{path}: prepare job must use only its canonical direct keys")
    prepare_permissions = _yaml_block(prepare, "permissions:", indent=4)
    if prepare_permissions is None or not _exact_mapping(
        prepare_permissions, indent=6, expected={"contents": "read"}
    ):
        errors.append(f"{path}: prepare permissions must be exactly contents: read")
    expected_outputs = {
        "artifact_name": "${{ steps.identity.outputs.artifact_name }}",
        "version": "${{ steps.identity.outputs.version }}",
        "wheel_name": "${{ steps.identity.outputs.wheel_name }}",
        "wheel_sha256": "${{ steps.identity.outputs.wheel_sha256 }}",
        "sdist_name": "${{ steps.identity.outputs.sdist_name }}",
        "sdist_sha256": "${{ steps.identity.outputs.sdist_sha256 }}",
    }
    outputs = _yaml_block(prepare, "outputs:", indent=4)
    if outputs is None or not _exact_mapping(outputs, indent=6, expected=expected_outputs):
        errors.append(f"{path}: prepare outputs must expose exactly the bound identities")

    required_prepare = (
        "actions/checkout@",
        "actions/setup-python@",
        "astral-sh/setup-uv@",
        "actions/upload-artifact@",
        "fetch-depth: 0",
        "persist-credentials: false",
        'version: "0.12.5"',
        "uv sync --locked --group dev --group release --no-install-project",
        'test "${GITHUB_EVENT_NAME}" = "workflow_dispatch"',
        'test "${GITHUB_REF}" = "refs/heads/main"',
        'git cat-file -t "refs/tags/${TAG}"',
        'git rev-parse "refs/tags/${TAG}^{commit}"',
        'git merge-base --is-ancestor "${TAG_COMMIT}" "${GITHUB_SHA}"',
        'gh release download "${TAG}"',
        "--json isDraft --jq .isDraft",
        "--json isPrerelease --jq .isPrerelease",
        "--pattern 'agent_statusline-*.whl'",
        "--pattern 'agent_statusline-*.tar.gz'",
        "scripts/verify_artifacts.py release-dist/*",
        "twine check --strict release-dist/*",
        "scripts/release_artifacts.py prepare",
        '--tag "${TAG}"',
        "ARTIFACT_NAME: release-distributions-${{ steps.release.outputs.tag_commit }}",
        "          name: ${{ steps.identity.outputs.artifact_name }}",
        "path: release-dist",
        "if-no-files-found: error",
        "include-hidden-files: false",
        "retention-days: 1",
    )
    for fragment in required_prepare:
        if prepare.count(fragment) != 1:
            errors.append(f"{path}: prepare job must contain exactly once: {fragment}")
    if prepare.count('--repo "${GITHUB_REPOSITORY}"') != 3:
        errors.append(f"{path}: every release query must bind the current repository")

    if index == "pypi":
        required_test_evidence = (
            "TestPyPI already reports the exact promotion pair",
            "VERSION: ${{ steps.identity.outputs.version }}",
            "WHEEL_NAME: ${{ steps.identity.outputs.wheel_name }}",
            "WHEEL_SHA256: ${{ steps.identity.outputs.wheel_sha256 }}",
            "SDIST_NAME: ${{ steps.identity.outputs.sdist_name }}",
            "SDIST_SHA256: ${{ steps.identity.outputs.sdist_sha256 }}",
            "python scripts/verify_package_index.py",
            "--index testpypi",
            "--attempts 3 \\",
            "--delay-seconds 2 \\",
            "--timeout-seconds 10",
        )
        for fragment in required_test_evidence:
            if prepare.count(fragment) != 1:
                errors.append(
                    f"{path}: production preparation must contain exactly once: {fragment}"
                )
    elif "TestPyPI already reports the exact promotion pair" in prepare:
        errors.append(f"{path}: TestPyPI promotion must not require prior index publication")

    publish = _yaml_block(workflow, "publish:", indent=2) or ""
    if not _exact_mapping(
        publish,
        indent=4,
        expected={
            "needs": "prepare",
            "runs-on": "ubuntu-latest",
            "timeout-minutes": "5",
            "environment": "",
            "permissions": "",
            "steps": "",
        },
    ):
        errors.append(f"{path}: {label} publish job must use only its canonical direct keys")
    environment = _yaml_block(publish, "environment:", indent=4)
    if environment is None or not _exact_mapping(
        environment,
        indent=6,
        expected={"name": index, "url": str(config["environment_url"])},
    ):
        errors.append(f"{path}: {label} publish environment must be exact")
    publish_permissions = _yaml_block(publish, "permissions:", indent=4)
    if publish_permissions is None or not _exact_mapping(
        publish_permissions, indent=6, expected={"id-token": "write"}
    ):
        errors.append(f"{path}: {label} publish permission must be exactly id-token: write")

    download_action = "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
    download_step = _yaml_step_with_action(publish, download_action) or ""
    download_inputs = _yaml_block(download_step, "with:", indent=8)
    if (
        not download_step
        or download_step.splitlines()[0] != f"      - uses: {download_action} # v8.0.1"
        or not _exact_mapping(download_step, indent=8, expected={"with": ""})
        or download_inputs is None
        or not _exact_mapping(
            download_inputs,
            indent=10,
            expected={
                "name": "${{ needs.prepare.outputs.artifact_name }}",
                "path": "release-dist",
            },
        )
    ):
        errors.append(f"{path}: {label} download step must bind only this run's prepared pair")

    pypi_action = "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33"
    pypi_step = _yaml_step_with_action(publish, pypi_action) or ""
    pypi_inputs = _yaml_block(pypi_step, "with:", indent=8)
    if (
        not pypi_step
        or pypi_step.splitlines()[0] != f"      - name: publish the exact artifacts to {label}"
        or not _exact_mapping(
            pypi_step,
            indent=8,
            expected={"uses": pypi_action + " # v1.14.2", "with": ""},
        )
        or pypi_inputs is None
        or not _exact_mapping(pypi_inputs, indent=10, expected=dict(config["publish_inputs"]))
    ):
        errors.append(f"{path}: {label} publishing action and inputs must be exact")
    if publish.count("\n      - ") != 2:
        errors.append(f"{path}: {label} publish job must contain exactly two action steps")
    for forbidden in (
        "run:",
        "actions/checkout@",
        "actions/setup-python@",
        "uv build",
        "python -m build",
        "password:",
        "user:",
        "skip-existing:",
    ):
        if forbidden in publish:
            errors.append(f"{path}: {label} publish job must not contain: {forbidden}")

    verify = _yaml_block(workflow, "verify:", indent=2) or ""
    if hashlib.sha256(verify.encode()).hexdigest() != config["verify_sha256"]:
        errors.append(f"{path}: verify steps must match the exact reviewed sequence")
    if not _exact_mapping(
        verify,
        indent=4,
        expected={
            "needs": "[prepare, publish]",
            "runs-on": "ubuntu-latest",
            "timeout-minutes": "5",
            "permissions": "",
            "steps": "",
        },
    ):
        errors.append(f"{path}: {label} verify job must use only its canonical direct keys")
    verify_permissions = _yaml_block(verify, "permissions:", indent=4)
    if verify_permissions is None or not _exact_mapping(
        verify_permissions, indent=6, expected={"contents": "read"}
    ):
        errors.append(f"{path}: {label} verify permissions must be exactly contents: read")
    venv = str(config["venv"])
    required_verify = (
        "actions/checkout@",
        "actions/setup-python@",
        'python-version: "3.9"',
        "persist-credentials: false",
        "VERSION: ${{ needs.prepare.outputs.version }}",
        "WHEEL_NAME: ${{ needs.prepare.outputs.wheel_name }}",
        "WHEEL_SHA256: ${{ needs.prepare.outputs.wheel_sha256 }}",
        "SDIST_NAME: ${{ needs.prepare.outputs.sdist_name }}",
        "SDIST_SHA256: ${{ needs.prepare.outputs.sdist_sha256 }}",
        "python scripts/verify_package_index.py",
        f"--index {config['json_index']}",
        "--project agent-statusline",
        f"python -m venv {venv}",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--no-deps",
        "--only-binary=:all:",
        f"--index-url {config['simple_url']}",
        "--retries 4",
        "--timeout 10",
        '"agent-statusline==${VERSION}"',
        f'test "$({venv}/bin/agent-statusline --version)" = "${{VERSION}}"',
        f"AGENT_STATUSLINE_STATE: ${{{{ runner.temp }}}}/{config['state']}",
        f"{venv}/bin/agent-statusline selftest",
    )
    for fragment in required_verify:
        if fragment not in verify:
            errors.append(f"{path}: {label} verification job is missing: {fragment}")
    for exact_line in ("--attempts 12 \\", "--delay-seconds 5 \\", "--timeout-seconds 10"):
        if sum(line.strip() == exact_line for line in verify.splitlines()) != 1:
            errors.append(f"{path}: {label} verification requires: {exact_line}")

    if len(re.findall(r"^\s*id-token\s*:", workflow, re.MULTILINE)) != 1:
        errors.append(f"{path}: exactly one job must receive package-index identity permission")
    if (
        any(
            _has_yaml_key(workflow, key)
            for key in ("password", "user", "username", "api-token", "secrets")
        )
        or "${{ secrets." in workflow
    ):
        errors.append(f"{path}: stored package-index credentials are forbidden")
    if re.search(r"(?:^|\s)dist/\*", workflow):
        errors.append(f"{path}: ambient dist wildcard is forbidden")
    if "uv build" in workflow or "python -m build" in workflow:
        errors.append(f"{path}: package-index promotion must not rebuild distributions")
    if _has_yaml_key(workflow, "continue-on-error") or _has_yaml_key(workflow, "if"):
        errors.append(f"{path}: publishing evidence may not be conditional or nonblocking")
    return errors


def check_lean_policy(root: Path) -> list[str]:
    errors: list[str] = []
    ci = _read(root / ".github" / "workflows" / "ci.yml", errors)
    release = _read(root / ".github" / "workflows" / "release.yml", errors)
    publish_testpypi = _read(root / ".github" / "workflows" / "publish-testpypi.yml", errors)
    publish_pypi = _read(root / ".github" / "workflows" / "publish-pypi.yml", errors)
    required_step_fragments = (
        "CHECKS_RESULT: ${{ needs.checks.result }}",
        "TEST_RESULT: ${{ needs.test.result }}",
        "MACOS_RESULT: ${{ needs.macos.result }}",
        "FULL_RUN: ${{ needs.checks.outputs.full }}",
        "set -eu",
        'test "${CHECKS_RESULT}" = "success"',
        'if [ "${FULL_RUN}" = "true" ]; then',
        'elif [ "${FULL_RUN}" = "false" ]; then',
        'test "${TEST_RESULT}" = "success"',
        'test "${MACOS_RESULT}" = "success"',
        'test "${TEST_RESULT}" = "skipped"',
        'test "${MACOS_RESULT}" = "skipped"',
        'echo "invalid full-scope result: ${FULL_RUN}" >&2',
        "exit 1",
    )
    required_ci = (
        "pull_request:",
        "workflow_dispatch:",
        "contents: read",
        "fetch-depth: 0",
        "python scripts/audit_reachable_history.py --ref HEAD",
        "if: needs.checks.outputs.full == 'true'",
        "macos:",
        "needs: checks",
        "runs-on: macos-latest",
        "required:",
        "if: always()",
        "needs: [checks, test, macos]",
        *required_step_fragments,
    )
    required_release = (
        'tags: ["v*"]',
        "fetch-depth: 0",
        "uv run --no-sync python scripts/audit_reachable_history.py --ref HEAD",
    )
    for fragment in required_ci:
        if fragment not in ci:
            errors.append(f".github/workflows/ci.yml: missing lean-policy fragment: {fragment}")
    for fragment in required_release:
        if fragment not in release:
            errors.append(
                f".github/workflows/release.yml: missing release-policy fragment: {fragment}"
            )
    errors.extend(check_release_pipeline(release))
    errors.extend(check_package_publish_pipeline(publish_testpypi, index="testpypi"))
    errors.extend(check_package_publish_pipeline(publish_pypi, index="pypi"))
    if "paths-ignore:" in ci:
        errors.append(
            ".github/workflows/ci.yml: ancestry audit must not skip documentation-only refs"
        )
    if "hosted_macos" in ci:
        errors.append(
            ".github/workflows/ci.yml: public full-scope macos must not be dispatch-gated"
        )

    checks_job = _yaml_block(ci, "checks:", indent=2)
    scope_step = _yaml_step_with_id(checks_job or "", "scope")
    if checks_job is None or scope_step is None:
        errors.append(".github/workflows/ci.yml: requires one unambiguous scope step")
    else:
        if not _exact_mapping(
            checks_job,
            indent=4,
            expected={
                "runs-on": "ubuntu-latest",
                "timeout-minutes": "10",
                "outputs": "",
                "steps": "",
            },
        ):
            errors.append(
                ".github/workflows/ci.yml: checks job must use only its canonical direct keys"
            )
        checks_outputs = _yaml_block(checks_job, "outputs:", indent=4)
        if checks_outputs is None or not _exact_mapping(
            checks_outputs,
            indent=6,
            expected={"full": "${{ steps.scope.outputs.full }}"},
        ):
            errors.append(
                ".github/workflows/ci.yml: checks outputs must bind exactly to the scope step"
            )
        scope_condition = (
            'elif git diff --quiet "${BASE_SHA}" HEAD -- . '
            "':(exclude)docs/**' ':(exclude)**/*.md' "
            "':(top,glob,exclude)*.md' ':(exclude)LICENSE'; then"
        )
        expected_scope_step = "\n".join(
            (
                "      - name: preserve the documentation-only compute boundary",
                "        id: scope",
                "        env:",
                "          BASE_SHA: ${{ github.event_name == 'pull_request' "
                "&& github.event.pull_request.base.sha || github.event.before }}",
                "        run: |",
                '          if [ "${GITHUB_EVENT_NAME}" = "workflow_dispatch" ]; then',
                '            echo "full=true" >> "${GITHUB_OUTPUT}"',
                f"          {scope_condition}",
                '            echo "full=false" >> "${GITHUB_OUTPUT}"',
                "          else",
                '            echo "full=true" >> "${GITHUB_OUTPUT}"',
                "          fi",
            )
        )
        if scope_step != expected_scope_step:
            errors.append(
                ".github/workflows/ci.yml: scope step must exactly match the reviewed "
                "fail-closed classifier"
            )

    required_job = _yaml_block(ci, "required:", indent=2)
    required_step = _yaml_block(
        required_job or "", "- name: enforce the complete required CI result", indent=6
    )
    if required_job is None or required_step is None:
        errors.append(".github/workflows/ci.yml: requires one named aggregate enforcement step")
    else:
        job_entries = _canonical_yaml_direct_entries(required_job, indent=4)
        step_entries = _canonical_yaml_direct_entries(required_step, indent=8)
        env_block = _yaml_block(required_step, "env:", indent=8)
        env_entries = _canonical_yaml_direct_entries(env_block or "", indent=10)
        expected_job_keys = {"if", "needs", "runs-on", "timeout-minutes", "steps"}
        expected_step_keys = {"env", "run"}
        if (
            job_entries is None
            or [key for key, _ in job_entries] != list(dict.fromkeys(key for key, _ in job_entries))
            or not {key for key, _ in job_entries}.issubset(expected_job_keys)
        ):
            errors.append(
                ".github/workflows/ci.yml: aggregate job must use only its canonical direct keys"
            )
            job_entries = []
        if (
            step_entries is None
            or [key for key, _ in step_entries]
            != list(dict.fromkeys(key for key, _ in step_entries))
            or not {key for key, _ in step_entries}.issubset(expected_step_keys)
        ):
            errors.append(
                ".github/workflows/ci.yml: aggregate enforcement step must use only its "
                "canonical direct keys"
            )
            step_entries = []

        expected_env = {
            "CHECKS_RESULT": "${{ needs.checks.result }}",
            "TEST_RESULT": "${{ needs.test.result }}",
            "MACOS_RESULT": "${{ needs.macos.result }}",
            "FULL_RUN": "${{ needs.checks.outputs.full }}",
        }
        if (
            env_block is None
            or env_entries is None
            or [key for key, _ in env_entries] != list(dict.fromkeys(key for key, _ in env_entries))
            or {key for key, _ in env_entries} != set(expected_env)
            or dict(env_entries) != expected_env
        ):
            errors.append(
                ".github/workflows/ci.yml: aggregate environment must use exactly its "
                "canonical result inputs"
            )

        job_conditions = [value for key, value in job_entries if key == "if"]
        if job_conditions != ["always()"]:
            errors.append(
                ".github/workflows/ci.yml: aggregate job must declare exactly: if: always()"
            )
        if not re.search(r"^    needs: \[checks, test, macos\]\s*$", required_job, re.MULTILINE):
            errors.append(
                ".github/workflows/ci.yml: aggregate job is missing: "
                "needs: [checks, test, macos]"
            )
        for fragment in required_step_fragments:
            if fragment not in required_step:
                errors.append(
                    ".github/workflows/ci.yml: aggregate enforcement step is missing: "
                    f"{fragment}"
                )

    macos_job = _yaml_block(ci, "macos:", indent=2)
    if macos_job is None:
        errors.append(".github/workflows/ci.yml: requires one unambiguous macos job")
    else:
        macos_entries = _canonical_yaml_direct_entries(macos_job, indent=4)
        expected_macos_keys = {"needs", "if", "runs-on", "timeout-minutes", "steps"}
        if (
            macos_entries is None
            or [key for key, _ in macos_entries]
            != list(dict.fromkeys(key for key, _ in macos_entries))
            or not {key for key, _ in macos_entries}.issubset(expected_macos_keys)
        ):
            errors.append(
                ".github/workflows/ci.yml: macos job must use only its canonical direct keys"
            )
            macos_entries = []
        macos_values = dict(macos_entries)
        expected_macos_values = {
            "needs": "checks",
            "if": "needs.checks.outputs.full == 'true'",
            "runs-on": "macos-latest",
        }
        for key, value in expected_macos_values.items():
            if macos_values.get(key) != value:
                errors.append(
                    f".github/workflows/ci.yml: macos job must declare exactly: {key}: {value}"
                )
        for fragment in (
            "python -m pytest tests -v",
            "the macOS-specific probes actually return data",
            "mem = probes.memory()",
        ):
            if fragment not in macos_job:
                errors.append(f".github/workflows/ci.yml: macos job is missing: {fragment}")
        macos_test_step = _yaml_block(macos_job, "- run: python -m pytest tests -v", indent=6)
        macos_probe_step = _yaml_block(
            macos_job, "- name: the macOS-specific probes actually return data", indent=6
        )
        test_entries = _canonical_yaml_direct_entries(macos_test_step or "", indent=8)
        probe_entries = _canonical_yaml_direct_entries(macos_probe_step or "", indent=8)
        if macos_test_step is None or test_entries != []:
            errors.append(
                ".github/workflows/ci.yml: macos test step must be exact and unconditional"
            )
        if (
            macos_probe_step is None
            or probe_entries is None
            or [key for key, _ in probe_entries]
            != list(dict.fromkeys(key for key, _ in probe_entries))
            or dict(probe_entries) != {"run": "|"}
        ):
            errors.append(
                ".github/workflows/ci.yml: macos probe step must be exact and unconditional"
            )
    return errors


def check_billing_privacy(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / "docs" / "adrs" / "0018-budget-hosted-ci.md"
    text = _read(path, errors)
    for pattern in PRIVATE_BILLING_RE:
        if pattern.search(text):
            errors.append(
                f"{path.relative_to(root).as_posix()}: contains exact private billing data"
            )
            break
    return errors


def _git(root: Path, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def check_release_commit(root: Path, ref: str) -> list[str]:
    errors: list[str] = []
    status, output, stderr = _git(root, "show", "-s", "--format=%ae%x00%ce", ref)
    if status:
        detail = stderr.strip() or "unknown Git error"
        return [f"release identity: cannot inspect commit {ref}: {detail}"]
    fields = output.rstrip("\n").split("\x00")
    if len(fields) != 2:
        return [f"release identity: malformed metadata for commit {ref}"]
    author_email, committer_email = fields
    if author_email != EXPECTED_RELEASE_AUTHOR_EMAIL:
        errors.append(f"release identity: commit {ref} does not use the maintainer no-reply author")
    if committer_email not in ALLOWED_RELEASE_COMMITTER_EMAILS:
        errors.append(f"release identity: commit {ref} has an unapproved committer identity")
    return errors


def check_release_tag(root: Path, tag: str) -> list[str]:
    errors: list[str] = []
    status, object_type, stderr = _git(root, "cat-file", "-t", tag)
    if status:
        detail = stderr.strip() or "unknown Git error"
        return [f"release identity: cannot inspect tag {tag}: {detail}"]
    if object_type.strip() != "tag":
        return [f"release identity: {tag} is not an annotated tag"]

    status, tag_object, stderr = _git(root, "cat-file", "-p", tag)
    if status:
        detail = stderr.strip() or "unknown Git error"
        return [f"release identity: cannot read tag {tag}: {detail}"]
    match = re.search(r"^tagger .* <([^<>]+)> \d+ [+-]\d{4}$", tag_object, re.MULTILINE)
    if match is None:
        errors.append(f"release identity: annotated tag {tag} has no parseable tagger")
    elif match.group(1) != EXPECTED_RELEASE_AUTHOR_EMAIL:
        errors.append(f"release identity: tag {tag} does not use the maintainer no-reply tagger")

    status, commit, stderr = _git(root, "rev-parse", "--verify", f"{tag}^{{commit}}")
    if status:
        detail = stderr.strip() or "unknown Git error"
        errors.append(f"release identity: cannot peel tag {tag}: {detail}")
    else:
        errors.extend(check_release_commit(root, commit.strip()))
    return errors


def verify_repository(root: Path) -> list[str]:
    root = root.resolve()
    errors = []
    errors.extend(check_private_ignores(root))
    errors.extend(check_workflows(root))
    errors.extend(check_lean_policy(root))
    errors.extend(check_billing_privacy(root))
    return sorted(set(errors))


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--release-commit", metavar="REF")
    group.add_argument("--release-tag", metavar="TAG")
    return parser.parse_args(argv[1:])


def main(argv: Sequence[str]) -> int:
    args = _parse_args(argv)
    root = args.root
    errors = verify_repository(root)
    if args.release_commit:
        errors.extend(check_release_commit(root.resolve(), args.release_commit))
    if args.release_tag:
        errors.extend(check_release_tag(root.resolve(), args.release_tag))
    if errors:
        for error in errors:
            print(f"public-readiness policy: {error}", file=sys.stderr)
        return 1
    checked = "private boundaries, immutable actions, lean CI"
    if args.release_commit:
        checked += ", release commit identity"
    if args.release_tag:
        checked += ", annotated release identity"
    print(f"public-readiness policy passed: {checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
