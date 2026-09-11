"""Transcript signal extraction.

Field names here are not documented by Claude Code and were verified against
real transcripts; these tests are what stops a refactor silently renaming one.
"""

import json
import os
import subprocess
import sys

from agent_statusline import transcript


def absorb(*entries):
    tot = transcript._blank()
    for e in entries:
        transcript._absorb(tot, e)
    return tot


def assistant(usage, **extra):
    return {"type": "assistant", "message": {"usage": usage}, **extra}


class TestDig:
    def test_walks_a_nested_path(self):
        assert transcript.dig({"a": {"b": {"c": 1}}}, "a", "b", "c") == 1

    def test_missing_path_returns_the_default(self):
        assert transcript.dig({"a": {}}, "a", "b", default="x") == "x"

    def test_null_value_returns_the_default(self):
        assert transcript.dig({"a": None}, "a", default="x") == "x"


class TestUsage:
    def test_token_counts_accumulate(self):
        tot = absorb(
            assistant(
                {
                    "input_tokens": 1,
                    "output_tokens": 10,
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 1000,
                }
            ),
            assistant(
                {
                    "input_tokens": 2,
                    "output_tokens": 20,
                    "cache_creation_input_tokens": 200,
                    "cache_read_input_tokens": 2000,
                }
            ),
        )
        assert (tot["in"], tot["out"], tot["cw"], tot["cr"]) == (3, 30, 300, 3000)
        assert tot["turns"] == 2

    def test_thinking_tokens_are_read_from_the_details_block(self):
        tot = absorb(
            assistant({"input_tokens": 1, "output_tokens_details": {"thinking_tokens": 42}})
        )
        assert tot["think"] == 42

    def test_entries_without_usage_are_not_counted_as_turns(self):
        assert absorb({"type": "assistant", "message": {}})["turns"] == 0

    def test_synthetic_model_counts_as_an_api_error(self):
        tot = absorb(
            {"type": "assistant", "message": {"model": "<synthetic>", "usage": {"input_tokens": 1}}}
        )
        assert tot["synth"] == 1

    def test_numeric_strings_retain_transcript_count_semantics(self):
        tot = absorb(
            assistant(
                {
                    "input_tokens": "1",
                    "output_tokens": "2",
                    "cache_creation_input_tokens": "3",
                    "cache_read_input_tokens": "4",
                    "output_tokens_details": {"thinking_tokens": "5"},
                    "cache_creation": {
                        "ephemeral_1h_input_tokens": "6",
                        "ephemeral_5m_input_tokens": "7",
                    },
                }
            )
        )
        assert (tot["in"], tot["out"], tot["cw"], tot["cr"], tot["think"]) == (1, 2, 3, 4, 5)
        assert (tot["b1h"], tot["b5m"]) == (6, 7)

    def test_invalid_numeric_values_default_and_later_valid_values_count(self):
        tot = absorb(
            assistant(
                {
                    "input_tokens": "not-a-number",
                    "output_tokens": float("nan"),
                    "cache_creation_input_tokens": float("inf"),
                    "cache_read_input_tokens": True,
                    "output_tokens_details": {"thinking_tokens": float("-inf")},
                    "cache_creation": {
                        "ephemeral_1h_input_tokens": "invalid",
                        "ephemeral_5m_input_tokens": float("nan"),
                    },
                }
            ),
            assistant(
                {
                    "input_tokens": 11,
                    "output_tokens": 12,
                    "cache_creation_input_tokens": 13,
                    "cache_read_input_tokens": 14,
                    "output_tokens_details": {"thinking_tokens": 15},
                    "cache_creation": {
                        "ephemeral_1h_input_tokens": 16,
                        "ephemeral_5m_input_tokens": 17,
                    },
                }
            ),
        )
        assert (tot["in"], tot["out"], tot["cw"], tot["cr"], tot["think"]) == (11, 12, 13, 14, 15)
        assert (tot["b1h"], tot["b5m"], tot["last_bucket"]) == (16, 17, "5m")

    def test_non_mapping_message_usage_and_cache_creation_are_ignored(self):
        assert absorb({"type": "assistant", "message": []})["turns"] == 0
        assert absorb({"type": "assistant", "message": {"usage": "bad"}})["turns"] == 0
        tot = absorb(assistant({"input_tokens": 2, "cache_creation": "bad"}))
        assert (tot["in"], tot["b1h"], tot["b5m"]) == (2, 0, 0)


