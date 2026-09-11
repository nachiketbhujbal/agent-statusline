#!/usr/bin/env python3
"""Verify tracked documentation relationships without third-party dependencies."""

import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from urllib.parse import unquote

EXCLUDED_PARTS = {".git", ".pvt", ".worktrees", ".venv", "__pycache__"}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
REFERENCE_TARGET_RE = re.compile(
    r"^[ \t]{0,3}\[(?!\^)[^\]\n]+\]:[ \t]*(?:\n[ \t]+)?(<[^>\n]+>|[^\s]+)",
    re.MULTILINE,
)
ADR_FILE_RE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
ADR_ROW_RE = re.compile(r"^\| \[(\d{4})\]\(([^)#]+\.md)\) \|", re.MULTILINE)
VERSION_RE = r"0\.\d+\.\d+"

GOVERNANCE_PATHS = (
    Path("AGENTS.md"),
    Path("HANDOFF.md"),
    Path("docs/RESEARCH.md"),
    Path("docs/adrs/0026-coordinate-one-owner-and-one-reviewer.md"),
)

PRIVATE_PATTERNS: Sequence[tuple[re.Pattern, str]] = (
    (re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)"), "machine home path"),
    (re.compile(r"(?:^|[^A-Za-z0-9_-])\.pvt(?:/|\b)"), "private workspace path"),
    (re.compile(r"\bagent-relay(?:/|\b)", re.IGNORECASE), "private coordination path"),
    (
        re.compile(r"\bsession[_ -]?id\s*[:=]\s*[`\"']?[A-Za-z0-9_-]{8,}", re.IGNORECASE),
        "concrete session identifier",
    ),
    (
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
        "UUID-shaped private identifier",
    ),
    (
        re.compile(r"\baccount (?:balance|allowance|ledger)\s*[:=]\s*\$?\d", re.IGNORECASE),
        "account value",
    ),
    (
        re.compile(r"\b(?:user|system|assistant) prompt\s*:", re.IGNORECASE),
        "prompt transcript",
    ),
)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def markdown_files(root: Path) -> list[Path]:
    """Return public Markdown files in deterministic order."""
    files = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if not any(part in EXCLUDED_PARTS for part in relative.parts):
            files.append(path)
    return sorted(files)


def _link_target(raw: str) -> str:
    candidate = raw.strip()
    if candidate.startswith("<") and ">" in candidate:
        return candidate[1 : candidate.index(">")]
    return candidate.split(maxsplit=1)[0]


def _markdown_targets(text: str) -> Iterable[str]:
    for match in LINK_RE.finditer(text):
        yield _link_target(match.group(1))
    for match in REFERENCE_TARGET_RE.finditer(text):
        yield _link_target(match.group(1))


