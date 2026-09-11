"""Cost accounting.

These cases exist because rendering against a live ledger banked phantom runs
twice and roughly doubled a session's reported cost (docs/adrs/0014). The defences are
pid-keyed run detection and a high-water fallback; both are pinned here.
"""

import json
import os
import subprocess
import sys

from agent_statusline import ledger


class TestApplyCost:
    def test_first_sighting_starts_a_run(self):
        row = {}
        assert ledger.apply_cost(row, 5.0, pid=100) == 5.0
        assert row["runs"] == 1
        assert row["cost_base"] == 0.0

    def test_cost_rising_within_one_run_does_not_bank(self):
        row = {}
        ledger.apply_cost(row, 5.0, pid=100)
        assert ledger.apply_cost(row, 8.0, pid=100) == 8.0
        assert row["runs"] == 1
        assert row["cost_base"] == 0.0

    def test_new_pid_reporting_less_banks_the_finished_run(self):
        row = {}
        ledger.apply_cost(row, 10.0, pid=100)
        total = ledger.apply_cost(row, 2.0, pid=200)  # resumed: new process
        assert total == 12.0
        assert row["cost_base"] == 10.0
        assert row["runs"] == 2

    def test_same_pid_reporting_less_keeps_the_high_water_mark(self):
        """A replayed or stale payload must not look like a resume."""
        row = {}
        ledger.apply_cost(row, 10.0, pid=100)
        assert ledger.apply_cost(row, 2.0, pid=100) == 10.0
        assert row["runs"] == 1
        assert row["cost_base"] == 0.0

    def test_decrease_without_a_pid_falls_back_to_banking(self):
        row = {}
        ledger.apply_cost(row, 10.0, pid=None)
        assert ledger.apply_cost(row, 2.0, pid=None) == 12.0
        assert row["runs"] == 2

    def test_missing_cost_leaves_the_row_alone(self):
        row = {"cost": 3.0}
        assert ledger.apply_cost(row, None) == 3.0

    def test_preexisting_cost_is_banked_on_first_sighting(self):
        row = {"cost": 7.0}
        assert ledger.apply_cost(row, 2.0, pid=100) == 7.0
        assert row["cost_base"] == 5.0


class TestTimestamps:
    def test_iso_round_trips_through_epoch(self):
        stamp = ledger.iso(1700000000)
        assert ledger.epoch(stamp) == 1700000000

    def test_epoch_accepts_legacy_numeric_stamps(self):
        assert ledger.epoch(1700000000.0) == 1700000000.0

    def test_epoch_is_zero_for_junk(self):
        assert ledger.epoch("not a date") == 0.0
        assert ledger.epoch(None) == 0.0

    def test_epoch_rejects_nonfinite_numbers_and_booleans(self):
        assert ledger.epoch(float("nan")) == 0.0
        assert ledger.epoch(float("inf")) == 0.0
        assert ledger.epoch(float("-inf")) == 0.0
        assert ledger.epoch(True) == 0.0

    def test_iso_has_an_offset(self):
        assert ledger.iso(1700000000)[-6] in "+-"