class TestCacheTtlBucket:
    def test_newest_write_decides_the_live_ttl(self):
        """Cumulative sums lag; the last write is the truth."""
        tot = absorb(
            assistant({"cache_creation": {"ephemeral_1h_input_tokens": 10000}}),
            assistant({"cache_creation": {"ephemeral_5m_input_tokens": 5}}),
        )
        assert tot["last_bucket"] == "5m", "must not be outvoted by cumulative 1h totals"
        assert tot["b1h"] == 10000
        assert tot["b5m"] == 5

    def test_no_writes_leaves_the_bucket_unknown(self):
        assert absorb(assistant({"input_tokens": 1}))["last_bucket"] is None


class TestToolSignals:
    def test_tool_uses_are_counted_by_name(self):
        tot = absorb(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash", "input": {}},
                        {"type": "tool_use", "name": "Bash", "input": {}},
                        {"type": "tool_use", "name": "Read", "input": {}},
                    ]
                },
            }
        )
        assert tot["tools"] == {"Bash": 2, "Read": 1}

    def test_non_string_tool_names_use_unknown_key_and_later_tools_count(self):
        tot = absorb(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": ["invalid"], "input": {}},
                        {"type": "tool_use", "name": {"invalid": True}, "input": {}},
                        {"type": "tool_use", "name": "Read", "input": {}},
                    ]
                },
            }
        )
        assert tot["tools"] == {"?": 2, "Read": 1}

    def test_edited_and_read_paths_are_kept_apart(self):
        tot = absorb(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "/a"}},
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "/b"}},
                    ]
                },
            }
        )
        assert tot["f_edit"] == ["/a"]
        assert tot["f_read"] == ["/b"]

    def test_paths_are_deduplicated(self):
        tot = absorb(
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "/a"}},
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "/a"}},
                    ]
                },
            }
        )
        assert tot["f_edit"] == ["/a"]

    def test_error_results_are_counted(self):
        tot = absorb(
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "is_error": True},
                        {"type": "tool_result", "is_error": False},
                    ]
                },
            }
        )
        assert tot["errors"] == 1


class TestSystemEntries:
    def test_turn_durations_are_collected(self):
        tot = absorb({"type": "system", "subtype": "turn_duration", "durationMs": 1234})
        assert tot["durs"] == [1234]

    def test_hook_summaries_record_runs_and_errors(self):
        tot = absorb(
            {
                "type": "system",
                "subtype": "stop_hook_summary",
                "hookInfos": [{"durationMs": 10}, {"durationMs": 20}],
                "hookErrors": ["boom"],
            }
        )
        assert tot["hook_runs"] == 2
        assert tot["hook_ms"] == [10, 20]
        assert tot["hook_errs"] == 1

    def test_invalid_durations_default_without_blocking_later_valid_durations(self):
        tot = absorb(
            {"type": "system", "subtype": "turn_duration", "durationMs": float("nan")},
            {
                "type": "system",
                "subtype": "stop_hook_summary",
                "hookInfos": [{"durationMs": float("inf")}, "invalid"],
                "hookErrors": "invalid",
            },
            {"type": "system", "subtype": "turn_duration", "durationMs": 1234},
            {
                "type": "system",
                "subtype": "stop_hook_summary",
                "hookInfos": [{"durationMs": "56"}],
            },
        )
        assert tot["durs"] == [1234]
        assert tot["hook_runs"] == 2
        assert tot["hook_ms"] == [0, 56]
        assert tot["hook_errs"] == 0

    def test_non_string_local_command_content_is_ignored(self):
        assert absorb({"type": "system", "subtype": "local_command", "content": []})["cmds"] == {}

    def test_slash_commands_are_parsed_out_of_the_content(self):
        tot = absorb(
            {
                "type": "system",
                "subtype": "local_command",
                "content": "<command-name>/effort</command-name>",
            }
        )
        assert tot["cmds"] == {"/effort": 1}


