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
        total = ledger.apply_cost(row, 2.0, pid=200)      # resumed: new process
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
