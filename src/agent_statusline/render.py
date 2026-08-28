"""Colours, units, bars, and the width-fitting row packer.

Nothing here knows what a Claude payload looks like -- this is the presentation
layer any host can reuse (see docs/PORTING.md).
"""

import re
import shutil
import unicodedata

R = "\033[0m"
D = "\033[2m"
B = "\033[1m"
RED = "\033[31m"
GRN = "\033[32m"
YEL = "\033[33m"
BLU = "\033[34m"
MAG = "\033[35m"
CYN = "\033[36m"
GRY = "\033[90m"

#: Width of the dim label column that prefixes every row.
LABEL = 8
#: Rows wrap onto at most this many lines before segments start being dropped.
MAXLINES = 2
#: Used when the terminal width cannot be determined at all.
FALLBACK_WIDTH = 120

ANSI = re.compile(r"\033\[[0-9;]*m")
ESCAPE = re.compile(r"\033(?:\[[0-?]*[ -/]*[@-~]|[^\033]?)")


def sanitize(s):
    """Remove terminal controls while preserving our intentional SGR styles."""
    s = str(s)
    out = []
    i = 0
    while i < len(s):
        sgr = ANSI.match(s, i)
        if sgr:
            out.append(sgr.group())
            i = sgr.end()
            continue
        if s[i] == "\033":
            control = ESCAPE.match(s, i)
            i = control.end() if control else i + 1
            continue
        if unicodedata.category(s[i]).startswith("C"):
            i += 1
            continue
        out.append(s[i])
        i += 1
    return "".join(out)


def _cell_width(char):
    if unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def vis(s):
    """Printable width, ignoring colour escapes.

    Colour codes occupy no columns, so they must not count toward the width
    budget -- measuring len(s) directly makes every coloured row look roughly
    twice as wide as it is and truncates almost everything.
    """
    return sum(_cell_width(char) for char in ANSI.sub("", sanitize(s)))


def width():
    """Current terminal width.

    Claude Code exports COLUMNS into the status-line subprocess, which is what
    shutil consults first. Nothing else works from in there: stdin, stdout,
    stderr and /dev/tty all raise OSError. See docs/INTERNALS.md.

    Deliberately read on every call rather than cached at import: the status
    line is a fresh process per redraw and the user resizes windows live, so a
    module-level constant would freeze the layout at the first width seen.
    """
    return shutil.get_terminal_size((FALLBACK_WIDTH, 24)).columns


def clip(s, budget):
    """Hard-truncate one segment to `budget` printable columns.

    Packing alone cannot save a row whose *single* segment is wider than the
    terminal -- at least one segment is always kept, so an 80-column segment in
    a 60-column window would overflow. Escapes are copied through rather than
    counted, and a reset is appended so a cut inside a coloured run cannot leak
    its colour into the rest of the line.
    """
    s = sanitize(s)
    if budget <= 0:
        return ""
    if vis(s) <= budget:
        return s
    out, seen, i = [], 0, 0
    keep = max(0, budget - 1)  # leave a column for the ellipsis
    while i < len(s):
        m = ANSI.match(s, i)
        if m:
            out.append(m.group())
            i = m.end()
            continue
        cells = _cell_width(s[i])
        if seen + cells > keep:
            break
        out.append(s[i])
        seen += cells
        i += 1
    return "".join(out) + f"{R}{D}…{R}"


def pack(segs, sep, budget, maxlines=MAXLINES):
    """Greedily pack segments into at most `maxlines` lines.

    Returns (lines, dropped). Segments arrive ordered most- to least-important,
    so overflow is taken off the end: a narrow terminal loses the last segment
    of a row rather than the row itself.
    """
    lines: list[list[str]] = []
    cur: list[str] = []
    for seg in segs:
        if not cur:
            cur = [seg]
            continue
        if vis(sep.join([*cur, seg])) <= budget:
            cur.append(seg)
            continue
        if len(lines) + 1 < maxlines:  # room for another line
            lines.append(cur)
            cur = [seg]
        else:  # out of lines: drop the rest
            lines.append(cur)
            return lines, True
    lines.append(cur)
    return lines, False


def row(label, segs, sep=None, maxlines=MAXLINES):
    """Render one labelled row, wrapping to `maxlines` before truncating.

    A row that fits on one line stays on one line -- wrapping only happens when
    the content genuinely does not fit the current terminal. Continuation lines
    are indented under the label so the row still reads as one block.
    """
    sep = sanitize(f" {D}│{R} " if sep is None else sep)
    label = sanitize(label)
    segs = [sanitize(s) for s in segs if s]
    if not segs:
        return ""
    budget = width() - LABEL - 2
    segs = [clip(s, budget) for s in segs]
    lines, dropped = pack(segs, sep, budget, maxlines)
    # Keep an SGR prefix on continuation lines. Claude Code trims raw leading
    # whitespace from multiline status-line output, but it preserves spaces
    # that follow an escape sequence. This keeps wrapped content aligned with
    # the first segment instead of snapping back under the row label.
    out = [
        (f"{D}{label:<{LABEL}}{R}" if i == 0 else f"{D}{'':<{LABEL}}{R}") + sep.join(ln)
        for i, ln in enumerate(lines)
    ]
    if dropped:
        marker = f" {D}…{R}"
        available = max(0, width() - vis(marker))
        if vis(out[-1]) > available:
            out[-1] = clip(out[-1], available)
        out[-1] += marker
    return "\n".join(out)


def tok(n):
    """3 significant figures, trailing zeros stripped: 515k, 1M, 71.9M, 1.42M."""
    n = int(n or 0)
    for div, suf in ((1_000_000, "M"), (1_000, "k")):
        if n >= div:
            v = n / div
            s = f"{v:.3g}"
            if "e" in s or float(s) >= 1000:
                s = f"{v:.0f}"
            return s + suf
    return str(n)


def gb(n):
    n = float(n or 0)
    return f"{n / 2 ** 30:.1f}G" if n >= 2**30 else f"{n / 2 ** 20:.0f}M"


def dur(sec):
    sec = int(max(0, sec))
    d, h, m = sec // 86400, (sec % 86400) // 3600, (sec % 3600) // 60
    if d:
        return f"{d}d{h}h"
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m"
    return f"{sec}s"


def grade(p, warn=50, crit=80):
    return RED if p >= crit else YEL if p >= warn else GRN


def bar(pct, width_=10, warn=50, crit=80):
    pct = max(0.0, min(100.0, float(pct)))
    f = round(pct / 100 * width_)
    return f"{D}[{R}{grade(pct, warn, crit)}{'█' * f}{GRY}{'░' * (width_ - f)}{R}{D}]{R}"
