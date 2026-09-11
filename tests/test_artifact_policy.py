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


def test_artifact_policy_accepts_expected_wheel_and_sdist_members(tmp_path):
    wheel = tmp_path / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agent_statusline/ledger.py", "")
        archive.writestr("agent_statusline-0.2.5.dist-info/METADATA", "")
    sdist = tmp_path / "package.tar.gz"
    write_tar(
        sdist, ["agent_statusline-0.2.5/src/ledger.py", "agent_statusline-0.2.5/docs/FIELDS.md"]
    )

    result = run_policy(wheel, sdist)

    assert result.returncode == 0, result.stderr


def test_artifact_policy_rejects_private_or_worktree_members(tmp_path):
    archive_path = tmp_path / "package.tar.gz"
    write_tar(
        archive_path,
        [
            "agent_statusline-0.2.5/src/ledger.py",
            "agent_statusline-0.2.5/.pvt/project/STATUS.md",
            "agent_statusline-0.2.5/.worktrees/codex/src/agent_statusline/ledger.py",
        ],
    )

    result = run_policy(archive_path)

    assert result.returncode == 1
    assert ".pvt" in result.stderr
    assert ".worktrees" in result.stderr
