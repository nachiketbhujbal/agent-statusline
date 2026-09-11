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
import math
import os
import time
from collections.abc import Mapping

from agent_statusline.coerce import finite_integer
from agent_statusline.paths import state
from agent_statusline.storage import update_json

TSTATE = state("statusline-transcript.json")

SCHEMA = 3
CACHE_RETENTION_S = 35 * 24 * 60 * 60
CACHE_TOUCH_S = 60 * 60
MAX_CACHED_TRANSCRIPTS = 512


def _accessed_at(row, now):
    if not isinstance(row, Mapping):
        return None
    accessed = row.get("accessed_at")
    if isinstance(accessed, bool) or not isinstance(accessed, (int, float)):
        return None
    try:
        if not math.isfinite(accessed) or accessed < 0 or accessed > now:
            return None
    except OverflowError:
        return None
    return accessed


def _maintain_cache(cache, path, now):
    """Touch the active transcript and prune invalid, old, or excess rows."""
    changed = False
    raw_row = cache.get(path)
    row = dict(raw_row) if isinstance(raw_row, Mapping) else {}
    if raw_row != row or path not in cache:
        cache[path] = row
        changed = True

    accessed = _accessed_at(row, now)
    if accessed is None or now - accessed >= CACHE_TOUCH_S:
        row["accessed_at"] = now
        cache[path] = row
        changed = True

    observed = {path: row["accessed_at"]}
    for cached_path, cached_row in list(cache.items()):
        if cached_path == path:
            continue
        if not isinstance(cached_row, Mapping):
            del cache[cached_path]
            changed = True
            continue
        normalized = dict(cached_row)
        last_access = _accessed_at(normalized, now)
        if last_access is None:
            last_access = now
            normalized["accessed_at"] = now
            cache[cached_path] = normalized
            changed = True
        if now - last_access > CACHE_RETENTION_S:
            del cache[cached_path]
            changed = True
        else:
            observed[cached_path] = last_access

    if len(cache) > MAX_CACHED_TRANSCRIPTS:
        remove = len(cache) - MAX_CACHED_TRANSCRIPTS
        candidates = sorted(
            (key for key in cache if key != path),
            key=lambda key: (observed[key], str(key)),
        )
        for key in candidates[:remove]:
            del cache[key]
        changed = True
    return row, changed


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


_COUNT_FIELDS = (
    "in",
    "cw",
    "cr",
    "out",
    "turns",
    "think",
    "b1h",
    "b5m",
    "errors",
    "synth",
    "side",
    "compact",
    "hook_runs",
    "hook_errs",
)
_COUNT_MAP_FIELDS = ("tools", "cmds")
_PATH_LIST_FIELDS = ("f_edit", "f_read")
_COUNT_LIST_FIELDS = ("durs", "hook_ms")
_STRING_FIELDS = ("last_ts", "perm", "tier", "last_bucket")


def _normalized_totals(value):
    """Return a complete safe totals mapping from package-owned cache state."""
    normalized = _blank()
    if not isinstance(value, Mapping):
        return normalized
    for key in _COUNT_FIELDS:
        normalized[key] = max(0, finite_integer(value.get(key)))
    for key in _COUNT_MAP_FIELDS:
        current = value.get(key)
        if isinstance(current, Mapping):
            normalized[key] = {
                name: max(0, finite_integer(count))
                for name, count in current.items()
                if isinstance(name, str)
            }
    for key in _PATH_LIST_FIELDS:
        current = value.get(key)
        if isinstance(current, list):
            normalized[key] = [item for item in current if isinstance(item, str)]
    for key in _COUNT_LIST_FIELDS:
        current = value.get(key)
        if isinstance(current, list):
            normalized[key] = [max(0, finite_integer(item)) for item in current]
    for key in _STRING_FIELDS:
        current = value.get(key)
        if isinstance(current, str):
            normalized[key] = current
    if normalized["last_bucket"] not in (None, "1h", "5m"):
        normalized["last_bucket"] = None
    return normalized


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
    computed = z
    now = time.time()

    def absorb_new(cache):
        nonlocal computed
        row, changed = _maintain_cache(cache, path, now)
        raw_row = dict(row)
        root = row.get("root") if isinstance(row.get("root"), str) else None
        if row.get("schema") == SCHEMA:
            offset_value = row.get("offset")
            if (
                isinstance(offset_value, int)
                and not isinstance(offset_value, bool)
                and offset_value >= 0
                and isinstance(row.get("totals"), Mapping)
            ):
                offset = offset_value
                totals = _normalized_totals(row.get("totals"))
            else:
                offset, totals = 0, _blank()
        else:
            offset, totals = 0, _blank()
        computed = totals
        normalized_row = {
            "offset": offset,
            "totals": totals,
            "schema": SCHEMA,
            "root": root,
            "accessed_at": row["accessed_at"],
        }
        normalized = raw_row != normalized_row

        try:
            size = os.stat(path).st_size
        except Exception:
            if normalized:
                cache[path] = normalized_row
            return changed or normalized, totals
        if size < offset:
            offset, totals = 0, _blank()
            computed = totals
        if size == offset:
            row = {
                "offset": offset,
                "totals": totals,
                "schema": SCHEMA,
                "root": root,
                "accessed_at": normalized_row["accessed_at"],
            }
            if normalized or raw_row != row:
                cache[path] = row
                return True, totals
            return changed, totals
        try:
            with open(path, "rb") as fh:
                fh.seek(offset)
                chunk = fh.read()
                new_offset = fh.tell()
        except Exception:
            if normalized:
                cache[path] = normalized_row
            return changed or normalized, totals
        if not chunk.endswith(b"\n"):
            cut = chunk.rfind(b"\n")
            if cut == -1:
                if normalized:
                    cache[path] = normalized_row
                return changed or normalized, totals
            tail = chunk[cut + 1 :]
            chunk = chunk[: cut + 1]
            new_offset -= len(tail)
        for line in chunk.split(b"\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if not isinstance(entry, dict):
                continue
            _absorb(totals, entry)
        cache[path] = {
            "offset": new_offset,
            "totals": totals,
            "schema": SCHEMA,
            "root": root,
            "accessed_at": normalized_row["accessed_at"],
        }
        return True, totals

    try:
        return update_json(TSTATE, {}, absorb_new)
    except OSError:
        # Cache persistence is optional. Unsafe entries and failed publications
        # stay refused by storage, while this redraw retains only a result that
        # was already computed inside the failed transaction.
        return computed


def conversation_root(path):
    """First user message uuid -- identical across forks of one conversation."""
    if not path or not os.path.exists(path):
        return None
    computed = None
    now = time.time()

    def discover(cache):
        nonlocal computed
        row, changed = _maintain_cache(cache, path, now)
        cached_root = row.get("root")
        if isinstance(cached_root, str) and cached_root:
            computed = cached_root
            return changed, cached_root
        if "root" in row:
            row.pop("root")
            changed = True
        root = None
        try:
            with open(path) as fh:
                for number, line in enumerate(fh):
                    if number > 400:
                        break
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(entry, dict):
                        continue
                    uuid_value = entry.get("uuid")
                    if entry.get("type") == "user" and isinstance(uuid_value, str) and uuid_value:
                        root = uuid_value
                        break
        except Exception:
            return changed, None
        if root:
            row["root"] = root
            changed = True
        computed = root
        return changed, root

    try:
        return update_json(TSTATE, {}, discover)
    except OSError:
        return computed
