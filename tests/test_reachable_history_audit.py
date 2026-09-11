import os
import subprocess
import sys
from pathlib import Path

AUDIT = Path(__file__).parents[1] / "scripts" / "audit_reachable_history.py"
NO_REPLY = "17068914+nachiketbhujbal@users.noreply.github.com"


def git(root, *args, input_text=None, env=None):
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        input=input_text,
        env=env,
    )


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def repository(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Release Maintainer")
    git(tmp_path, "config", "user.email", NO_REPLY)
    write(tmp_path / "README.md", "# Clean repository\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "clean root")
    git(tmp_path, "tag", "-a", "v0.2.12", "-m", "release")
    return tmp_path


def run_audit(root, *args):
    return subprocess.run(
        [sys.executable, str(AUDIT), *args, str(root)],
        capture_output=True,
        text=True,
    )


def test_reachable_history_audit_accepts_clean_refs(tmp_path):
    root = repository(tmp_path)

    result = run_audit(root)

    assert result.returncode == 0, result.stderr


def test_reachable_history_audit_rejects_personal_commit_identity(tmp_path):
    root = repository(tmp_path)
    git(root, "config", "user.email", "maintainer@example.com")
    write(root / "README.md", "changed\n")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "personal identity")

    result = run_audit(root)

    assert result.returncode == 1
    assert "author email is not an approved no-reply identity" in result.stderr


def test_reachable_history_audit_rejects_private_billing_blob(tmp_path):
    root = repository(tmp_path)
    path = root / "docs" / "adrs" / "0018-budget-hosted-ci.md"
    private_measurement = "The run consumed " + "12.5 percent" + " of the allowance.\n"
    write(path, private_measurement)
    git(root, "add", path.relative_to(root).as_posix())
    git(root, "commit", "-m", "private measurement")

    result = run_audit(root)

    assert result.returncode == 1
    assert "contains exact private billing evidence" in result.stderr


def test_reachable_history_audit_rejects_private_path(tmp_path):
    root = repository(tmp_path)
    write(root / ".pvt" / "record.md", "private\n")
    git(root, "add", "-f", ".pvt/record.md")
    git(root, "commit", "-m", "private path")

    result = run_audit(root)

    assert result.returncode == 1
    assert "contains private component .pvt" in result.stderr


def test_reachable_history_audit_rejects_oversized_blob_instead_of_skipping_it(tmp_path):
    root = repository(tmp_path)
    write(root / "oversized.txt", "x" * (2 * 1024 * 1024 + 1))
    git(root, "add", "oversized.txt")
    git(root, "commit", "-m", "oversized evidence")

    result = run_audit(root)

    assert result.returncode == 1
    assert "exceeds 2097152-byte audit limit" in result.stderr


def test_reachable_history_audit_ignores_unreferenced_commit_objects(tmp_path):
    root = repository(tmp_path)
    tree = git(root, "write-tree").stdout.strip()
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Old Maintainer",
            "GIT_AUTHOR_EMAIL": "old@example.com",
            "GIT_COMMITTER_NAME": "Old Maintainer",
            "GIT_COMMITTER_EMAIL": "old@example.com",
        }
    )
    git(root, "commit-tree", tree, input_text="unreferenced\n", env=environment)

    result = run_audit(root)

    assert result.returncode == 0, result.stderr


def test_explicit_ref_audits_only_its_complete_ancestry(tmp_path):
    root = repository(tmp_path)
    git(root, "config", "user.email", "maintainer@example.com")
    write(root / "README.md", "personal descendant\n")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "personal descendant")

    clean_result = run_audit(root, "--ref", "v0.2.12")
    descendant_result = run_audit(root, "--ref", "HEAD")

    assert clean_result.returncode == 0, clean_result.stderr
    assert descendant_result.returncode == 1
    assert "author email is not an approved no-reply identity" in descendant_result.stderr


def test_explicit_ref_rejects_unknown_ref(tmp_path):
    root = repository(tmp_path)

    result = run_audit(root, "--ref", "refs/heads/missing")

    assert result.returncode == 2
    assert "unknown revision" in result.stderr
