#!/usr/bin/env python3
"""Fail when a distribution archive contains local or private workspace state."""

import pathlib
import sys
import tarfile
import zipfile

FORBIDDEN_PARTS = {".git", ".pvt", ".worktrees", "__pycache__"}


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
        unsafe = sorted(name for name in archive_names(path) if unsafe_name(name))
        if unsafe:
            failures.append(f"{path}: forbidden archive members: {unsafe}")
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
    print(f"artifact privacy verified: {', '.join(paths)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
