#!/usr/bin/env python3
"""Verify static repository boundaries needed before public visibility."""

import argparse
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
        match = re.fullmatch(r"([a-z][a-z0-9-]*):(?:\s+(.*))?", content)
        if match is None:
            return None
        entries.append((match.group(1), match.group(2) or ""))
    return entries


def check_lean_policy(root: Path) -> list[str]:
    errors: list[str] = []
    ci = _read(root / ".github" / "workflows" / "ci.yml", errors)
    release = _read(root / ".github" / "workflows" / "release.yml", errors)
    required_ci = (
        "pull_request:",
        "workflow_dispatch:",
        "hosted_macos:",
        "if: github.event_name == 'workflow_dispatch' && inputs.hosted_macos",
        "contents: read",
        "fetch-depth: 0",
        "python scripts/audit_reachable_history.py --ref HEAD",
        'git diff --quiet "${BASE_SHA}" HEAD --',
        "if: needs.checks.outputs.full == 'true'",
        "required:",
        "if: always()",
        "needs: [checks, test]",
        "CHECKS_RESULT: ${{ needs.checks.result }}",
        "TEST_RESULT: ${{ needs.test.result }}",
        "FULL_RUN: ${{ needs.checks.outputs.full }}",
        "set -eu",
        'test "${CHECKS_RESULT}" = "success"',
        'if [ "${FULL_RUN}" = "true" ]; then',
        'elif [ "${FULL_RUN}" = "false" ]; then',
        'test "${TEST_RESULT}" = "success"',
        'test "${TEST_RESULT}" = "skipped"',
        'echo "invalid full-scope result: ${FULL_RUN}" >&2',
        "exit 1",
    )
    required_release = (
        'tags: ["v*"]',
        "contents: write",
        "fetch-depth: 0",
        "python scripts/audit_reachable_history.py --ref HEAD",
    )
    for fragment in required_ci:
        if fragment not in ci:
            errors.append(f".github/workflows/ci.yml: missing lean-policy fragment: {fragment}")
    for fragment in required_release:
        if fragment not in release:
            errors.append(
                f".github/workflows/release.yml: missing release-policy fragment: {fragment}"
            )
    if "paths-ignore:" in ci:
        errors.append(
            ".github/workflows/ci.yml: ancestry audit must not skip documentation-only refs"
        )

    checks_job = _yaml_block(ci, "checks:", indent=2)
    scope_step = _yaml_step_with_id(checks_job or "", "scope")
    if checks_job is None or scope_step is None:
        errors.append(".github/workflows/ci.yml: requires one unambiguous scope step")
    else:
        for output in (
            'echo "full=true" >> "${GITHUB_OUTPUT}"',
            'echo "full=false" >> "${GITHUB_OUTPUT}"',
        ):
            if output not in scope_step:
                errors.append(f".github/workflows/ci.yml: scope step must emit: {output}")

    required_job = _yaml_block(ci, "required:", indent=2)
    required_step = _yaml_block(
        required_job or "", "- name: enforce the complete required CI result", indent=6
    )
    if required_job is None or required_step is None:
        errors.append(".github/workflows/ci.yml: requires one named aggregate enforcement step")
    else:
        job_entries = _canonical_yaml_direct_entries(required_job, indent=4)
        step_entries = _canonical_yaml_direct_entries(required_step, indent=8)
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

        job_conditions = [value for key, value in job_entries if key == "if"]
        if job_conditions != ["always()"]:
            errors.append(
                ".github/workflows/ci.yml: aggregate job must declare exactly: if: always()"
            )
        if not re.search(r"^    needs: \[checks, test\]\s*$", required_job, re.MULTILINE):
            errors.append(
                ".github/workflows/ci.yml: aggregate job is missing: needs: [checks, test]"
            )
        for fragment in required_ci[12:]:
            if fragment not in required_step:
                errors.append(
                    ".github/workflows/ci.yml: aggregate enforcement step is missing: "
                    f"{fragment}"
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
