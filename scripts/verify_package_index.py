#!/usr/bin/env python3
"""Verify that a package index exposes one exact release artifact pair."""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import NamedTuple, Optional

INDEX_JSON_BASES = {
    "pypi": "https://pypi.org/pypi",
    "testpypi": "https://test.pypi.org/pypi",
}
MAX_RESPONSE_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ExpectedFile(NamedTuple):
    filename: str
    sha256: str
    package_type: str


def _normalized_project(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _release_url(index: str, project: str, version: str) -> str:
    base = INDEX_JSON_BASES[index]
    return "/".join(
        (
            base,
            urllib.parse.quote(project, safe=""),
            urllib.parse.quote(version, safe=""),
            "json",
        )
    )


def _request_json(url: str, timeout_seconds: float) -> object:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "agent-statusline-release-verifier/1"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("package-index response exceeds the one-MiB limit")
    return json.loads(body)


def _expected_files(args: argparse.Namespace) -> tuple[ExpectedFile, ExpectedFile]:
    expected = (
        ExpectedFile(args.wheel_name, args.wheel_sha256, "bdist_wheel"),
        ExpectedFile(args.sdist_name, args.sdist_sha256, "sdist"),
    )
    for item in expected:
        if not item.filename or "/" in item.filename or "\\" in item.filename:
            raise ValueError("expected distribution filename must be a plain basename")
        if SHA256_RE.fullmatch(item.sha256) is None:
            raise ValueError(f"expected SHA-256 is malformed for {item.filename}")
    if expected[0].filename == expected[1].filename:
        raise ValueError("wheel and source distribution filenames must differ")
    return expected


def validate_release(
    payload: object,
    *,
    project: str,
    version: str,
    expected: Sequence[ExpectedFile],
) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("package-index response is not an object")
    info = payload.get("info")
    if not isinstance(info, Mapping):
        raise ValueError("package-index response lacks release metadata")
    if _normalized_project(str(info.get("name", ""))) != _normalized_project(project):
        raise ValueError("package-index project identity does not match")
    if info.get("version") != version:
        raise ValueError("package-index version does not match")

    urls = payload.get("urls")
    if not isinstance(urls, list):
        raise ValueError("package-index response lacks distribution files")
    observed: dict[str, Mapping[object, object]] = {}
    for item in urls:
        if not isinstance(item, Mapping):
            raise ValueError("package-index distribution entry is malformed")
        filename = item.get("filename")
        if not isinstance(filename, str) or filename in observed:
            raise ValueError("package-index distribution filenames are malformed or duplicated")
        observed[filename] = item

    expected_names = {item.filename for item in expected}
    if set(observed) != expected_names:
        raise ValueError("package index does not expose exactly the expected release pair")
    for wanted in expected:
        item = observed[wanted.filename]
        digests = item.get("digests")
        if not isinstance(digests, Mapping) or digests.get("sha256") != wanted.sha256:
            raise ValueError(f"package-index SHA-256 does not match for {wanted.filename}")
        if item.get("packagetype") != wanted.package_type:
            raise ValueError(f"package-index type does not match for {wanted.filename}")


def verify_with_retries(
    *,
    index: str,
    project: str,
    version: str,
    expected: Sequence[ExpectedFile],
    attempts: int,
    delay_seconds: float,
    timeout_seconds: float,
) -> None:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    if delay_seconds < 0 or timeout_seconds <= 0:
        raise ValueError("retry delay must be nonnegative and timeout must be positive")

    url = _release_url(index, project, version)
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            payload = _request_json(url, timeout_seconds)
            validate_release(payload, project=project, version=version, expected=expected)
            return
        except (OSError, ValueError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(delay_seconds)
    raise ValueError(
        f"package-index evidence did not converge after {attempts} attempts: {last_error}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, choices=sorted(INDEX_JSON_BASES))
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--wheel-name", required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--sdist-name", required=True)
    parser.add_argument("--sdist-sha256", required=True)
    parser.add_argument("--attempts", required=True, type=int)
    parser.add_argument("--delay-seconds", required=True, type=float)
    parser.add_argument("--timeout-seconds", required=True, type=float)
    return parser


def main(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv[1:])
    try:
        expected = _expected_files(args)
        verify_with_retries(
            index=args.index,
            project=args.project,
            version=args.version,
            expected=expected,
            attempts=args.attempts,
            delay_seconds=args.delay_seconds,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError) as error:
        print(f"package index: {error}", file=sys.stderr)
        return 1
    print(f"verified exact {args.project} {args.version} files and SHA-256 identities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
