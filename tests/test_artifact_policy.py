import io
import subprocess
import sys
import tarfile
import zipfile


def run_policy(*paths):
    return subprocess.run(
        [sys.executable, "scripts/verify_artifacts.py", *(str(path) for path in paths)],
        capture_output=True,
        text=True,
    )


def write_tar(path, names):
    with tarfile.open(path, "w:gz") as archive:
        for name in names:
            info = tarfile.TarInfo(name)
            info.size = 0
            archive.addfile(info, io.BytesIO())


def write_tar_content(path, members):
    with tarfile.open(path, "w:gz") as archive:
        for name, content in members.items():
            payload = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def test_artifact_policy_accepts_expected_wheel_and_sdist_members(tmp_path):
    wheel = tmp_path / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agent_statusline/ledger.py", "")
        archive.writestr("agent_statusline-0.2.5.dist-info/METADATA", "")
    sdist = tmp_path / "package.tar.gz"
    write_tar(
        sdist,
        [
            "agent_statusline-0.2.10/src/ledger.py",
            "agent_statusline-0.2.10/docs/FIELDS.md",
            "agent_statusline-0.2.10/tests/fixture_payload.py",
            "agent_statusline-0.2.10/tests/fixtures/statusline-payload.json",
            "agent_statusline-0.2.10/tests/fixtures/statusline-transcript.jsonl",
        ],
    )

    result = run_policy(wheel, sdist)

    assert result.returncode == 0, result.stderr


def test_artifact_policy_rejects_private_or_worktree_members(tmp_path):
    archive_path = tmp_path / "package.tar.gz"
    write_tar(
        archive_path,
        [
            "agent_statusline-0.2.5/src/ledger.py",
            "agent_statusline-0.2.5/tests/fixture_payload.py",
            "agent_statusline-0.2.5/tests/fixtures/statusline-payload.json",
            "agent_statusline-0.2.5/tests/fixtures/statusline-transcript.jsonl",
            "agent_statusline-0.2.5/.pvt/project/STATUS.md",
            "agent_statusline-0.2.5/.worktrees/codex/src/agent_statusline/ledger.py",
        ],
    )

    result = run_policy(archive_path)

    assert result.returncode == 1
    assert ".pvt" in result.stderr
    assert ".worktrees" in result.stderr


def test_artifact_policy_rejects_missing_sdist_evidence(tmp_path):
    archive_path = tmp_path / "package.tar.gz"
    write_tar(archive_path, ["agent_statusline-0.2.10/src/ledger.py"])

    result = run_policy(archive_path)

    assert result.returncode == 1
    assert "source evidence missing" in result.stderr


def test_artifact_policy_rejects_test_evidence_in_wheel(tmp_path):
    wheel = tmp_path / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agent_statusline/ledger.py", "")
        archive.writestr("tests/fixture_payload.py", "")

    result = run_policy(wheel)

    assert result.returncode == 1
    assert "test evidence leaked into wheel" in result.stderr


def test_artifact_policy_rejects_private_billing_content(tmp_path):
    archive_path = tmp_path / "package.tar.gz"
    private_measurement = "The account used " + "2,000.3 Linux-equivalent" + " minutes.\n"
    write_tar_content(
        archive_path,
        {
            "agent_statusline-0.2.12/tests/fixture_payload.py": "",
            "agent_statusline-0.2.12/tests/fixtures/statusline-payload.json": "",
            "agent_statusline-0.2.12/tests/fixtures/statusline-transcript.jsonl": "",
            "agent_statusline-0.2.12/docs/audit.md": private_measurement,
        },
    )

    result = run_policy(archive_path)

    assert result.returncode == 1
    assert "private billing evidence" in result.stderr


def test_artifact_policy_rejects_oversized_tar_member_instead_of_skipping_it(tmp_path):
    archive_path = tmp_path / "package.tar.gz"
    write_tar_content(
        archive_path,
        {
            "agent_statusline-0.2.13/tests/fixture_payload.py": "",
            "agent_statusline-0.2.13/tests/fixtures/statusline-payload.json": "",
            "agent_statusline-0.2.13/tests/fixtures/statusline-transcript.jsonl": "",
            "agent_statusline-0.2.13/docs/oversized.txt": "x" * (2 * 1024 * 1024 + 1),
        },
    )

    result = run_policy(archive_path)

    assert result.returncode == 1
    assert "exceeds 2097152-byte audit limit" in result.stderr


def test_artifact_policy_rejects_oversized_zip_member_instead_of_skipping_it(tmp_path):
    wheel = tmp_path / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agent_statusline/oversized.txt", b"x" * (2 * 1024 * 1024 + 1))

    result = run_policy(wheel)

    assert result.returncode == 1
    assert "exceeds 2097152-byte audit limit" in result.stderr


def test_artifact_policy_rejects_personal_email_content(tmp_path):
    wheel = tmp_path / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agent_statusline/metadata.txt", "owner@example.outlook.com")

    result = run_policy(wheel)

    assert result.returncode == 0, result.stderr

    with zipfile.ZipFile(wheel, "w") as archive:
        personal_email = "owner@" + "outlook.com"
        archive.writestr("agent_statusline/metadata.txt", personal_email)

    result = run_policy(wheel)

    assert result.returncode == 1
    assert "personal-provider email" in result.stderr
