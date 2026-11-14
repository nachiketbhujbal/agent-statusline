"""Render a demonstration session from synthetic evidence only."""

import argparse

from agent_statusline.acquisition import claude_facts
from agent_statusline.config import load_config
from agent_statusline.statusline import render_facts


def _facts():
    payload = {
        "session_id": "synthetic-preview",
        "session_name": "Synthetic preview",
        "cwd": "example-project",
        "workspace": {"added_dirs": ["reference"]},
        "version": "2.0.0",
        "output_style": {"name": "review"},
        "model": {"display_name": "Synthetic Model"},
        "effort": {"level": "high"},
        "thinking": {"enabled": True},
        "context_window": {
            "context_window_size": 200_000,
            "used_percentage": 24,
            "current_usage": {"input_tokens": 150, "cache_read_input_tokens": 47_850},
        },
        "rate_limits": {
            "five_hour": {"used_percentage": 15},
            "seven_day": {"used_percentage": 42},
        },
        "cost": {
            "total_cost_usd": 1.25,
            "total_duration_ms": 600_000,
            "total_api_duration_ms": 120_000,
            "total_lines_added": 10,
            "total_lines_removed": 2,
        },
    }
    activity = {
        "in": 300,
        "cr": 47_850,
        "cw": 200,
        "out": 600,
        "turns": 8,
        "think": 150,
        "last_bucket": "1h",
        "b1h": 200,
        "cache_pricing_model": "claude-opus-5-5",
        "cache_pricing_complete": True,
        "tools": {"Read": 5, "Edit": 2},
        "errors": 0,
        "synth": 1,
        "f_edit": {"example.py"},
        "f_read": {"README.md"},
        "side": 0,
        "subagent_ids": {"synthetic-agent": True},
        "compact": 1,
        "cmds": {"/compact": 1},
        "durs": [1_200, 4_000],
        "hook_runs": 1,
        "hook_ms": [12],
        "hook_errs": 0,
        "perm": "plan",
        "tier": "priority",
    }
    return claude_facts(payload, lambda _: activity)


def _git(cwd):
    return {"branch": "example", "upstream": True}, cwd, False


def _probe(key, _ttl, _native_probe):
    return {
        "procs": {
            "mine_rss": 256 * 2**20,
            "mine_procs": 2,
            "mine_pid": 1234,
            "all_rss": 512 * 2**20,
            "all_n": 3,
        },
        "mem": {"pct": 45, "total": 16 * 2**30},
        "disk": {"pct": 31, "free": 128 * 2**30},
        "account": {"enabled": True},
    }[key.partition(":")[0]]


def _cost(_facts, _config, _project, _procs, _wall):
    return {
        "session": 1.25,
        "base": 0.0,
        "d1": 1.25,
        "d7": 1.25,
        "d30": 1.25,
        "d1_complete": True,
        "d7_complete": True,
        "d30_complete": True,
        "last5": 1.25,
        "all": 1.25,
        "convos": 1,
        "n": 1,
        "forks": 0,
    }


def cli(argv):
    parser = argparse.ArgumentParser(prog="agent-statusline config preview", allow_abbrev=False)
    parser.add_argument("--width", type=int, help="terminal width in cells")
    args = parser.parse_args(argv)
    if args.width is not None and args.width < 1:
        parser.error("--width must be positive")
    output = render_facts(
        _facts(),
        load_config(),
        find_git=_git,
        probe=_probe,
        record_limits=lambda _five, _seven: None,
        summarize_cost=_cost,
        columns=args.width,
    )
    if output:
        print(output)
    return 0
