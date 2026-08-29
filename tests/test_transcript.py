"""Transcript signal extraction.

Field names here are not documented by Claude Code and were verified against
real transcripts; these tests are what stops a refactor silently renaming one.
"""

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
