#!/usr/bin/env python3
"""Audit reachable Git refs for private billing evidence and personal identities."""

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from verify_public_readiness import PRIVATE_BILLING_RE

ALLOWED_EXACT_EMAILS = {
    "17068914+nachiketbhujbal@users.noreply.github.com",
    "noreply@anthropic.com",
    "noreply@github.com",
    "noreply@openai.com",
}
PERSONAL_EMAIL_RE = re.compile(
    rb"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:gmail|outlook)\.com\b", re.IGNORECASE
)
FORBIDDEN_PATH_PARTS = {".claude", ".pvt", ".worktrees"}
PRIVATE_BILLING_PATH = "docs/adrs/0018-budget-hosted-ci.md"
MAX_AUDITED_BLOB = 2 * 1024 * 1024


def _git(root: Path, *args: str, input_text: str = "") -> str:
    result = subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=root,
        input=input_text or None,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or "unknown Git error"
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def published_refs(root: Path) -> list[str]:
    output = _git(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads",
        "refs/remotes/origin",
        "refs/tags",
    )
    return sorted({line for line in output.splitlines() if line and not line.endswith("/HEAD")})


def _email_allowed(email: str) -> bool:
    return email in ALLOWED_EXACT_EMAILS or email.endswith("@users.noreply.github.com")


def check_commit_identities(root: Path, refs: Sequence[str]) -> list[str]:
    errors: list[str] = []
    output = _git(root, "log", "--format=%H%x00%ae%x00%ce", *refs)
    for line in output.splitlines():
        fields = line.split("\x00")
        commit = fields.pop(0) if fields else "unknown"
        if len(fields) != 2:
            errors.append(f"commit {commit}: malformed identity metadata")
            continue
        for role, email in zip(("author", "committer"), fields):
            if not _email_allowed(email):
                errors.append(f"commit {commit}: {role} email is not an approved no-reply identity")
    return errors


def _batch_objects(root: Path, object_ids: Sequence[str]):
    result = subprocess.run(
        ["git", "--no-optional-locks", "cat-file", "--batch"],
        cwd=root,
        input=("\n".join(object_ids) + "\n").encode(),
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip() or "unknown Git error"
        raise ValueError(f"git cat-file --batch failed: {detail}")
    output = result.stdout
    position = 0
    while position < len(output):
        line_end = output.find(b"\n", position)
        if line_end < 0:
            raise ValueError("git cat-file --batch returned a truncated header")
        header = output[position:line_end].decode("ascii", "replace").split()
        position = line_end + 1
        if len(header) != 3:
            raise ValueError("git cat-file --batch returned malformed object metadata")
        object_id, object_type, raw_size = header
        size = int(raw_size)
        content = output[position : position + size]
        position += size + 1
        yield object_id, object_type, content


def check_tag_identities(root: Path) -> list[str]:
    errors: list[str] = []
    output = _git(
        root,
        "for-each-ref",
        "--format=%(refname)%00%(objecttype)%00%(taggeremail)",
        "refs/tags",
    )
    for line in output.splitlines():
        ref, object_type, raw_email = line.split("\x00")
        if object_type != "tag":
            errors.append(f"{ref}: release ref is not an annotated tag")
            continue
        email = raw_email.removeprefix("<").removesuffix(">")
        if not _email_allowed(email):
            errors.append(f"{ref}: tagger email is not an approved no-reply identity")
    return errors


def check_reachable_objects(root: Path, refs: Sequence[str]) -> list[str]:
    errors: list[str] = []
    lines = _git(root, "rev-list", "--objects", *refs).splitlines()
    paths_by_object: dict[str, set[str]] = {}
    for line in lines:
        object_id, separator, path = line.partition(" ")
        paths_by_object.setdefault(object_id, set())
        if separator:
            paths_by_object[object_id].add(path)
            parts = set(PurePosixPath(path).parts)
            forbidden = sorted(parts.intersection(FORBIDDEN_PATH_PARTS))
            if forbidden:
                errors.append(f"reachable path {path}: contains private component {forbidden[0]}")

    for object_id, object_type, content in _batch_objects(root, sorted(paths_by_object)):
        if object_type != "blob":
            continue
        paths = paths_by_object[object_id]
        locations = ", ".join(sorted(paths)) or "unknown path"
        if len(content) > MAX_AUDITED_BLOB:
            errors.append(
                f"blob {object_id} ({locations}): exceeds " f"{MAX_AUDITED_BLOB}-byte audit limit"
            )
            continue
        if b"\x00" in content:
            continue
        if PERSONAL_EMAIL_RE.search(content):
            errors.append(f"blob {object_id} ({locations}): contains a personal-provider email")
        text = content.decode("utf-8", "replace")
        if PRIVATE_BILLING_PATH in paths and any(
            pattern.search(text) for pattern in PRIVATE_BILLING_RE
        ):
            errors.append(
                f"blob {object_id} ({locations}): contains exact private billing evidence"
            )
    return errors


def audit(root: Path, explicit_refs: Sequence[str] = ()) -> list[str]:
    root = root.resolve()
    refs = sorted(set(explicit_refs)) if explicit_refs else published_refs(root)
    if not refs:
        return ["reachable history: no local, origin, or tag refs found"]
    errors = []
    errors.extend(check_commit_identities(root, refs))
    if not explicit_refs:
        errors.extend(check_tag_identities(root))
    errors.extend(check_reachable_objects(root, refs))
    return sorted(set(errors))


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--ref",
        action="append",
        default=[],
        help="audit only this ref and its complete ancestry; may be repeated",
    )
    return parser.parse_args(argv[1:])


def main(argv: Sequence[str]) -> int:
    args = _parse_args(argv)
    try:
        errors = audit(args.root, args.ref)
    except (OSError, ValueError) as error:
        print(f"reachable-history audit: {error}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"reachable-history audit: {error}", file=sys.stderr)
        return 1
    scope = "selected ref ancestry" if args.ref else "published refs"
    print("reachable-history audit passed: " f"{scope}, identities, paths, and private evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
