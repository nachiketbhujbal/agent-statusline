#!/usr/bin/env python3
"""Environment probes for the status line, cached so redraws stay cheap.

The status line redraws constantly, so anything that costs a subprocess is read
through `probe()` and reused for a few seconds. Measured costs on this machine:
`ps -eo` ~29ms, `git stash list` ~15ms, `vm_stat` ~6ms, `sysctl` ~4ms,
`os.statvfs` ~0ms. Uncached that is ~55ms per redraw; cached it is ~0.
"""
import json
import math
import os
import subprocess
import time
from collections.abc import Mapping

from agent_statusline.paths import state
from agent_statusline.storage import read_json, update_json

STATE = state("statusline-probe-cache.json")
MAX_CACHE_AGE_S = 7 * 24 * 60 * 60
MAX_CACHE_ENTRIES = 256


def _observed_at(row, now):
    if not isinstance(row, Mapping):
        return None
    observed = row.get("at")
    if isinstance(observed, bool) or not isinstance(observed, (int, float)):
        return None
    try:
        if not math.isfinite(observed) or observed > now:
            return None
    except OverflowError:
        return None
    return observed


def _prune(cache, now, active_key):
    """Discard stale rows and retain the active row plus newest observations."""
    changed = False
    observed = {}
    for key, row in list(cache.items()):
        at = _observed_at(row, now)
        if at is None or now - at > MAX_CACHE_AGE_S:
            del cache[key]
            changed = True
        else:
            observed[key] = at

    if len(cache) > MAX_CACHE_ENTRIES:
        remove = len(cache) - MAX_CACHE_ENTRIES
        candidates = sorted(
            (key for key in cache if key != active_key),
            key=lambda key: (observed[key], str(key)),
        )
        for key in candidates[:remove]:
            del cache[key]
        changed = True
    return changed


def _fresh(row, now, ttl):
    observed = _observed_at(row, now)
    return observed is not None and now - observed < ttl


def probe(key, ttl, fn):
    """Run fn() at most once per ttl seconds, persisting the result across renders."""
    now = time.time()
    try:
        cache = read_json(STATE, {})
    except Exception:
        cache = {}
    maintenance_needed = _prune(cache, now, key)
    row = cache.get(key)
    cached = _fresh(row, now, ttl)
    if cached and not maintenance_needed:
        return row.get("val")
    if cached:
        val = row.get("val")
    else:
        try:
            val = fn()
        except Exception:
            val = None

    def publish(current):
        transaction_now = time.time()
        changed = _prune(current, transaction_now, key)
        existing = current.get(key)
        if _fresh(existing, transaction_now, ttl):
            return changed, existing.get("val")
        current[key] = {"at": transaction_now, "val": val}
        _prune(current, transaction_now, key)
        return True, val

    try:
        return update_json(STATE, {}, publish)
    except Exception:
        return val


def _run(*args, timeout=1.0):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r.stdout if r.returncode == 0 else ""


def _is_claude(cmd):
    tok = cmd.split(" ", 1)[0]
    base = os.path.basename(tok)
    return (
        base == "claude"
        or tok.endswith("/claude")
        or "ClaudeCode.app" in tok
        or ("/share/claude/versions/" in tok)
    )


