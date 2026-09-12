#!/usr/bin/env python3
"""Identify and verify the one exact release artifact pair."""

import argparse
import hashlib
import re
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
ARTIFACT_NAME_RE = re.compile(r"^release-distributions-[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WHEEL_RE = re.compile(r"^agent_statusline-(\d+\.\d+\.\d+)-py3-none-any\.whl$")
SDIST_RE = re.compile(r"^agent_statusline-(\d+\.\d+\.\d+)\.tar\.gz$")


class DistributionPair(NamedTuple):
    wheel: Path
    sdist: Path
    wheel_sha256: str
    sdist_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_entries(directory: Path) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"release directory is not a regular directory: {directory}")
    entries = sorted(directory.iterdir(), key=lambda path: path.name)
    for path in entries:
        mode = path.lstat().st_mode
        if path.is_symlink() or not stat.S_ISREG(mode):
            raise ValueError(f"release directory contains a non-regular entry: {path.name}")
    return entries


def _expected_pair(directory: Path, version: str) -> DistributionPair:
    wheel = directory / f"agent_statusline-{version}-py3-none-any.whl"
    sdist = directory / f"agent_statusline-{version}.tar.gz"
    entries = _regular_entries(directory)
    expected = [wheel, sdist]
    if entries != sorted(expected, key=lambda path: path.name):
        names = [path.name for path in entries]
        raise ValueError(f"expected exactly the v{version} wheel and sdist, found: {names}")
    return DistributionPair(wheel, sdist, _sha256(wheel), _sha256(sdist))


def _append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as destination:
        destination.write(text)


def prepare(args: argparse.Namespace) -> None:
    match = TAG_RE.fullmatch(args.tag)
    if match is None:
        raise ValueError(f"release tag must be exact vMAJOR.MINOR.PATCH: {args.tag!r}")
    if ARTIFACT_NAME_RE.fullmatch(args.artifact_name) is None:
        raise ValueError(
            "artifact name must bind release-distributions to the exact 40-character commit SHA"
        )

    pair = _expected_pair(args.directory, match.group(1))
    outputs = {
        "artifact_name": args.artifact_name,
        "wheel_name": pair.wheel.name,
        "wheel_sha256": pair.wheel_sha256,
        "sdist_name": pair.sdist.name,
        "sdist_sha256": pair.sdist_sha256,
    }
    _append(args.github_output, "".join(f"{key}={value}\n" for key, value in outputs.items()))
    _append(
        args.github_summary,
        "## Release distributions\n\n"
        f"- `{pair.wheel.name}` — `sha256:{pair.wheel_sha256}`\n"
        f"- `{pair.sdist.name}` — `sha256:{pair.sdist_sha256}`\n",
    )
    print(f"identified exact v{match.group(1)} release pair: {pair.wheel.name}, {pair.sdist.name}")


def _version_from_names(wheel_name: str, sdist_name: str) -> str:
    wheel_match = WHEEL_RE.fullmatch(wheel_name)
    sdist_match = SDIST_RE.fullmatch(sdist_name)
    if wheel_match is None or sdist_match is None:
        raise ValueError("release filenames do not match the exact wheel and sdist contracts")
    if wheel_match.group(1) != sdist_match.group(1):
        raise ValueError("release wheel and sdist versions do not agree")
    return wheel_match.group(1)


def verify(args: argparse.Namespace) -> None:
    if SHA256_RE.fullmatch(args.wheel_sha256) is None:
        raise ValueError("expected wheel SHA-256 is malformed")
    if SHA256_RE.fullmatch(args.sdist_sha256) is None:
        raise ValueError("expected sdist SHA-256 is malformed")
    version = _version_from_names(args.wheel_name, args.sdist_name)
    pair = _expected_pair(args.directory, version)
    if pair.wheel_sha256 != args.wheel_sha256:
        raise ValueError("downloaded wheel SHA-256 does not match the build job")
    if pair.sdist_sha256 != args.sdist_sha256:
        raise ValueError("downloaded sdist SHA-256 does not match the build job")
    print(f"verified exact v{version} release pair and SHA-256 identities")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--directory", required=True, type=Path)
    prepare_parser.add_argument("--tag", required=True)
    prepare_parser.add_argument("--artifact-name", required=True)
    prepare_parser.add_argument("--github-output", required=True, type=Path)
    prepare_parser.add_argument("--github-summary", required=True, type=Path)
    prepare_parser.set_defaults(handler=prepare)

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--directory", required=True, type=Path)
    verify_parser.add_argument("--wheel-name", required=True)
    verify_parser.add_argument("--wheel-sha256", required=True)
    verify_parser.add_argument("--sdist-name", required=True)
    verify_parser.add_argument("--sdist-sha256", required=True)
    verify_parser.set_defaults(handler=verify)
    return parser


def main(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv[1:])
    try:
        args.handler(args)
    except (OSError, ValueError) as error:
        print(f"release artifacts: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