class TestRollingCosts:
    NOW = 1_800_000_000

    def test_initialization_seeds_legacy_rows_once_without_accrual(self):
        data = {
            "sessions": {
                "paid": {
                    "cost": 8.0,
                    "started": ledger.iso(self.NOW - 3600),
                    "updated": ledger.iso(self.NOW),
                },
                "zero": {"cost": 0.0},
                "poison": {"cost": "not-money"},
            }
        }

        assert ledger.record_cost_delta(data, "paid", 8.0, 8.0, when=self.NOW)
        assert data["cost_event_schema"] == ledger.COST_EVENT_SCHEMA
        assert data["cost_tracking_started"] == ledger.iso(self.NOW)
        assert len(data["cost_events"]) == 1
        assert data["cost_events"][0] == {
            "at": ledger.iso(self.NOW),
            "accrued_at": ledger.iso(self.NOW),
            "started_at": ledger.iso(self.NOW - 3600),
            "session": "paid",
            "delta": 8.0,
            "lifetime": 8.0,
            "seed": True,
        }
        assert all(row["cost_journal_seeded"] for row in data["sessions"].values())

        assert not ledger.record_cost_delta(data, "paid", 8.0, 8.0, when=self.NOW + 1)
        assert len(data["cost_events"]) == 1

    def test_initialization_ignores_a_seed_marker_without_its_schema(self):
        data = {
            "sessions": {
                "stale": {
                    "cost": 8.0,
                    "started": ledger.iso(self.NOW - 3600),
                    "updated": ledger.iso(self.NOW),
                    "cost_journal_seeded": True,
                }
            }
        }

        assert ledger.record_cost_delta(data, "stale", 8.0, 8.0, when=self.NOW)

        assert len(data["cost_events"]) == 1
        assert data["cost_events"][0]["seed"] is True
        assert data["cost_events"][0]["delta"] == 8.0

    def test_partial_schemaless_journal_is_preserved_as_incomplete_evidence(self):
        partial_journals = [
            {"cost_event_schema": None},
            {"cost_tracking_started": ledger.iso(self.NOW - 60)},
            {"cost_events": [{"malformed": True}]},
        ]

        for partial in partial_journals:
            data = {"sessions": {}, **partial}
            before = json.loads(json.dumps(data))

            assert not ledger.record_cost_delta(data, "paid", 0.0, 8.0, when=self.NOW)
            assert data == before

            rolling = ledger.rolling_costs(data, when=self.NOW)
            assert all(rolling[key] == 0.0 for key in ledger.COST_WINDOWS)
            assert not any(rolling[key + "_complete"] for key in ledger.COST_WINDOWS)

    def test_spanning_seed_is_a_lower_bound_but_wider_windows_are_exact(self):
        data = {
            "sessions": {
                "old": {
                    "cost": 50.0,
                    "started": ledger.iso(self.NOW - 2 * 86400),
                    "updated": ledger.iso(self.NOW),
                }
            }
        }
        ledger.record_cost_delta(data, "old", 50.0, 50.0, when=self.NOW)

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d1"] == 0.0
        assert rolling["d1_unattributed"] == 50.0
        assert rolling["d1_open_rows"] == 1
        assert not rolling["d1_complete"]
        assert rolling["d7"] == 50.0 and rolling["d7_complete"]
        assert rolling["d30"] == 50.0 and rolling["d30_complete"]

    def test_unknown_start_is_only_incomplete_while_the_seed_can_touch_a_window(self):
        data = {"sessions": {"unknown": {"cost": 5.0, "updated": ledger.iso(self.NOW - 2 * 86400)}}}
        ledger.record_cost_delta(data, "unknown", 5.0, 5.0, when=self.NOW)

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d1"] == 0.0 and rolling["d1_complete"]
        assert rolling["d7_unattributed"] == 5.0
        assert not rolling["d7_complete"]
        assert not rolling["d30_complete"]

    def test_closed_seed_uses_close_time_to_prove_it_ended_before_the_window(self):
        data = {
            "sessions": {
                "closed": {
                    "cost": 5.0,
                    "started": ledger.iso(self.NOW - 10 * 86400),
                    "updated": ledger.iso(self.NOW - 9 * 86400),
                    "closed": ledger.iso(self.NOW - 8 * 86400),
                    "state": "closed",
                }
            }
        }
        ledger.record_cost_delta(data, "closed", 5.0, 5.0, when=self.NOW)

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d7"] == 0.0
        assert rolling["d7_unattributed"] == 0.0
        assert rolling["d7_complete"]
        assert rolling["d30"] == 5.0

    def test_inconsistent_closed_lifecycle_remains_a_lower_bound(self):
        data = {
            "sessions": {
                "closed": {
                    "cost": 5.0,
                    "started": ledger.iso(self.NOW - 10 * 86400),
                    "updated": ledger.iso(self.NOW),
                    "closed": ledger.iso(self.NOW - 8 * 86400),
                    "state": "closed",
                }
            }
        }
        ledger.record_cost_delta(data, "closed", 5.0, 5.0, when=self.NOW)

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d7"] == 0.0
        assert rolling["d7_unattributed"] == 5.0
        assert not rolling["d7_complete"]

    def test_positive_deltas_use_inclusive_independent_window_boundaries(self):
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": [],
        }
        for age, amount in ((86400, 1.0), (7 * 86400, 2.0), (30 * 86400, 4.0)):
            data["cost_events"].append(
                {
                    "at": ledger.iso(self.NOW - age),
                    "accrued_at": ledger.iso(self.NOW - age),
                    "session": str(age),
                    "delta": amount,
                    "lifetime": amount,
                    "seed": False,
                }
            )

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d1"] == 1.0
        assert rolling["d7"] == 3.0
        assert rolling["d30"] == 7.0
        assert all(rolling[key + "_complete"] for key in ledger.COST_WINDOWS)

    def test_subsequent_delta_prefers_assistant_time_and_clamps_the_future(self):
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": [],
            "sessions": {"a": {"cost_journal_seeded": True}},
        }
        ledger.record_cost_delta(
            data,
            "a",
            1.0,
            2.0,
            when=self.NOW,
            accrued_at=ledger.iso(self.NOW - 3600),
        )
        ledger.record_cost_delta(
            data,
            "a",
            2.0,
            4.0,
            when=self.NOW + 60,
            accrued_at=ledger.iso(self.NOW + 365 * 86400),
        )

        assert data["cost_events"][0]["accrued_at"] == ledger.iso(self.NOW - 3600)
        assert data["cost_events"][1]["accrued_at"] == ledger.iso(self.NOW + 60)
        assert ledger.rolling_costs(data, when=self.NOW + 2 * 86400)["d1"] == 0.0

    def test_zero_decrease_replay_and_nonfinite_cost_append_nothing(self):
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW),
            "cost_events": [],
            "sessions": {"a": {"cost_journal_seeded": True}},
        }

        for previous, current in (
            (1.0, 1.0),
            (2.0, 1.0),
            (1.0, float("nan")),
            (1.0, float("inf")),
            (-1.0, 2.0),
            (-1e308, 1e308),
            ("bad", 2.0),
        ):
            assert not ledger.record_cost_delta(data, "a", previous, current, when=self.NOW)
        assert data["cost_events"] == []

    def test_unknown_schema_and_future_tracking_never_claim_exactness(self):
        event = {
            "at": ledger.iso(self.NOW),
            "accrued_at": ledger.iso(self.NOW),
            "session": "a",
            "delta": 10.0,
            "lifetime": 10.0,
            "seed": False,
        }
        unknown = {
            "cost_event_schema": 999,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": [event],
        }
        future = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW + 1),
            "cost_events": [],
        }

        unknown_rolling = ledger.rolling_costs(unknown, when=self.NOW)
        future_rolling = ledger.rolling_costs(future, when=self.NOW)

        assert unknown_rolling["d30"] == 0.0
        assert not any(unknown_rolling[key + "_complete"] for key in ledger.COST_WINDOWS)
        assert not any(future_rolling[key + "_complete"] for key in ledger.COST_WINDOWS)

    def test_finite_events_cannot_overflow_a_window_total(self):
        events = [
            {
                "at": ledger.iso(self.NOW),
                "accrued_at": ledger.iso(self.NOW),
                "session": str(number),
                "delta": 1e308,
                "lifetime": 1e308,
                "seed": False,
            }
            for number in range(2)
        ]
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": events,
        }

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d1"] == 1e308
        assert not rolling["d1_complete"]

    def test_poisoned_event_is_excluded_and_keeps_every_window_incomplete(self):
        valid = {
            "at": ledger.iso(self.NOW),
            "accrued_at": ledger.iso(self.NOW),
            "session": "valid",
            "delta": 2.0,
            "lifetime": 2.0,
            "seed": False,
        }
        poisoned = {**valid, "session": "poison", "accrued_at": float("nan"), "delta": 50.0}
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": [valid, poisoned],
        }

        rolling = ledger.rolling_costs(data, when=self.NOW)

        assert rolling["d1"] == 2.0
        assert not any(rolling[key + "_complete"] for key in ledger.COST_WINDOWS)

    def test_malformed_event_container_and_future_event_are_safe_and_incomplete(self):
        malformed = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": 17,
        }
        future_event = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": [
                {
                    "at": ledger.iso(self.NOW + 60),
                    "accrued_at": ledger.iso(self.NOW + 60),
                    "session": "future",
                    "delta": 9.0,
                    "lifetime": 9.0,
                    "seed": False,
                }
            ],
        }

        for data in (malformed, future_event):
            rolling = ledger.rolling_costs(data, when=self.NOW)
            assert rolling["d30"] == 0.0
            assert not rolling["d30_complete"]

    def test_event_validator_rejects_incomplete_or_inconsistent_shapes(self):
        valid = {
            "at": ledger.iso(self.NOW),
            "accrued_at": ledger.iso(self.NOW),
            "session": "a",
            "delta": 1.0,
            "lifetime": 1.0,
            "seed": False,
        }
        mutations = (
            {**valid, "session": ""},
            {**valid, "at": float("inf")},
            {**valid, "accrued_at": ledger.iso(self.NOW + 1)},
            {**valid, "seed": 1},
            {**valid, "delta": True},
            {**valid, "delta": -1.0},
            {**valid, "delta": 2.0, "lifetime": 1.0},
            {**valid, "lifetime": float("nan")},
            {**valid, "seed": True},
            {**valid, "seed": True, "started_at": ledger.iso(self.NOW + 1)},
        )

        assert ledger._valid_cost_event(valid)
        assert all(not ledger._valid_cost_event(event) for event in mutations)

    def test_retention_keeps_35_day_boundary_and_never_prunes_poison(self):
        def event(age):
            return {
                "at": ledger.iso(self.NOW - age),
                "accrued_at": ledger.iso(self.NOW - age),
                "session": str(age),
                "delta": 1.0,
                "lifetime": 1.0,
                "seed": False,
            }

        boundary = event(35 * 86400)
        outside = event(35 * 86400 + 1)
        recent = event(1)
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(self.NOW - 40 * 86400),
            "cost_events": [outside, boundary, recent],
            "sessions": {"a": {"cost_journal_seeded": True}},
        }

        assert ledger.record_cost_delta(data, "a", 1.0, 1.0, when=self.NOW)
        assert data["cost_events"] == [boundary, recent]

        poison = {**outside, "delta": float("nan")}
        data["cost_events"] = [outside, poison, recent]
        assert not ledger.record_cost_delta(data, "a", 1.0, 1.0, when=self.NOW)
        assert data["cost_events"] == [outside, poison, recent]