class TestTopLevelFlags:
    def test_sidechain_entries_count_as_subagent_traffic(self):
        assert absorb({"type": "user", "isSidechain": True})["side"] == 1

    def test_permission_mode_is_taken_from_the_transcript(self):
        assert absorb({"type": "user", "permissionMode": "plan"})["perm"] == "plan"

    def test_compaction_is_detected_defensively(self):
        assert absorb({"type": "user", "isCompactSummary": True})["compact"] == 1


class TestMissingFiles:
    def test_absent_transcript_yields_blank_totals(self):
        assert transcript.transcript_totals("/nonexistent/x.jsonl") == transcript._blank()

    def test_absent_transcript_has_no_conversation_root(self):
        assert transcript.conversation_root("/nonexistent/x.jsonl") is None


class TestRowShape:
    def test_non_object_rows_are_ignored_and_later_rows_count(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text(
            '["ignored"]\n'
            '{"type":"assistant","message":{"usage":{"input_tokens":2}}}\n'
            "null\n"
            '{"type":"assistant","message":{"usage":{"input_tokens":3}}}\n'
        )
        monkeypatch.setattr(transcript, "TSTATE", str(tmp_path / "state.json"))

        totals = transcript.transcript_totals(str(path))

        assert totals["in"] == 5
        assert totals["turns"] == 2

    def test_non_object_root_rows_are_ignored_and_later_user_counts(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text('42\nnull\n{"type":"user","uuid":"root-123"}\n')
        monkeypatch.setattr(transcript, "TSTATE", str(tmp_path / "state.json"))

        assert transcript.conversation_root(str(path)) == "root-123"

    def test_non_string_root_uuid_is_ignored_and_later_valid_root_counts(
        self, tmp_path, monkeypatch
    ):
        path = tmp_path / "session.jsonl"
        path.write_text(
            '{"type":"user","uuid":["invalid"]}\n'
            '{"type":"user","uuid":{"invalid":true}}\n'
            '{"type":"user","uuid":"root-123"}\n'
        )
        monkeypatch.setattr(transcript, "TSTATE", str(tmp_path / "state.json"))

        assert transcript.conversation_root(str(path)) == "root-123"

    def test_cached_non_string_root_is_ignored(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"user","uuid":"root-123"}\n')
        state_path = tmp_path / "state.json"
        state_path.write_text(f'{{"{path}":{{"root":["invalid"]}}}}')
        monkeypatch.setattr(transcript, "TSTATE", str(state_path))

        assert transcript.conversation_root(str(path)) == "root-123"


class TestCachedStateShape:
    def test_non_mapping_cache_row_is_replaced_without_losing_other_rows(
        self, tmp_path, monkeypatch
    ):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"assistant","message":{"usage":{"input_tokens":3}}}\n')
        other = tmp_path / "other.jsonl"
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({str(path): [], str(other): {"keep": True}}))
        monkeypatch.setattr(transcript, "TSTATE", str(state_path))

        assert transcript.transcript_totals(str(path))["in"] == 3
        cache = json.loads(state_path.read_text())
        assert cache[str(other)]["keep"] is True
        assert isinstance(cache[str(other)]["accessed_at"], float)
        assert cache[str(path)]["totals"]["in"] == 3

    def test_non_mapping_totals_and_invalid_offset_are_normalized(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"assistant","message":{"usage":{"output_tokens":4}}}\n')
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    str(path): {
                        "schema": transcript.SCHEMA,
                        "offset": [],
                        "totals": [],
                    }
                }
            )
        )
        monkeypatch.setattr(transcript, "TSTATE", str(state_path))

        totals = transcript.transcript_totals(str(path))

        assert totals["out"] == 4
        assert json.loads(state_path.read_text())[str(path)]["offset"] == path.stat().st_size

    def test_non_mapping_totals_with_valid_eof_offset_replays_from_zero(
        self, tmp_path, monkeypatch
    ):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n')
        other = tmp_path / "other.jsonl"
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    str(path): {
                        "schema": transcript.SCHEMA,
                        "offset": path.stat().st_size,
                        "totals": [],
                        "root": "root-keep",
                    },
                    str(other): {"keep": True},
                }
            )
        )
        monkeypatch.setattr(transcript, "TSTATE", str(state_path))

        totals = transcript.transcript_totals(str(path))

        cache = json.loads(state_path.read_text())
        assert totals["in"] == 5
        assert totals["turns"] == 1
        assert cache[str(path)]["offset"] == path.stat().st_size
        assert cache[str(path)]["root"] == "root-keep"
        assert cache[str(other)]["keep"] is True
        assert isinstance(cache[str(other)]["accessed_at"], float)

    def test_nested_totals_containers_are_normalized_before_absorb(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"assistant","message":{"usage":{"input_tokens":2}}}\n')
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    str(path): {
                        "schema": transcript.SCHEMA,
                        "offset": 0,
                        "totals": {
                            "tools": [],
                            "cmds": "bad",
                            "f_edit": {},
                            "durs": "bad",
                            "in": [],
                            "last_bucket": [],
                        },
                    }
                }
            )
        )
        monkeypatch.setattr(transcript, "TSTATE", str(state_path))

        totals = transcript.transcript_totals(str(path))

        assert totals["in"] == 2
        assert totals["tools"] == {}
        assert totals["cmds"] == {}
        assert totals["f_edit"] == []
        assert totals["durs"] == []
        assert totals["last_bucket"] is None

    def test_invalid_offset_discards_cached_totals_before_replay(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n')
        state_path = tmp_path / "state.json"
        for invalid_offset in (-1, True, []):
            totals = transcript._blank()
            totals.update({"in": 5, "turns": 1})
            state_path.write_text(
                json.dumps(
                    {
                        str(path): {
                            "schema": transcript.SCHEMA,
                            "offset": invalid_offset,
                            "totals": totals,
                        }
                    }
                )
            )
            monkeypatch.setattr(transcript, "TSTATE", str(state_path))

            result = transcript.transcript_totals(str(path))

            assert result["in"] == 5
            assert result["turns"] == 1

    def test_non_mapping_conversation_row_is_replaced(self, tmp_path, monkeypatch):
        path = tmp_path / "session.jsonl"
        path.write_text('{"type":"user","uuid":"root-123"}\n')
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({str(path): []}))
        monkeypatch.setattr(transcript, "TSTATE", str(state_path))

        assert transcript.conversation_root(str(path)) == "root-123"
        assert json.loads(state_path.read_text())[str(path)]["root"] == "root-123"


