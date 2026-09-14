import argparse
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_package_index.py"
SPEC = importlib.util.spec_from_file_location("verify_package_index", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
verify_package_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_package_index)

WHEEL = "agent_statusline-0.3.4-py3-none-any.whl"
SDIST = "agent_statusline-0.3.4.tar.gz"
WHEEL_SHA = "a" * 64
SDIST_SHA = "b" * 64
EXPECTED = (
    verify_package_index.ExpectedFile(WHEEL, WHEEL_SHA, "bdist_wheel"),
    verify_package_index.ExpectedFile(SDIST, SDIST_SHA, "sdist"),
)


def payload(*, name="agent-statusline", version="0.3.4", files=None):
    if files is None:
        files = [
            {
                "filename": WHEEL,
                "digests": {"sha256": WHEEL_SHA},
                "packagetype": "bdist_wheel",
            },
            {
                "filename": SDIST,
                "digests": {"sha256": SDIST_SHA},
                "packagetype": "sdist",
            },
        ]
    return {"info": {"name": name, "version": version}, "urls": files}


def test_validate_release_accepts_exact_pair_and_normalized_project_name():
    verify_package_index.validate_release(
        payload(name="agent_statusline"),
        project="agent-statusline",
        version="0.3.4",
        expected=EXPECTED,
    )


@pytest.mark.parametrize(
    ("candidate", "message"),
    (
        (payload(name="other"), "project identity"),
        (payload(version="0.3.5"), "version does not match"),
        (payload(files=[]), "exactly the expected release pair"),
        (
            payload(
                files=[
                    {
                        "filename": WHEEL,
                        "digests": {"sha256": "0" * 64},
                        "packagetype": "bdist_wheel",
                    },
                    {
                        "filename": SDIST,
                        "digests": {"sha256": SDIST_SHA},
                        "packagetype": "sdist",
                    },
                ]
            ),
            "SHA-256 does not match",
        ),
        (
            payload(
                files=[
                    {
                        "filename": WHEEL,
                        "digests": {"sha256": WHEEL_SHA},
                        "packagetype": "sdist",
                    },
                    {
                        "filename": SDIST,
                        "digests": {"sha256": SDIST_SHA},
                        "packagetype": "sdist",
                    },
                ]
            ),
            "type does not match",
        ),
    ),
)
def test_validate_release_rejects_identity_membership_hash_or_type(candidate, message):
    with pytest.raises(ValueError, match=message):
        verify_package_index.validate_release(
            candidate,
            project="agent-statusline",
            version="0.3.4",
            expected=EXPECTED,
        )


def test_verify_retries_bounded_partial_index_state(monkeypatch):
    responses = [payload(files=[]), payload()]
    sleeps = []
    monkeypatch.setattr(
        verify_package_index,
        "_request_json",
        lambda _url, _timeout: responses.pop(0),
    )
    monkeypatch.setattr(verify_package_index.time, "sleep", sleeps.append)

    verify_package_index.verify_with_retries(
        index="testpypi",
        project="agent-statusline",
        version="0.3.4",
        expected=EXPECTED,
        attempts=2,
        delay_seconds=0.25,
        timeout_seconds=1,
    )

    assert sleeps == [0.25]


def test_verify_fails_after_the_exact_attempt_bound(monkeypatch):
    calls = []

    def unavailable(url, timeout):
        calls.append((url, timeout))
        raise OSError("unavailable")

    monkeypatch.setattr(verify_package_index, "_request_json", unavailable)
    monkeypatch.setattr(verify_package_index.time, "sleep", lambda _delay: None)

    with pytest.raises(ValueError, match="after 3 attempts"):
        verify_package_index.verify_with_retries(
            index="testpypi",
            project="agent-statusline",
            version="0.3.4",
            expected=EXPECTED,
            attempts=3,
            delay_seconds=0,
            timeout_seconds=2,
        )

    assert len(calls) == 3
    assert calls[0] == (
        "https://test.pypi.org/pypi/agent-statusline/0.3.4/json",
        2,
    )


def test_production_index_uses_the_exact_versioned_json_endpoint(monkeypatch):
    calls = []

    def available(url, timeout):
        calls.append((url, timeout))
        return payload()

    monkeypatch.setattr(verify_package_index, "_request_json", available)

    verify_package_index.verify_with_retries(
        index="pypi",
        project="agent-statusline",
        version="0.3.4",
        expected=EXPECTED,
        attempts=1,
        delay_seconds=0,
        timeout_seconds=3,
    )

    assert calls == [("https://pypi.org/pypi/agent-statusline/0.3.4/json", 3)]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("wheel_name", "../wheel.whl", "plain basename"),
        ("wheel_sha256", "bad", "SHA-256 is malformed"),
        ("sdist_sha256", "bad", "SHA-256 is malformed"),
    ),
)
def test_expected_files_rejects_malformed_identity(field, value, message):
    values = {
        "wheel_name": WHEEL,
        "wheel_sha256": WHEEL_SHA,
        "sdist_name": SDIST,
        "sdist_sha256": SDIST_SHA,
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        verify_package_index._expected_files(argparse.Namespace(**values))