class TestPersistence:
    def test_save_then_load_round_trips(self):
        ledger.save({"sessions": {"abc": {"cost": 1.5}}})
        assert ledger.load()["sessions"]["abc"]["cost"] == 1.5

    def test_close_stamps_state_and_reason(self):
        ledger.save({"sessions": {"abc": {"cost": 1.5, "state": "live"}}})
        row = ledger.close_session("abc", reason="end")
        assert row["state"] == "closed"
        assert row["reason"] == "end"
        assert row["closed"]

    def test_closing_an_unknown_session_returns_none(self):
        ledger.save({"sessions": {}})
        assert ledger.close_session("nope") is None

    def test_session_end_can_create_and_close_an_unseen_session_atomically(self):
        ledger.save({"sessions": {}})
        row = ledger.close_session("new", reason="end", create=True)
        assert row["state"] == "closed"
        assert row["cost"] == 0.0
        assert ledger.load()["sessions"]["new"]["state"] == "closed"

    def test_load_normalizes_sessions_without_dropping_unrelated_state(self):
        with open(ledger.LEDGER, "w") as fh:
            json.dump(
                {
                    "sessions": {
                        "good": {"cost": 2.0},
                        "bad-list": [],
                        "bad-scalar": "invalid",
                    },
                    "metadata": {"keep": True},
                },
                fh,
            )

        assert ledger.load() == {
            "sessions": {"good": {"cost": 2.0}},
            "metadata": {"keep": True},
        }

    def test_save_normalizes_a_malformed_sessions_container(self):
        ledger.save({"sessions": ["bad"], "metadata": {"keep": True}})

        assert ledger.load() == {"sessions": {}, "metadata": {"keep": True}}

    def test_close_handles_a_malformed_session_row(self):
        ledger.save({"sessions": {"bad": []}})

        assert ledger.close_session("bad") is None
        row = ledger.close_session("bad", create=True)

        assert row["state"] == "closed"
        assert ledger.load()["sessions"]["bad"]["state"] == "closed"