def test_transcript_cache_retention_boundary_migration_and_invalid_rows(tmp_path, monkeypatch):
    now = 2_000_000_000.0
    path = tmp_path / "active.jsonl"
    path.write_text("")
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                str(path): {
                    "schema": transcript.SCHEMA,
                    "offset": 0,
                    "totals": transcript._blank(),
                    "accessed_at": now - 1,
                },
                "boundary": {"accessed_at": now - transcript.CACHE_RETENTION_S},
                "expired": {"accessed_at": now - transcript.CACHE_RETENTION_S - 1},
                "legacy": {"root": "legacy-root"},
                "future": {"accessed_at": now + 1},
                "malformed": [],
            }
        )
    )
    monkeypatch.setattr(transcript, "TSTATE", str(state_path))
    monkeypatch.setattr(transcript.time, "time", lambda: now)

    assert transcript.transcript_totals(str(path)) == transcript._blank()

    cache = json.loads(state_path.read_text())
    assert "boundary" in cache
    assert "expired" not in cache
    assert cache["legacy"]["accessed_at"] == now
    assert cache["future"]["accessed_at"] == now
    assert "malformed" not in cache


def test_transcript_cache_cap_preserves_active_row_and_totals(tmp_path, monkeypatch):
    now = 2_000_000_000.0
    path = tmp_path / "active.jsonl"
    path.write_text('{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n')
    cached_totals = transcript._blank()
    cached_totals.update({"in": 5, "turns": 1})
    state_path = tmp_path / "state.json"
    rows = {
        str(path): {
            "schema": transcript.SCHEMA,
            "offset": path.stat().st_size,
            "totals": cached_totals,
            "accessed_at": now - transcript.CACHE_TOUCH_S,
        },
        **{
            f"other:{index:03d}": {"accessed_at": now - index}
            for index in range(transcript.MAX_CACHED_TRANSCRIPTS)
        },
    }
    state_path.write_text(json.dumps(rows))
    monkeypatch.setattr(transcript, "TSTATE", str(state_path))
    monkeypatch.setattr(transcript.time, "time", lambda: now)

    totals = transcript.transcript_totals(str(path))

    cache = json.loads(state_path.read_text())
    assert totals["in"] == 5
    assert totals["turns"] == 1
    assert cache[str(path)]["offset"] == path.stat().st_size
    assert len(cache) == transcript.MAX_CACHED_TRANSCRIPTS
    assert "other:511" not in cache


