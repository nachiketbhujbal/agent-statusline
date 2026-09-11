#!/usr/bin/env python3
"""Verify distribution privacy and installed-renderer evidence placement."""

import pathlib
import sys
import tarfile
import zipfile

FORBIDDEN_PARTS = {".git", ".pvt", ".worktrees", "__pycache__"}
EVIDENCE_SUFFIXES = (
    "tests/fixture_payload.py",
    "tests/fixtures/statusline-payload.json",
    "tests/fixtures/statusline-transcript.jsonl",
)


def archive_names(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            return archive.getnames()
    raise ValueError(f"unsupported distribution archive: {path}")


def unsafe_name(name):
    path = pathlib.PurePosixPath(name)
    return (
        path.is_absolute() or ".." in path.parts or bool(FORBIDDEN_PARTS.intersection(path.parts))
    )


def verify(paths):
    failures = []
    for path in paths:
        names = archive_names(path)
        unsafe = sorted(name for name in names if unsafe_name(name))
        if unsafe:
            failures.append(f"{path}: forbidden archive members: {unsafe}")
        evidence = {
            suffix: [name for name in names if name == suffix or name.endswith("/" + suffix)]
            for suffix in EVIDENCE_SUFFIXES
        }
        if str(path).endswith(".whl"):
            leaked = sorted(name for matches in evidence.values() for name in matches)
            if leaked:
                failures.append(f"{path}: test evidence leaked into wheel: {leaked}")
        else:
            missing = sorted(suffix for suffix, matches in evidence.items() if not matches)
            if missing:
                failures.append(f"{path}: source evidence missing: {missing}")
    if failures:
        raise ValueError("\n".join(failures))


def main(argv=None):
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        print("usage: verify_artifacts.py <wheel-or-sdist> [...]", file=sys.stderr)
        return 2
    try:
        verify(paths)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"artifact evidence and privacy verified: {', '.join(paths)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
