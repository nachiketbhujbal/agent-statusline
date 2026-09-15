#!/usr/bin/env python3
"""The Claude Code status line: ten labelled rows, fitted to the terminal.

Rows are ordered by how often they answer a question worth asking, not by how
the data happens to arrive -- see ORDER below. Every value is already in the
payload, comes from an incremental transcript read, or is a cached probe.

Run directly; no install step is required:

    python3 -m agent_statusline.statusline < payload.json
"""
import json
import math
import os
import sys
import time
from collections.abc import Mapping

if __package__ in (None, ""):  # running as a plain script from a checkout
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from agent_statusline import ledger
from agent_statusline import probes as pr
from agent_statusline.acquisition import claude_facts
from agent_statusline.coerce import finite_integer, finite_number
from agent_statusline.paths import state
from agent_statusline.render import (
    BLU,
    CYN,
    GRN,
    GRY,
    MAG,
    RED,
    YEL,
    B,
    D,
    R,
    bar,
    dur,
    gb,
    grade,
    plain,
    row,
    tok,
)
from agent_statusline.storage import append_json_if_changed, write_text
from agent_statusline.transcript import (
    conversation_root,
    dig,
    iso_epoch,
    transcript_totals,
)

LEDGER = ledger.LEDGER
RLHIST = state("rate-limit-history.jsonl")
PAYLOAD = state("statusline-last-payload.json")
RATE_HISTORY_MAX_BYTES = 1024 * 1024

# Server-side prompt cache TTL. Detected from the usage block's cache_creation
# buckets (ephemeral_1h vs ephemeral_5m); this is only the fallback.
CACHE_TTL_S = 3600
# Provider-defined cache billing ratios, NOT prices -- safe to hardcode where a
# $/token table would silently drift. Used only for the effective multiplier.
W_READ, W_WRITE, W_FRESH = 0.1, 1.25, 1.0

# Permission-mode colours and labels, read out of Claude Code v2.1.246 itself so
# this field matches the indicator under the prompt instead of inventing a scheme:
#   default->inactive(grey)  plan->planMode(cyan)  acceptEdits->autoAccept(magenta)
#   auto->warning(yellow)    bypassPermissions/dontAsk->error(red)
MODES = {
    "default": (GRY, "manual"),
    "plan": (CYN, "plan"),
    "acceptEdits": (MAG, "accept edits"),
    "auto": (YEL, "auto"),
    "bypassPermissions": (RED, "bypass permissions"),
    "dontAsk": (RED, "don't ask"),
}

# Top-to-bottom row order. Rows are built into a dict keyed by these names and
# emitted in this sequence, so reordering is a one-line change here rather than
# a reshuffle of main(). Rows with nothing to say are simply absent.
ORDER = [
    "PROJECT",
    "MODEL",
    "CONTEXT",
    "USAGE",
    "COST",
    "SYSTEM",
    "TOOLS",
    "CACHE",
    "TOKENS",
    "TIMING",
]