def test_unchanged_transcript_row_is_touched_no_more_than_hourly(tmp_path, monkeypatch):
    clock = [2_000_000_000.0]
    path = tmp_path / "active.jsonl"
    path.write_text("")
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(transcript, "TSTATE", str(state_path))
    monkeypatch.setattr(transcript.time, "time", lambda: clock[0])

    transcript.transcript_totals(str(path))
    initial = state_path.read_bytes()
    initial_access = json.loads(initial)[str(path)]["accessed_at"]

    clock[0] += transcript.CACHE_TOUCH_S - 1
    transcript.transcript_totals(str(path))
    assert state_path.read_bytes() == initial

    clock[0] += 1
    transcript.transcript_totals(str(path))
    touched = json.loads(state_path.read_text())[str(path)]["accessed_at"]
    assert touched == initial_access + transcript.CACHE_TOUCH_S


def test_cached_conversation_root_also_runs_retention_maintenance(tmp_path, monkeypatch):
    now = 2_000_000_000.0
    path = tmp_path / "active.jsonl"
    path.write_text('{"type":"user","uuid":"root-123"}\n')
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                str(path): {"root": "root-123", "accessed_at": now - 1},
                "expired": {"accessed_at": now - transcript.CACHE_RETENTION_S - 1},
            }
        )
    )
    monkeypatch.setattr(transcript, "TSTATE", str(state_path))
    monkeypatch.setattr(transcript.time, "time", lambda: now)

    assert transcript.conversation_root(str(path)) == "root-123"
    assert "expired" not in json.loads(state_path.read_text())


def test_transcript_cache_read_failure_uses_established_fallbacks(tmp_path, monkeypatch):
    path = tmp_path / "session.jsonl"
    path.write_text(
        '{"type":"user","uuid":"root-123"}\n'
        '{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n'
    )

    def fail_read(_path, _default, _updater):
        raise PermissionError("read-only state directory")

    monkeypatch.setattr(transcript, "update_json", fail_read)

    assert transcript.transcript_totals(str(path)) == transcript._blank()
    assert transcript.conversation_root(str(path)) is None