def processes():
    """One `ps` sweep -> this session's RSS, and the total across all claude processes.

    'This session' is found by walking up the parent chain from the status-line
    process until a claude process is hit, so it is the real session process
    rather than a guess.
    """
    out = _run("ps", "-eo", "pid=,ppid=,rss=,command=")
    if not out:
        return None
    ppid, rss, cmd = {}, {}, {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            p, pp, rs = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue
        ppid[p], rss[p], cmd[p] = pp, rs * 1024, parts[3]

    claude = {p for p, c in cmd.items() if _is_claude(c)}
    mine, cur, seen = None, os.getpid(), 0
    while cur in ppid and seen < 40:
        if cur in claude:
            mine = cur
            break
        cur = ppid[cur]
        seen += 1
    # Everything the session process spawned counts toward its footprint.
    kids, total_mine = {mine} if mine else set(), 0
    if mine:
        changed = True
        while changed:
            changed = False
            for p, pp in ppid.items():
                if pp in kids and p not in kids:
                    kids.add(p)
                    changed = True
        total_mine = sum(rss.get(p, 0) for p in kids)
    return {
        "mine_rss": total_mine,
        "mine_pid": mine,
        "mine_procs": len(kids),
        "all_rss": sum(rss.get(p, 0) for p in claude),
        "all_n": len(claude),
    }


def memory():
    """System memory: total, and a used fraction from vm_stat page counts."""
    total = _run("sysctl", "-n", "hw.memsize").strip()
    total = int(total) if total.isdigit() else 0
    vm = _run("vm_stat")
    if not vm:
        return {"total": total}
    page = 4096
    first = vm.splitlines()[0]
    if "page size of" in first:
        try:
            page = int(first.split("page size of")[1].split()[0])
        except Exception:
            pass
    vals = {}
    for line in vm.splitlines()[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().rstrip(".")
        if v.isdigit():
            vals[k.strip()] = int(v) * page
    used = (
        vals.get("Pages active", 0)
        + vals.get("Pages wired down", 0)
        + vals.get("Pages occupied by compressor", 0)
    )
    return {
        "total": total,
        "used": used,
        "pct": (used / total * 100) if total else None,
        "compressed": vals.get("Pages occupied by compressor", 0),
    }


def disk(path):
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    return {"free": free, "total": total, "pct": ((total - free) / total * 100) if total else None}


def git_state(cwd):
    """Whole git picture in as few subprocesses as possible.

    `status --porcelain=v2 --branch` yields branch, upstream, ahead/behind and
    dirtiness in a single call -- four separate git invocations used to cost ~63ms
    per redraw, which was the dominant source of status-line flicker.
    Returns None when cwd is not a repository.
    """
    out = _run("git", "-C", cwd, "status", "--porcelain=v2", "--branch", "--untracked-files=no")
    if not out:
        return None
    branch, ahead, behind, dirty, upstream = None, 0, 0, False, False
    for line in out.splitlines():
        if line.startswith("# branch.head "):
            branch = line[len("# branch.head ") :].strip()
        elif line.startswith("# branch.upstream "):
            upstream = True
        elif line.startswith("# branch.ab "):
            for piece in line[len("# branch.ab ") :].split():
                if piece.startswith("+"):
                    ahead = int(piece[1:])
                elif piece.startswith("-"):
                    behind = int(piece[1:])
        elif not line.startswith("#"):
            dirty = True
    if branch is None:
        return None
    rp = _run("git", "-C", cwd, "rev-parse", "--git-dir", "--git-common-dir").split()
    worktree = len(rp) == 2 and os.path.abspath(os.path.join(cwd, rp[0])) != os.path.abspath(
        os.path.join(cwd, rp[1])
    )
    stash = _run("git", "-C", cwd, "stash", "list")
    return {
        "branch": branch,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "upstream": upstream,
        "worktree": worktree,
        "stash": len([l for l in stash.splitlines() if l.strip()]),
    }


def account():
    """Credit-related account flags from ~/.claude.json.

    There is NO credit balance anywhere on disk, and none in the status-line
    payload -- `rate_limits` carries only `used_percentage` and `resets_at`, even
    while an account is over its limit. `/usage-credits` fetches the balance from
    the server interactively. So the most that can be reported locally is whether
    credits are switched on, and which models are exempt from drawing them.
    """
    with open(os.path.expanduser("~/.claude.json")) as fh:
        d = json.load(fh)
    oa = d.get("oauthAccount") or {}
    gb = d.get("cachedGrowthBookFeatures") or {}
    return {
        "enabled": bool(oa.get("hasExtraUsageEnabled")),
        "disabled_reason": d.get("cachedExtraUsageDisabledReason"),
        "included_models": gb.get("tengu_usage_overage_included_models") or [],
    }