def ledger_update(
    sid,
    cost,
    project,
    name,
    root=None,
    pid=None,
    accrued_at=None,
    duration=None,
):
    # Timestamps are ISO 8601 local-with-offset (see ledger.py); every comparison
    # goes through ledger.epoch so legacy numeric rows still sort correctly.
    computed_result = None

    def mutate(data):
        nonlocal computed_result
        sessions = data["sessions"]
        now = time.time()
        stamp = ledger.iso(now)
        previous = sessions.get(sid, {})
        previous_cost = previous.get("cost", 0.0)
        session_cost = previous_cost
        changed = False
        if cost is not None:
            # Seed every lifetime that predates the journal before applying the
            # current payload increase. This keeps historical money non-accrual
            # without losing a newly observed, timestamped positive delta.
            changed = (
                ledger.record_cost_delta(
                    data, sid, previous_cost, previous_cost, now, accrued_at=accrued_at
                )
                or changed
            )
            entry = {
                **previous,
                "updated": stamp,
                "state": "live",
                "project": project,
                "name": name,
                **({"root": root} if root else {}),
            }
            if "started" not in previous:
                elapsed = finite_number(duration) if duration is not None else 0.0
                if 0 < elapsed <= now:
                    entry["started"] = ledger.iso(now - elapsed)
            if not isinstance(entry.get("root"), str):
                entry.pop("root", None)
            # Lifetime cost, carried across runs. Resuming a closed row makes it live
            # again; `closed` is left in place as the last close time.
            session_cost = ledger.apply_cost(entry, cost, pid)
            sessions[sid] = entry
            changed = (
                abs(previous.get("cost", -1) - session_cost) > 1e-9
                or previous.get("state") != "live"
                or changed
            )
            changed = (
                ledger.record_cost_delta(
                    data,
                    sid,
                    previous_cost,
                    session_cost,
                    now,
                    accrued_at=accrued_at,
                )
                or changed
            )
        rows = sorted(
            sessions.values(), key=lambda row: ledger.epoch(row.get("updated")), reverse=True
        )
        rolling = ledger.rolling_costs(data, now)

        # A row counts as a real session only if it produced something: a cost, or a
        # readable transcript (its conversation root).
        real = [
            row
            for row in rows
            if row.get("cost", 0) > 0 or (isinstance(row.get("root"), str) and row["root"])
        ]
        conversations = {
            row["root"] if isinstance(row.get("root"), str) and row["root"] else id(row)
            for row in real
        }
        result = {
            "all": sum(row.get("cost", 0) for row in rows),
            "n": len(real),
            "convos": len(conversations),
            "forks": max(0, len(real) - len(conversations)),
            "last5": sum(row.get("cost", 0) for row in rows[:5]),
            "session": session_cost,
            "base": sessions.get(sid, {}).get("cost_base", 0.0),
            "runs": sessions.get(sid, {}).get("runs", 1),
            **rolling,
        }
        computed_result = result
        return changed, result

    try:
        return ledger.update(mutate)
    except OSError:
        # State is optional display metadata. Preserve the render when a private
        # state transaction fails, without claiming that the update was published.
        # Publication happens after the updater, so retain its exact-money result
        # when available rather than discarding already-read historical totals.
        if computed_result is not None:
            return computed_result
        fallback = mutate({"sessions": {}})[1]
        # The current payload is still a useful lower bound, but a transaction
        # that failed before the updater ran could have hidden any amount of
        # historical spend. Never label that fallback as an exact window.
        for key in ledger.COST_WINDOWS:
            fallback[key + "_complete"] = False
        return fallback


def rl_log(node5, node7):
    """Append rate-limit readings, but only when one actually changes.

    Exists to settle an open question: whether `used_percentage` keeps climbing past
    100% or pins near it once an account is in credit-funded overage. Nothing on disk
    or in the binary answers that, so it is being measured. Writes a few bytes per
    change, nothing on an unchanged render.
    """
    try:

        def optional_number(value):
            return None if value is None else finite_number(value)

        cur = {
            "5h": optional_number(dig(node5, "used_percentage")),
            "5h_reset": optional_number(dig(node5, "resets_at")),
            "7d": optional_number(dig(node7, "used_percentage")),
            "7d_reset": optional_number(dig(node7, "resets_at")),
        }
        cur["at"] = ledger.iso()
        append_json_if_changed(
            RLHIST,
            cur,
            ("5h", "5h_reset", "7d", "7d_reset"),
            max_bytes=RATE_HISTORY_MAX_BYTES,
        )
    except Exception:
        pass


def limit_seg(label, node, window_h):
    pct = finite_number(dig(node, "used_percentage", default=0) or 0)
    reset_value = dig(node, "resets_at")
    resets = None if reset_value is None else finite_number(reset_value)
    shown_pct = math.floor(pct)
    s = f"{D}{label:<3}{R}{bar(pct)} {grade(pct)}{shown_pct:3d}%{R}"
    if resets:
        try:
            clock = time.strftime("%a %H:%M", time.localtime(resets))
        except (OverflowError, OSError, ValueError):
            resets = None
    if resets:
        left = resets - time.time()
        if pct < 100:
            elapsed = max(0.05, window_h - left / 3600)
            burn = pct / elapsed
            proj = burn * window_h
            pc = RED if proj >= 100 else YEL if proj >= 80 else GRN
            s += f" {D}@{R}{burn:.1f}{D}%/h{R} {D}▸{R} {pc}{proj:.0f}%{R}"
        else:
            # Past 100% the included allowance is already spent, so a burn rate and a
            # projection derived from this number say nothing useful -- and the number
            # itself may be pinned rather than climbing (see rate-limit-history.jsonl).
            s += f" {RED}{B}+{pct-100:.0f}% over{R}"
        s += f" {D}(reset {clock} | {dur(left)}){R}"
    return s