def test_transcript_cache_symlink_is_refused_without_touching_target(tmp_path, monkeypatch):
    path = tmp_path / "session.jsonl"
    path.write_text(
        '{"type":"user","uuid":"root-123"}\n'
        '{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n'
    )
    outside = tmp_path / "outside.json"
    outside.write_text('{"sentinel":true}\n')
    state_path = tmp_path / "state.json"
    state_path.symlink_to(outside)
    before = outside.read_bytes()
    monkeypatch.setattr(transcript, "TSTATE", str(state_path))

    assert transcript.transcript_totals(str(path)) == transcript._blank()
    assert transcript.conversation_root(str(path)) is None
    assert outside.read_bytes() == before
    assert state_path.is_symlink()


def test_transcript_cache_publication_failure_returns_computed_results(tmp_path, monkeypatch):
    path = tmp_path / "session.jsonl"
    path.write_text(
        '{"type":"user","uuid":"root-123"}\n'
        '{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n'
    )
    computed = []

    def fail_after_update(_path, _default, updater):
        changed, result = updater({})
        assert changed
        computed.append(result)
        raise OSError("injected publication failure")

    monkeypatch.setattr(transcript, "update_json", fail_after_update)

    totals = transcript.transcript_totals(str(path))
    root = transcript.conversation_root(str(path))

    assert totals == computed[0]
    assert totals["in"] == 5
    assert totals["turns"] == 1
    assert root == computed[1] == "root-123"


def test_truncated_final_line_is_deferred_without_double_counting(tmp_path, monkeypatch):
    path = tmp_path / "session.jsonl"
    first = '{"type":"assistant","message":{"usage":{"input_tokens":1}}}\n'
    second = '{"type":"assistant","message":{"usage":{"input_tokens":2}}}'
    path.write_text(first + second[:30])
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(transcript, "TSTATE", str(state_path))

    assert transcript.transcript_totals(str(path))["in"] == 1
    with path.open("a") as fh:
        fh.write(second[30:] + "\n")

    assert transcript.transcript_totals(str(path))["in"] == 3
    assert json.loads(state_path.read_text())[str(path)]["offset"] == path.stat().st_size


def test_concurrent_readers_of_a_growing_transcript_do_not_regress_state(tmp_path):
    transcript_path = tmp_path / "growing.jsonl"
    transcript_path.write_text("")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    env = dict(os.environ)
    env["AGENT_STATUSLINE_STATE"] = str(state_dir)
    env["HOME"] = str(tmp_path / "home")
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    reader = r"""
import sys, time
from agent_statusline.transcript import transcript_totals
for _ in range(50):
    transcript_totals(sys.argv[1])
    time.sleep(0.002)
"""
    writer = r"""
import json, sys, time
with open(sys.argv[1], "a") as handle:
    for number in range(40):
        record = {"type": "assistant", "message": {"usage": {"input_tokens": 1}}}
        handle.write(json.dumps(record) + "\n")
        handle.flush()
        time.sleep(0.001)
"""
    readers = [
        subprocess.Popen([sys.executable, "-c", reader, str(transcript_path)], env=env)
        for _ in range(6)
    ]
    growing = subprocess.Popen([sys.executable, "-c", writer, str(transcript_path)], env=env)

    assert growing.wait(timeout=20) == 0
    assert [process.wait(timeout=20) for process in readers] == [0] * 6
    inspect = r"""
import json, sys
from agent_statusline.transcript import transcript_totals
print(json.dumps(transcript_totals(sys.argv[1])))
"""
    result = subprocess.run(
        [sys.executable, "-c", inspect, str(transcript_path)],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    totals = json.loads(result.stdout.splitlines()[-1])
    cache = json.loads((state_dir / "statusline-transcript.json").read_text())

    assert totals["in"] == 40
    assert totals["turns"] == 40
    assert cache[str(transcript_path)]["offset"] == transcript_path.stat().st_size