def check_relative_links(root: Path, files: Iterable[Path]) -> list[str]:
    errors = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for target in _markdown_targets(text):
            if not target or target.startswith("#") or target.startswith("//"):
                continue
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            clean_target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not clean_target:
                continue
            resolved = (path.parent / clean_target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(
                    f"{_relative(path, root)}: relative link escapes repository: {target}"
                )
                continue
            if not resolved.exists():
                errors.append(f"{_relative(path, root)}: missing relative link target: {target}")
    return errors


def _reserved_adrs(index_text: str) -> set[str]:
    match = re.search(r"Reserved but not yet accepted:\s*([0-9, ]+)\.", index_text)
    if not match:
        return set()
    return {value.strip() for value in match.group(1).split(",") if value.strip()}


def check_adr_index(root: Path) -> list[str]:
    errors = []
    adr_dir = root / "docs" / "adrs"
    index_path = adr_dir / "README.md"
    if not index_path.is_file():
        return ["docs/adrs/README.md: missing ADR index"]

    files_by_id: dict[str, str] = {}
    for path in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        match = ADR_FILE_RE.match(path.name)
        if not match:
            errors.append(f"docs/adrs/{path.name}: invalid ADR filename")
            continue
        adr_id = match.group(1)
        if adr_id in files_by_id:
            errors.append(f"docs/adrs: duplicate ADR number {adr_id}")
        files_by_id[adr_id] = path.name

    index_text = index_path.read_text(encoding="utf-8")
    index_rows = ADR_ROW_RE.findall(index_text)
    index_ids = [adr_id for adr_id, _filename in index_rows]
    if index_ids != sorted(index_ids):
        errors.append("docs/adrs/README.md: ADR rows are not in numeric order")
    indexed_by_id: dict[str, str] = {}
    for adr_id, filename in index_rows:
        if adr_id in indexed_by_id:
            errors.append(f"docs/adrs/README.md: duplicate ADR row {adr_id}")
        indexed_by_id[adr_id] = filename

    if indexed_by_id != files_by_id:
        for adr_id in sorted(set(files_by_id) - set(indexed_by_id)):
            errors.append(f"docs/adrs/README.md: ADR {adr_id} is not indexed")
        for adr_id in sorted(set(indexed_by_id) - set(files_by_id)):
            errors.append(f"docs/adrs/README.md: ADR {adr_id} has no file")
        for adr_id in sorted(set(files_by_id) & set(indexed_by_id)):
            if files_by_id[adr_id] != indexed_by_id[adr_id]:
                errors.append(
                    f"docs/adrs/README.md: ADR {adr_id} points to {indexed_by_id[adr_id]}, "
                    f"expected {files_by_id[adr_id]}"
                )

    if files_by_id:
        largest = max(int(value) for value in files_by_id)
        gaps = {f"{value:04d}" for value in range(1, largest + 1)} - set(files_by_id)
        reserved = _reserved_adrs(index_text)
        if gaps != reserved:
            errors.append(
                "docs/adrs/README.md: numeric gaps must exactly match the reserved ADR list "
                f"(gaps={sorted(gaps)}, reserved={sorted(reserved)})"
            )

    return errors


def _release_rows(roadmap: str) -> list[tuple[str, str]]:
    return re.findall(
        rf"^\| ({VERSION_RE}) \| [^|]+ \| (\*\*Current\*\*|\*\*Released\*\*|Planned[^|]*) \|$",
        roadmap,
        re.MULTILINE,
    )


def _version_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def check_release_agreement(root: Path) -> list[str]:
    errors = []
    required = {
        "roadmap": root / "docs" / "ROADMAP.md",
        "changelog": root / "docs" / "CHANGELOG.md",
        "review": root / "docs" / "CODE_REVIEW.md",
        "handoff": root / "HANDOFF.md",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        return [f"release agreement: missing {name}" for name in missing]

    texts = {name: path.read_text(encoding="utf-8") for name, path in required.items()}
    rows = _release_rows(texts["roadmap"])
    current = [version for version, status in rows if status == "**Current**"]
    if len(current) != 1:
        return [f"docs/ROADMAP.md: expected one Current release, found {current}"]
    current_version = current[0]

    changelog_match = re.search(
        rf"^## Unreleased — ({VERSION_RE})$", texts["changelog"], re.MULTILINE
    )
    if not changelog_match or changelog_match.group(1) != current_version:
        errors.append(
            f"docs/CHANGELOG.md: Unreleased version must be current release {current_version}"
        )
    if f"| {current_version} |" not in texts["review"]:
        errors.append(f"docs/CODE_REVIEW.md: no finding records current release {current_version}")
    if f"- Current release target: {current_version}," not in texts["handoff"]:
        errors.append(f"HANDOFF.md: current release target must be {current_version}")

    released = [version for version, status in rows if status == "**Released**"]
    preceding = max(
        (version for version in released if _version_key(version) < _version_key(current_version)),
        key=_version_key,
        default=None,
    )
    if preceding is None:
        errors.append("docs/ROADMAP.md: current release has no preceding released version")
    else:
        if f"- Preceding release: v{preceding}," not in texts["handoff"]:
            errors.append(f"HANDOFF.md: preceding release must be v{preceding}")
        if not re.search(rf"^## {re.escape(preceding)}$", texts["changelog"], re.MULTILINE):
            errors.append(f"docs/CHANGELOG.md: missing preceding release {preceding}")
    return errors


def check_review_governance(root: Path) -> list[str]:
    errors = []
    agents_path = root / "AGENTS.md"
    adr_path = root / "docs" / "adrs" / "0026-coordinate-one-owner-and-one-reviewer.md"
    handoff_path = root / "HANDOFF.md"
    for path in (agents_path, adr_path, handoff_path):
        if not path.is_file():
            errors.append(f"{_relative(path, root)}: missing governance record")
    if errors:
        return errors

    agents = re.sub(r"\s+", " ", agents_path.read_text(encoding="utf-8").lower())
    adr = re.sub(r"\s+", " ", adr_path.read_text(encoding="utf-8").lower())
    handoff = handoff_path.read_text(encoding="utf-8")
    required_agents = (
        "exactly one branch owner",
        "at most one independent reviewer may be active at a time",
        "does not commit to or check out the owner's worktree",
        "applies corrections",
        "requires a renewed exact-sha review",
    )
    required_adr = (
        "exactly one branch owner and one independent reviewer",
        "at most one independent reviewer is active at a time",
        "the reviewer does not further delegate",
        "the owner alone changes the release branch and applies corrections",
        "requires a renewed exact-sha review",
    )
    for phrase in required_agents:
        if phrase not in agents:
            errors.append(f"AGENTS.md: missing review rule: {phrase}")
    for phrase in required_adr:
        if phrase not in adr:
            errors.append(
                "docs/adrs/0026-coordinate-one-owner-and-one-reviewer.md: " f"missing: {phrase}"
            )
    if len(re.findall(r"^- Branch owner: .+$", handoff, re.MULTILINE)) != 1:
        errors.append("HANDOFF.md: expected exactly one branch-owner assignment")
    if len(re.findall(r"^- Reviewer role: .+$", handoff, re.MULTILINE)) != 1:
        errors.append("HANDOFF.md: expected exactly one reviewer-role assignment")
    return errors


def check_governance_privacy(root: Path) -> list[str]:
    errors = []
    for relative in GOVERNANCE_PATHS:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, description in PRIVATE_PATTERNS:
            if pattern.search(text):
                errors.append(f"{relative.as_posix()}: contains {description}")
    return errors


def verify_repository(root: Path) -> list[str]:
    root = root.resolve()
    errors = []
    files = markdown_files(root)
    errors.extend(check_relative_links(root, files))
    errors.extend(check_adr_index(root))
    errors.extend(check_release_agreement(root))
    errors.extend(check_review_governance(root))
    errors.extend(check_governance_privacy(root))
    return sorted(set(errors))


def main(argv: Sequence[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    errors = verify_repository(root)
    if errors:
        for error in errors:
            print(f"documentation policy: {error}", file=sys.stderr)
        return 1
    print(f"documentation policy passed: {len(markdown_files(root.resolve()))} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