def _render():
    raw = sys.stdin.read()
    try:
        write_text(PAYLOAD, raw)
    except Exception:
        pass
    try:
        d = json.loads(raw)
    except Exception:
        print(f"{D}claude{R}")
        return
    if not isinstance(d, Mapping):
        print(f"{D}claude{R}")
        return
    facts = claude_facts(d, transcript_totals, os.getcwd())
    identity = facts["identity"]
    workspace = facts["workspace"]
    model_facts = facts["model"]
    context = facts["context"]
    limits = facts["limits"]
    money = facts["money"]
    rows = {}
    transcript_path = facts["transcript_path"]
    t = facts["activity"]

    # ---------- rows 1-2: project/git, then model + mode flags ----------
    pj = []
    p1 = []
    model = model_facts.get("display_name") or model_facts.get("id") or "claude"
    eff = model_facts.get("effort")
    p1.append(f"{MAG}{B}{plain(model)}{R}" + (f"{D}:{plain(eff)}{R}" if eff else ""))
    p1.append(f"{GRN}think{R}" if model_facts.get("thinking") else f"{YEL}no-think{R}")
    # fast mode is shown either way: silence would hide that it is on
    p1.append(f"{RED}{B}FAST ON{R}" if model_facts.get("fast_mode") else f"{D}fast off{R}")
    perm = model_facts.get("permission_mode")
    if perm:
        pc, plab = MODES.get(perm, (D, perm))
        p1.append(f"{pc}{plain(plab)}{R}" if perm == "default" else f"{pc}{B}{plain(plab)}{R}")
    style = model_facts.get("output_style")
    if style and style != "default":
        p1.append(f"{CYN}{plain(style)}{R}")
    if model_facts.get("service_tier") and model_facts["service_tier"] != "standard":
        p1.append(f"{YEL}{plain(model_facts['service_tier'])}{R}")
    ver = identity.get("client_version")
    if ver:
        p1.append(f"{D}v{plain(ver)}{R}")

    cwd = workspace["cwd"]
    project_path = workspace["project_dir"]
    proj = os.path.basename(project_path)
    here = os.path.basename(cwd)
    pj.append(
        f"{BLU}{B}{plain(proj)}{R}"
        if here == proj
        else f"{BLU}{B}{plain(proj)}{R}{D}/{R}{BLU}{plain(here)}{R}"
    )
    extra = workspace["added_dirs"]
    if extra:
        pj.append(f"{D}+{len(extra)} dir{'s' if len(extra)!=1 else ''}{R}")

    # One cached probe covers branch, dirtiness, ahead/behind, worktree and stash.
    gs = pr.probe(f"git:{cwd}", 3, lambda c=cwd: pr.git_state(c))
    nested = False
    git_cwd = cwd
    if not gs:
        # cwd is not a repo: if exactly one child directory is one, show its branch
        # marked with an arrow so it cannot be mistaken for the current directory's.
        try:
            cands = [
                e.path
                for e in os.scandir(cwd)
                if e.is_dir() and os.path.isdir(os.path.join(e.path, ".git"))
            ]
        except Exception:
            cands = []
        if len(cands) == 1:
            gs = pr.probe(f"git:{cands[0]}", 3, lambda c=cands[0]: pr.git_state(c))
            if gs:
                git_cwd = cands[0]
                nested = True
    if gs:
        br = gs["branch"]
        g = (
            f"{D}↳{plain(os.path.basename(git_cwd))} {R}" if nested else ""
        ) + f"{RED if br in ('main','master') else GRN}{plain(br)}{R}"
        if gs.get("dirty"):
            g += f"{YEL}*{R}"
        if gs.get("worktree"):
            g += f"{CYN}⑂wt{R}"
        if gs.get("upstream"):
            if gs.get("ahead"):
                g += f"{D}↑{R}{GRN}{gs['ahead']}{R}"
            if gs.get("behind"):
                g += f"{D}↓{R}{RED}{gs['behind']}{R}"
            if not gs.get("ahead") and not gs.get("behind"):
                g += f"{D}≡{R}"
        else:
            g += f"{D}(no upstream){R}"
        if gs.get("stash"):
            g += f" {D}stash{R}{YEL}{gs['stash']}{R}"
        pj.append(g)
    else:
        pj.append(f"{D}no git{R}")
    nm = identity.get("session_title")
    if nm:
        pj.append(f"{D}“{plain(nm)}”{R}")
    rows["PROJECT"] = row("PROJECT", pj)
    rows["MODEL"] = row("MODEL", p1)

    # ---------- row 2: context + both rate-limit windows ----------
    size = context["window_size"]
    upct = context["used_percentage"]
    cur = context["current_tokens"]
    live = sum(
        finite_integer(cur.get(k) or 0)
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )
    t_cr = finite_integer(t.get("cr"))
    t_cw = finite_integer(t.get("cw"))
    t_in = finite_integer(t.get("in"))
    t_out = finite_integer(t.get("out"))
    t_think = finite_integer(t.get("think"))
    t_turns = finite_integer(t.get("turns"))
    served = t_cr + t_cw + t_in

    # Context and this session's own token throughput belong together; the rate-limit
    # windows are account-wide and get their own row so both stay easy to scan.
    segs = []
    if size:
        c = f"{D}ctx{R}{bar(upct)} {grade(upct)}{B}{upct:4.0f}%{R} {D}{tok(live)}/{tok(size)}{R}"
        if upct >= 80:
            c += f" {RED}{B}⚠{R}"
        segs.append(c)
    sess = [f"{D}session{R} {CYN}{tok(served)}{R}{D} in{R}", f"{CYN}{tok(t_out)}{R}{D} out{R}"]
    if t_think:
        sess.append(f"{MAG}{tok(t_think)}{R}{D} thinking{R}")
    sess.append(f"{t_turns}{D} api turns{R}")
    if t_turns:
        sess.append(
            f"{D}avg{R} {tok(served//t_turns)}{D}/{R}{tok(t_out//t_turns)}" f"{D} per turn{R}"
        )
    segs.append(f" {D}·{R} ".join(sess))
    if segs:
        rows["CONTEXT"] = row("CONTEXT", segs)

    lim = []
    fh_ = limits.get("five_hour")
    over_pct = finite_number(dig(fh_, "used_percentage", default=0) or 0) if fh_ else 0.0
    over_active = over_pct >= 100
    if fh_:
        seg = limit_seg("5h", fh_, 5)
        if over_active:
            seg += f" {RED}{B}OVERAGE{R}"
        lim.append(seg)
    if limits.get("seven_day"):
        lim.append(limit_seg("7d", limits["seven_day"], 168))
    if lim:
        rows["USAGE"] = row("USAGE", lim)
    rl_log(fh_, limits.get("seven_day"))

    # ---------- row 3: cache economics ----------
    if served:
        hit = t_cr / served * 100
        hc = GRN if hit >= 80 else YEL if hit >= 50 else RED
        r3 = [f"{hc}{B}{hit:.1f}%{R}{D} hit{R}"]
        # TTL is detected from which ephemeral bucket the writes landed in, so this
        # is observed rather than assumed. Falls back to CACHE_TTL_S if neither.
        ttl = CACHE_TTL_S
        win = "1h"
        obs = False
        if t.get("last_bucket"):
            win = t["last_bucket"]
            ttl = 3600 if win == "1h" else 300
            obs = True
        age = None
        if t.get("last_ts"):
            ep = iso_epoch(t["last_ts"])
            if ep:
                age = time.time() - ep
        wc = RED if win == "5m" else GRN
        w = f"{wc}{B}{win}{R}{D} ttl{R}" + ("" if obs else f"{D} (assumed){R}")
        if age is not None and age >= 0:
            if age >= ttl:
                w += f" {RED}{B}COLD{R}{D} — next turn re-sends everything{R}"
            else:
                w += (
                    f"{D} ▸ expires {R}{time.strftime('%H:%M',time.localtime(time.time()-age+ttl))}"
                )
        r3.append(w)
        eff = (t_cr * W_READ + t_cw * W_WRITE + t_in * W_FRESH) / served
        ec = GRN if eff <= 0.4 else YEL if eff <= 0.8 else RED
        r3.append(f"{ec}{eff:.2f}x{R}{D} vs all-uncached{R}")
        t_b1h = finite_integer(t.get("b1h"))
        t_b5m = finite_integer(t.get("b5m"))
        if t_b1h or t_b5m:
            r3.append(f"{D}writes{R} {tok(t_b1h)}{D} 1h ·{R} {tok(t_b5m)}{D} 5m{R}")
        rows["CACHE"] = row("CACHE", r3)

        # ---------- row 4: token flow ----------
        cur_cr = finite_integer(cur.get("cache_read_input_tokens"))
        cur_cw = finite_integer(cur.get("cache_creation_input_tokens"))
        cur_in = finite_integer(cur.get("input_tokens"))
        rows["TOKENS"] = row(
            "TOKENS",
            [
                f"{D}total{R} {GRN}{tok(t_cr)}{R}{D} reused{R} {D}·{R} "
                f"{YEL}{tok(t_cw)}{R}{D} written{R} {D}·{R} "
                f"{RED}{tok(t_in)}{R}{D} uncached{R}",
                f"{D}turn{R} {GRN}{tok(cur_cr)}{R}{D} reused{R} "
                f"{D}·{R} "
                f"{YEL}{tok(cur_cw)}{R}{D} written{R} {D}·{R} "
                f"{RED}{tok(cur_in)}{R}{D} uncached{R}",
            ],
        )

    # ---------- row 5: what this session actually did ----------
    tools = t["tools"]
    ntool = sum(tools.values())
    r5 = [f"{B}{ntool}{R}{D} calls{R}"]
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:4]
        r5.append(" ".join(f"{D}{plain(n)}{R}{CYN}{c}{R}" for n, c in top))
    ec_ = RED if t["errors"] else D
    r5.append(f"{ec_}{t['errors']}{R}{D} tool errors{R}")
    if t["synth"]:
        r5.append(f"{RED}{t['synth']}{R}{D} api errors{R}")
    r5.append(
        f"{GRN}{len(t['f_edit'])}{R}{D} files edited{R} {D}·{R} " f"{len(t['f_read'])}{D} read{R}"
    )
    if t["side"]:
        r5.append(f"{MAG}{t['side']}{R}{D} subagent msgs{R}")
    else:
        r5.append(f"{D}0 subagents{R}")
    cc = RED if t["compact"] else D
    r5.append(f"{cc}{t['compact']}{R}{D} compactions{R}")
    if t["cmds"]:
        r5.append(
            f"{D}cmds{R} "
            + " ".join(
                f"{D}{plain(k)}{R}{CYN}{v}{R}"
                for k, v in sorted(t["cmds"].items(), key=lambda kv: -kv[1])[:3]
            )
        )
    rows["TOOLS"] = row("TOOLS", r5)

    # ---------- row 6: timing ----------
    wall = money.get("wall_seconds", 0.0)
    api = money.get("api_seconds", 0.0)
    r6 = []
    if t["durs"]:
        s = sorted(finite_integer(value) for value in t["durs"])
        med = s[len(s) // 2] / 1000
        last = finite_integer(t["durs"][-1]) / 1000
        mx = max(s) / 1000
        r6.append(
            f"{D}turn{R} {dur(last)}{D} last · {dur(med)} median · {dur(mx)} max"
            f" ({len(t['durs'])} timed){R}"
        )
    r6.append(
        f"{D}wall{R} {dur(wall)} {D}· api{R} {dur(api)}"
        + (f" {D}({api/wall*100:.0f}% busy){R}" if wall else "")
    )
    if t["hook_runs"]:
        hs = sorted(t["hook_ms"]) or [0]
        he = RED if t["hook_errs"] else D
        r6.append(
            f"{D}hooks{R} {t['hook_runs']}{D} runs · {hs[len(hs)//2]}ms median · {R}"
            f"{he}{t['hook_errs']}{R}{D} errors{R}"
        )
    rows["TIMING"] = row("TIMING", r6)

    # ---------- row 7: machine pressure ----------
    # Process results mix machine-wide totals with this session's PID and RSS.
    # Keep host-supplied identifiers opaque and namespace the parent fallback so
    # the two forms cannot collide inside the shared cache.
    process_session = identity.get("session_id")
    process_scope = (
        f"session:{process_session}"
        if isinstance(process_session, str)
        else f"parent:{os.getppid()}"
    )
    procs = pr.probe(f"procs:{process_scope}", 8, pr.processes) or {}
    mem = pr.probe("mem", 8, pr.memory) or {}
    dsk = pr.probe(f"disk:{cwd}", 30, lambda c=cwd: pr.disk(c)) or {}
    # Ordered so the two figures people compare -- this session's footprint and
    # every claude process -- sit side by side, with machine-wide pressure after
    # them and disk last, since disk is the first thing worth losing when narrow.
    r7 = []
    if procs.get("mine_rss"):
        r7.append(
            f"{D}this session{R} {CYN}{gb(procs['mine_rss'])}{R}"
            f"{D} · {procs.get('mine_procs',1)} proc · pid {procs.get('mine_pid')}{R}"
        )
    if procs.get("all_rss") is not None:
        c7 = (
            f"{D}all claude{R} {CYN}{gb(procs['all_rss'])}{R}"
            f"{D} · {procs.get('all_n',0)} proc{R}"
        )
        if mem.get("total"):
            c7 += f"{D} · {procs['all_rss']/mem['total']*100:.1f}% of ram{R}"
        r7.append(c7)
    if mem.get("pct") is not None:
        m7 = (
            f"{D}ram{R}{bar(mem['pct'],8,70,88)} {grade(mem['pct'],70,88)}"
            f"{mem['pct']:.0f}%{R}{D} of {gb(mem.get('total'))}{R}"
        )
        if mem.get("compressed"):
            m7 += f"{D} · {gb(mem['compressed'])} compressed{R}"
        r7.append(m7)
    if dsk.get("pct") is not None:
        r7.append(
            f"{D}disk{R}{bar(dsk['pct'],8,80,92)} {grade(dsk['pct'],80,92)}"
            f"{dsk['pct']:.0f}%{R}{D} · {gb(dsk.get('free'))} free{R}"
        )
    if r7:
        rows["SYSTEM"] = row("SYSTEM", r7)

    # ---------- row 8: money ----------
    usd = money.get("run_cost_usd")
    session_id = identity.get("session_id", "?")
    agg = ledger_update(
        session_id,
        usd,
        proj,
        identity.get("session_title"),
        conversation_root(transcript_path),
        pid=procs.get("mine_pid"),
        accrued_at=t.get("last_ts"),
        duration=wall if 0 < wall <= time.time() else None,
    )
    p8 = []
    if usd is not None:
        life = agg["session"]
        # After a resume the payload reports only this run; the ledger carries the
        # lifetime. Show both when they differ so the run's own spend stays visible.
        if agg["base"] > 1e-9:
            p8.append(
                f"{CYN}${life:.2f}{R}{D} session{R} "
                f"{D}(run {R}{CYN}${usd:.2f}{R}{D} · {agg['runs']} runs){R}"
            )
        else:
            p8.append(f"{CYN}${life:.2f}{R}{D} session{R}")

    def rolling_amount(label, key):
        marker = "" if agg[key + "_complete"] else f"{D}≥{R}"
        return f"{D}{label}{R} {marker}${agg[key]:.2f}"

    p8.append(
        f"{rolling_amount('24h', 'd1')} {D}·{R} "
        f"{rolling_amount('7d', 'd7')} {D}·{R} {rolling_amount('30d', 'd30')}"
    )
    p8.append(
        f"{D}last5{R} ${agg['last5']:.2f} {D}·{R} {D}all{R} ${agg['all']:.2f} "
        f"{D}({agg['convos']} convo{'s' if agg['convos']!=1 else ''} · {agg['n']} sess"
        + (f" · {agg['forks']} fork{'s' if agg['forks']!=1 else ''}" if agg["forks"] else "")
        + f"){R}"
    )
    la = money.get("lines_added", 0)
    lr = money.get("lines_removed", 0)
    p8.append(f"{GRN}+{la}{R}{D}/{R}{RED}-{lr}{R}{D} lines{R}")

    # Credits. The balance is NOT obtainable locally (see statusline_probes.account),
    # and a spend-since-crossing figure was deliberately removed: it could not be
    # accounted exactly -- it began counting when the status line first noticed, not
    # when overage actually started -- and this line does not invent dollar figures.
    # Only exact facts remain: whether credits are on, and whether this model draws.
    acct = pr.probe("account", 30, pr.account) or {}
    if acct:
        inc = [str(x).lower() for x in (acct.get("included_models") or [])]
        if acct.get("disabled_reason"):
            p8.append(f"{RED}{B}credits OFF{R}{D} ({plain(acct['disabled_reason'])}){R}")
        elif not acct.get("enabled"):
            p8.append(f"{YEL}credits off{R}")
        elif over_active and str(model).lower() not in inc:
            p8.append(f"{RED}{B}on credits{R}{D} · balance only via /usage-credits{R}")
        elif over_active:
            p8.append(f"{GRN}overage included{R}{D} for {plain(model)}{R}")
        else:
            p8.append(f"{D}credits on{R}")
    rows["COST"] = row("COST", p8)

    print("\n".join(rows[k] for k in ORDER if rows.get(k)))


def main():
    try:
        _render()
    except BrokenPipeError:
        # A host closing its status-line pipe is routine lifecycle behavior, not
        # renderer-health evidence.
        raise
    except Exception as error:
        try:
            from agent_statusline.diagnostics import record_render_failure

            record_render_failure(error)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
