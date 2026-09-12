import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "release_artifacts.py"
VERSION = "0.3.3"
ARTIFACT_NAME = "release-distributions-" + "a" * 40


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distributions(tmp_path):
    directory = tmp_path / "release-dist"
    directory.mkdir()
    wheel = directory / f"agent_statusline-{VERSION}-py3-none-any.whl"
    sdist = directory / f"agent_statusline-{VERSION}.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    return directory, wheel, sdist


def prepare(tmp_path, directory, **overrides):
    output = tmp_path / "output"
    summary = tmp_path / "summary"
    values = {
        "tag": f"v{VERSION}",
        "artifact_name": ARTIFACT_NAME,
    }
    values.update(overrides)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "prepare",
            "--directory",
            str(directory),
            "--tag",
            values["tag"],
            "--artifact-name",
            values["artifact_name"],
            "--github-output",
            str(output),
            "--github-summary",
            str(summary),
        ],
        capture_output=True,
        text=True,
    )
    return result, output, summary


def verify(directory, wheel, sdist, **overrides):
    values = {
        "wheel_name": wheel.name,
        "wheel_sha256": digest(wheel),
        "sdist_name": sdist.name,
        "sdist_sha256": digest(sdist),
    }
    values.update(overrides)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "verify",
            "--directory",
            str(directory),
            "--wheel-name",
            values["wheel_name"],
            "--wheel-sha256",
            values["wheel_sha256"],
            "--sdist-name",
            values["sdist_name"],
            "--sdist-sha256",
            values["sdist_sha256"],
        ],
        capture_output=True,
        text=True,
    )


def test_prepare_records_exact_names_and_hashes(tmp_path):
    directory, wheel, sdist = distributions(tmp_path)

    result, output, summary = prepare(tmp_path, directory)

    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8").splitlines() == [
        f"artifact_name={ARTIFACT_NAME}",
        f"wheel_name={wheel.name}",
        f"wheel_sha256={digest(wheel)}",
        f"sdist_name={sdist.name}",
        f"sdist_sha256={digest(sdist)}",
    ]
    summary_text = summary.read_text(encoding="utf-8")
    assert wheel.name in summary_text
    assert digest(wheel) in summary_text
    assert sdist.name in summary_text
    assert digest(sdist) in summary_text


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"tag": "0.3.3"}, "release tag must be exact"),
        ({"artifact_name": "release-distributions-main"}, "artifact name must bind"),
    ),
)
def test_prepare_rejects_unbound_release_identity(tmp_path, overrides, message):
    directory, _wheel, _sdist = distributions(tmp_path)

    result, _output, _summary = prepare(tmp_path, directory, **overrides)

    assert result.returncode == 1
    assert message in result.stderr


def test_prepare_rejects_an_extra_distribution(tmp_path):
    directory, _wheel, _sdist = distributions(tmp_path)
    (directory / "unexpected.zip").write_bytes(b"extra")

    result, _output, _summary = prepare(tmp_path, directory)

    assert result.returncode == 1
    assert "expected exactly" in result.stderr


def test_prepare_rejects_a_hidden_extra_file(tmp_path):
    directory, _wheel, _sdist = distributions(tmp_path)
    (directory / ".gitignore").write_text("*\n", encoding="utf-8")

    result, _output, _summary = prepare(tmp_path, directory)

    assert result.returncode == 1
    assert "expected exactly" in result.stderr


def test_prepare_rejects_a_symlinked_distribution(tmp_path):
    directory, wheel, _sdist = distributions(tmp_path)
    wheel.unlink()
    wheel.symlink_to(directory / f"agent_statusline-{VERSION}.tar.gz")

    result, _output, _summary = prepare(tmp_path, directory)

    assert result.returncode == 1
    assert "non-regular entry" in result.stderr


def test_verify_accepts_the_unchanged_pair(tmp_path):
    directory, wheel, sdist = distributions(tmp_path)

    result = verify(directory, wheel, sdist)

    assert result.returncode == 0, result.stderr
    assert "verified exact v0.3.3 release pair" in result.stdout


@pytest.mark.parametrize("field", ("wheel_sha256", "sdist_sha256"))
def test_verify_rejects_a_changed_hash(tmp_path, field):
    directory, wheel, sdist = distributions(tmp_path)

    result = verify(directory, wheel, sdist, **{field: "0" * 64})

    assert result.returncode == 1
    assert "does not match the build job" in result.stderr


def test_verify_rejects_disagreeing_versions(tmp_path):
    directory, wheel, sdist = distributions(tmp_path)

    result = verify(
        directory,
        wheel,
        sdist,
        sdist_name="agent_statusline-0.3.4.tar.gz",
    )

    assert result.returncode == 1
    assert "versions do not agree" in result.stderr