def test_concurrent_ledger_update_and_close_preserve_every_field(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    env = dict(os.environ)
    env["AGENT_STATUSLINE_STATE"] = str(state_dir)
    env["HOME"] = str(tmp_path / "home")
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    initialize = r"""
from agent_statusline import ledger
ledger.save({"sessions": {"shared": {"cost": 1.0, "state": "live"}}})
"""
    subprocess.run([sys.executable, "-c", initialize], env=env, check=True)
    update_code = r"""
import sys
from agent_statusline import ledger
key = sys.argv[1]
def change(data):
    row = data["sessions"]["shared"]
    row[key] = key
    return True, None
ledger.update(change)
"""
    close_code = r"""
from agent_statusline import ledger
ledger.close_session("shared", reason="end")
"""
    processes = [
        subprocess.Popen([sys.executable, "-c", update_code, f"field_{number}"], env=env)
        for number in range(6)
    ]
    processes.append(subprocess.Popen([sys.executable, "-c", close_code], env=env))

    assert [process.wait(timeout=20) for process in processes] == [0] * 7
    data = json.loads((state_dir / "cost-ledger.json").read_text())
    row = data["sessions"]["shared"]
    assert row["state"] == "closed"
    assert row["reason"] == "end"
    assert row["cost"] == 1.0
    assert all(row[f"field_{number}"] == f"field_{number}" for number in range(6))
