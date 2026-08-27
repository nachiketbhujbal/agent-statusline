"""Cost accounting.

These cases exist because rendering against a live ledger banked phantom runs
twice and roughly doubled a session's reported cost (docs/adrs/0014). The defences are
pid-keyed run detection and a high-water fallback; both are pinned here.
"""

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

    def test_iso_has_an_offset(self):
        assert ledger.iso(1700000000)[-6] in "+-"


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


class TestRollingCosts:
    def test_spanning_legacy_session_starts_as_an_honest_lower_bound(self):
        now = 1_800_000_000
        data = {
            "sessions": {
                "old": {
                    "cost": 50.0,
                    "started": ledger.iso(now - 2 * 86400),
                    "updated": ledger.iso(now),
                }
            }
        }
        assert ledger.record_cost_delta(data, "old", 50.0, 50.0, when=1_800_000_000)
        rolling = ledger.rolling_costs(data, when=1_800_000_001)
        assert rolling["d1"] == 0.0
        assert rolling["d1_unattributed"] == 50.0
        assert not rolling["d1_complete"]
        assert rolling["d7"] == 50.0 and rolling["d7_complete"]
        assert rolling["d30"] == 50.0 and rolling["d30_complete"]

    def test_missing_legacy_start_never_receives_an_exact_claim(self):
        now = 1_800_000_000
        data = {"sessions": {"old": {"cost": 50.0, "updated": ledger.iso(now)}}}
        ledger.record_cost_delta(data, "old", 50.0, 50.0, when=now)
        rolling = ledger.rolling_costs(data, when=now)
        assert rolling["d30"] == 0.0
        assert rolling["d30_unattributed"] == 50.0
        assert not rolling["d30_complete"]

    def test_positive_deltas_land_in_the_applicable_windows(self):
        now = 1_800_000_000
        data = {
            "cost_event_schema": ledger.COST_EVENT_SCHEMA,
            "cost_tracking_started": ledger.iso(now - 40 * 86400),
            "cost_events": [
                {
                    "at": ledger.iso(now - 12 * 3600),
                    "accrued_at": ledger.iso(now - 12 * 3600),
                    "session": "a",
                    "delta": 1.0,
                    "lifetime": 1.0,
                    "seed": False,
                },
                {
                    "at": ledger.iso(now - 3 * 86400),
                    "accrued_at": ledger.iso(now - 3 * 86400),
                    "session": "b",
                    "delta": 2.0,
                    "lifetime": 2.0,
                    "seed": False,
                },
                {
                    "at": ledger.iso(now - 20 * 86400),
                    "accrued_at": ledger.iso(now - 20 * 86400),
                    "session": "c",
                    "delta": 4.0,
                    "lifetime": 4.0,
                    "seed": False,
                },
            ],
        }
        rolling = ledger.rolling_costs(data, when=now)
        assert rolling["d1"] == 1.0
        assert rolling["d7"] == 3.0
        assert rolling["d30"] == 7.0
        assert rolling["d1_complete"]
        assert rolling["d7_complete"]
        assert rolling["d30_complete"]

    def test_zero_or_replayed_cost_does_not_create_an_event(self):
        data = {}
        ledger.record_cost_delta(data, "a", 1.0, 1.0, when=1_800_000_000)
        assert data["cost_events"] == []

    def test_first_sighting_is_a_seed_not_new_accrual(self):
        now = 1_800_000_000
        data = {
            "sessions": {
                "a": {
                    "cost": 8.0,
                    "started": ledger.iso(now - 3600),
                    "updated": ledger.iso(now),
                }
            }
        }
        ledger.record_cost_delta(data, "a", 0.0, 8.0, when=now)
        assert data["cost_events"] == [
            {
                "at": ledger.iso(now),
                "accrued_at": ledger.iso(now),
                "started_at": ledger.iso(now - 3600),
                "session": "a",
                "delta": 8.0,
                "lifetime": 8.0,
                "seed": True,
            }
        ]

    def test_subsequent_delta_uses_accrual_timestamp(self):
        now = 1_800_000_000
        data = {
            "sessions": {
                "a": {
                    "cost": 5.0,
                    "started": ledger.iso(now - 3600),
                    "updated": ledger.iso(now),
                }
            }
        }
        ledger.record_cost_delta(data, "a", 0.0, 5.0, when=now)
        data["sessions"]["a"]["cost"] = 7.0
        accrued = ledger.iso(now + 30)
        ledger.record_cost_delta(data, "a", 5.0, 7.0, when=now + 60, accrued_at=accrued)
        event = data["cost_events"][-1]
        assert not event["seed"]
        assert event["delta"] == 2.0
        assert event["accrued_at"] == accrued

    def test_unknown_schema_never_claims_a_complete_window(self):
        data = {
            "cost_event_schema": 999,
            "cost_tracking_started": ledger.iso(1_700_000_000),
            "cost_events": [],
        }
        rolling = ledger.rolling_costs(data, when=1_800_000_000)
        assert not any(rolling[key] for key in ("d1_complete", "d7_complete", "d30_complete"))
