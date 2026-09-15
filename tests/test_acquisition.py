"""Normalized host acquisition facts."""

from agent_statusline.acquisition import GROUPS, claude_facts


def test_claude_adapter_emits_the_normalized_groups(payload):
    facts = claude_facts(payload)

    assert tuple(key for key in facts if key in GROUPS) == GROUPS
    assert facts["host"] == "claude"
    assert facts["identity"]["session_id"] == payload["session_id"]
    assert facts["workspace"]["project_dir"] == payload["workspace"]["project_dir"]
    assert facts["model"]["display_name"] == payload["model"]["display_name"]
    assert facts["context"]["window_size"] == payload["context_window"]["context_window_size"]
    assert facts["tokens"]["turns"] == 1
    assert facts["limits"]["five_hour"] == payload["rate_limits"]["five_hour"]
    assert facts["money"]["run_cost_usd"] == 1.25


def test_claude_adapter_omits_money_the_host_did_not_supply(payload):
    payload["cost"].pop("total_cost_usd")

    facts = claude_facts(payload)

    assert "run_cost_usd" not in facts["money"]


def test_claude_adapter_omits_malformed_or_non_finite_money(payload):
    for invalid in ("invalid", float("nan"), float("inf"), True):
        payload["cost"]["total_cost_usd"] = invalid
        assert "run_cost_usd" not in claude_facts(payload)["money"]


def test_claude_adapter_uses_safe_shapes_for_malformed_optional_groups(tmp_path):
    facts = claude_facts(
        {
            "workspace": "invalid",
            "context_window": {"current_usage": "invalid"},
            "rate_limits": [],
            "cost": "invalid",
        },
        transcript_reader=lambda _path: "invalid",
        default_cwd=str(tmp_path),
    )

    assert facts["workspace"] == {
        "cwd": str(tmp_path),
        "project_dir": str(tmp_path),
        "added_dirs": [],
    }
    assert facts["context"] == {}
    assert facts["limits"] == {}
    assert "run_cost_usd" not in facts["money"]


def test_claude_adapter_rejects_a_non_object_payload():
    assert claude_facts([]) is None
