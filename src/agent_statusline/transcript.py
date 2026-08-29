"""Incremental parsing of a session transcript (.jsonl).

Each redraw reads only the bytes appended since the last one: `paths` holds a
byte offset plus the accumulated totals per transcript. SCHEMA versions the
shape of those totals -- bump it whenever a field is added or changed, or
existing caches keep their old shape and the new field stays empty forever with
no error anywhere.

Field names here were verified against real transcripts. They are documented
nowhere else; do not guess at them (see docs/INTERNALS.md).
"""

import datetime
import json
import os
from collections.abc import Mapping

from agent_statusline.coerce import finite_integer
from agent_statusline.paths import state

TSTATE = state("statusline-transcript.json")

SCHEMA = 3


def dig(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return default if d is None else d


def iso_epoch(ts):
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


# ---------- cumulative session facts, parsed incrementally ----------
def _blank():
    return {
        "in": 0,
        "cw": 0,
        "cr": 0,
        "out": 0,
        "turns": 0,
        "last_ts": None,
        "think": 0,
        "b1h": 0,
        "b5m": 0,
        "tools": {},
        "errors": 0,
        "synth": 0,
        "f_edit": [],
        "f_read": [],
        "side": 0,
        "compact": 0,
        "durs": [],
        "hook_runs": 0,
        "hook_ms": [],
        "hook_errs": 0,
        "cmds": {},
        "perm": None,
        "tier": None,
        "last_bucket": None,
    }


def _absorb(tot, e):
    t = e.get("type")
    if e.get("isSidechain"):
        tot["side"] += 1
    if e.get("permissionMode"):
        tot["perm"] = e["permissionMode"]
    if (t and "compact" in str(t).lower()) or e.get("isCompactSummary"):
        tot["compact"] += 1

    if t == "system":
        st = e.get("subtype")
        if st == "turn_duration" and e.get("durationMs"):
            duration = finite_integer(e["durationMs"])
            if duration:
                tot["durs"].append(duration)
            tot["durs"] = tot["durs"][-60:]
        elif st == "stop_hook_summary":
            infos = e.get("hookInfos") or []
            infos = [h for h in infos if isinstance(h, Mapping)] if isinstance(infos, list) else []
            errors = e.get("hookErrors") or []
            errors = errors if isinstance(errors, list) else []
            tot["hook_runs"] += len(infos)
            tot["hook_ms"] = (
                tot["hook_ms"] + [finite_integer(h.get("durationMs")) for h in infos]
            )[-60:]
            tot["hook_errs"] += len(errors)
        elif st == "local_command":
            c = e.get("content") or ""
            if not isinstance(c, str):
                return
            i, j = c.find("<command-name>"), c.find("</command-name>")
            if 0 <= i < j:
                name = c[i + 14 : j].strip()
                tot["cmds"][name] = tot["cmds"].get(name, 0) + 1
        return

    m = e.get("message") or {}
    if not isinstance(m, Mapping):
        m = {}
    body = m.get("content")
    if isinstance(body, list):
        for b in body:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                name_value = b.get("name")
                n = name_value if isinstance(name_value, str) and name_value else "?"
                tot["tools"][n] = tot["tools"].get(n, 0) + 1
                inp = b.get("input") or {}
                if not isinstance(inp, Mapping):
                    inp = {}
                fp = inp.get("file_path") or inp.get("notebook_path")
                if fp:
                    key = "f_edit" if n in ("Edit", "Write", "NotebookEdit") else "f_read"
                    if fp not in tot[key] and len(tot[key]) < 400:
                        tot[key].append(fp)
            elif b.get("type") == "tool_result" and b.get("is_error"):
                tot["errors"] += 1

    if t != "assistant":
        return
    if m.get("model") == "<synthetic>":
        tot["synth"] += 1
    u = m.get("usage") or {}
    if not isinstance(u, Mapping) or not u:
        return
    tot["in"] += finite_integer(u.get("input_tokens"))
    tot["cw"] += finite_integer(u.get("cache_creation_input_tokens"))
    tot["cr"] += finite_integer(u.get("cache_read_input_tokens"))
    tot["out"] += finite_integer(u.get("output_tokens"))
    tot["turns"] += 1
    tot["think"] += finite_integer(dig(u, "output_tokens_details", "thinking_tokens"))
    cc = u.get("cache_creation") or {}
    if not isinstance(cc, Mapping):
        cc = {}
    h1 = finite_integer(cc.get("ephemeral_1h_input_tokens"))
    m5 = finite_integer(cc.get("ephemeral_5m_input_tokens"))
    tot["b1h"] += h1
    tot["b5m"] += m5
    # Which bucket the newest write landed in is the live TTL. Cumulative sums lag:
    # an account crossing into usage overage switches from 1h to 5m mid-session.
    if h1 or m5:
        tot["last_bucket"] = "1h" if h1 >= m5 else "5m"
    if u.get("service_tier"):
        tot["tier"] = u["service_tier"]
    if e.get("timestamp"):
        tot["last_ts"] = e["timestamp"]


def transcript_totals(path):
    z = _blank()
    if not path or not os.path.exists(path):
        return z
    try:
        st = os.stat(path)
    except Exception:
        return z
    state = {}
    try:
        with open(TSTATE) as fh:
            state = json.load(fh)
    except Exception:
        pass
    row = state.get(path) or {}
    if row.get("schema") != SCHEMA:
        row = {}
    off = row.get("offset", 0)
    tot = row.get("totals") or _blank()
    for k, v in _blank().items():
        tot.setdefault(k, v)
    if st.st_size < off:
        off, tot = 0, _blank()
    if st.st_size == off:
        return tot
    try:
        with open(path, "rb") as fh:
            fh.seek(off)
            chunk = fh.read()
            newoff = fh.tell()
    except Exception:
        return tot
    tail = b""
    if not chunk.endswith(b"\n"):
        cut = chunk.rfind(b"\n")
        if cut == -1:
            return tot
        tail = chunk[cut + 1 :]
        chunk = chunk[: cut + 1]
        newoff -= len(tail)
    for line in chunk.split(b"\n"):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        _absorb(tot, e)
    prev = state.get(path) or {}
    state[path] = {"offset": newoff, "totals": tot, "schema": SCHEMA, "root": prev.get("root")}
    try:
        tmp = TSTATE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(state, fh)
        os.replace(tmp, TSTATE)
    except Exception:
        pass
    return tot


def conversation_root(path):
    """First user message uuid -- identical across forks of one conversation."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(TSTATE) as fh:
            st = json.load(fh)
    except Exception:
        st = {}
    row = st.get(path) or {}
    cached_root = row.get("root")
    if isinstance(cached_root, str) and cached_root:
        return cached_root
    root = None
    try:
        with open(path) as fh:
            for i, line in enumerate(fh):
                if i > 400:
                    break
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if not isinstance(e, dict):
                    continue
                uuid_value = e.get("uuid")
                if e.get("type") == "user" and isinstance(uuid_value, str) and uuid_value:
                    root = uuid_value
                    break
    except Exception:
        return None
    if root:
        row["root"] = root
        st[path] = row
        try:
            tmp = TSTATE + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(st, fh)
            os.replace(tmp, TSTATE)
        except Exception:
            pass
    return root
