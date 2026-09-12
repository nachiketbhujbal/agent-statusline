"""Colours, units, bars, and the width-fitting row packer.

Nothing here knows what a Claude payload looks like -- this is the presentation
layer any host can reuse (see docs/PORTING.md).
"""

import os
import re
import sys
import unicodedata

from agent_statusline.coerce import finite_integer, finite_number

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
CONTROL_STRING = re.compile(r"\033(?:\]|P|X|\^|_)(?:[^\033\x07]|\033(?!\\))*(?:\x07|\033\\|$)")
CSI = re.compile(r"\033\[[0-?]*[ -/]*[@-~]")
INCOMPLETE_CSI = re.compile(r"\033\[[0-?]*[ -/]*\Z")
ESCAPE = re.compile(r"\033(?:[ -/]*[@-~]|.)")
SAFE_SGR = frozenset((R, D, B, RED, GRN, YEL, BLU, MAG, CYN, GRY))


def sanitize(s, preserve_sgr=True):
    """Remove terminal controls, optionally preserving package-owned SGR styles."""
    text = str(s)
    out = []
    index = 0
    while index < len(text):
        sgr = ANSI.match(text, index)
        if sgr:
            if preserve_sgr and sgr.group() in SAFE_SGR:
                out.append(sgr.group())
            index = sgr.end()
            continue
        if text[index] == "\033":
            control = (
                CONTROL_STRING.match(text, index)
                or CSI.match(text, index)
                or INCOMPLETE_CSI.match(text, index)
                or ESCAPE.match(text, index)
            )
            index = control.end() if control else index + 1
            continue
        if unicodedata.category(text[index]) in {"Cc", "Cf", "Cs"}:
            index += 1
            continue
        out.append(text[index])
        index += 1
    return "".join(out)


def plain(s):
    """Return untrusted display text with every terminal control removed."""
    return sanitize(s, preserve_sgr=False)


def _cell_width(char):
    if unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1


def _take_cells(text, budget):
    """Return a sanitized whole-code-point prefix within a cell budget."""
    out = []
    seen = 0
    index = 0
    while index < len(text):
        sgr = ANSI.match(text, index)
        if sgr:
            out.append(sgr.group())
            index = sgr.end()
            continue
        cells = _cell_width(text[index])
        if seen + cells > budget:
            break
        out.append(text[index])
        seen += cells
        index += 1
    return "".join(out)


def vis(s):
    """Printable width, ignoring colour escapes.

    Colour codes occupy no columns, so they must not count toward the width
    budget -- measuring len(s) directly makes every coloured row look roughly
    twice as wide as it is and truncates almost everything.
    """
    return sum(_cell_width(char) for char in ANSI.sub("", sanitize(s)))


def width():
    """Current terminal width.

    Claude Code exports COLUMNS into the status-line subprocess. Nothing else
    works from in there: stdin, stdout, stderr and /dev/tty all raise OSError.
    See docs/INTERNALS.md.

    Deliberately read on every call rather than cached at import: the status
    line is a fresh process per redraw and the user resizes windows live, so a
    module-level constant would freeze the layout at the first width seen.
    """
    try:
        columns = int(os.environ.get("COLUMNS", ""))
    except ValueError:
        columns = 0
    if columns <= 0:
        try:
            output = sys.__stdout__
            columns = os.get_terminal_size(output.fileno()).columns if output else 0
        except (AttributeError, OSError, ValueError):
            columns = 0
    return columns if columns > 0 else FALLBACK_WIDTH


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
    keep = max(0, budget - 1)  # leave one cell for the ellipsis
    return _take_cells(s, keep) + f"{R}{D}…{R}"


def pack(segs, sep, budget, maxlines=MAXLINES):
    """Greedily pack segments into at most `maxlines` lines.

    Returns (lines, dropped). Segments arrive ordered most- to least-important,
    so overflow is taken off the end: a narrow terminal loses the last segment
    of a row rather than the row itself.
    """
    lines: list = []
    cur: list = []
    for seg in segs:
        if not cur:
            cur = [seg]
            continue
        if vis(sep.join(cur + [seg])) <= budget:
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
    total_width = max(0, width())
    if total_width == 0:
        return ""
    sep = sanitize(f" {D}│{R} ") if sep is None else plain(sep)
    label = plain(label)
    segs = [sanitize(s) for s in segs if s]
    if not segs:
        return ""
    budget = max(0, total_width - LABEL - 2)
    segs = [clip(s, budget) for s in segs]
    lines, dropped = pack(segs, sep, budget, maxlines)
    label_text = _take_cells(label, LABEL)
    label_text += " " * max(0, LABEL - vis(label_text))
    # Keep an SGR prefix on continuation lines. Claude Code was observed to
    # trim raw leading whitespace from multiline status-line output while
    # preserving spaces after an escape sequence. Re-verify if the host changes.
    out = [
        (f"{D}{label_text}{R}" if i == 0 else f"{D}{'':<{LABEL}}{R}") + sep.join(ln)
        for i, ln in enumerate(lines)
    ]
    if dropped:
        marker = f" {D}…{R}"
        available = max(0, total_width - vis(marker))
        out[-1] = _take_cells(out[-1], available) + marker
    out = [clip(line, total_width) if vis(line) > total_width else line for line in out]
    return "\n".join(out)


def tok(n):
    """3 significant figures, trailing zeros stripped: 515k, 1M, 71.9M, 1.42M."""
    n = finite_integer(n)
    for div, suf in ((1_000_000, "M"), (1_000, "k")):
        if n >= div:
            v = n / div
            s = f"{v:.3g}"
            if "e" in s or float(s) >= 1000:
                s = f"{v:.0f}"
            return s + suf
    return str(n)


def gb(n):
    n = finite_number(n)
    return f"{n / 2 ** 30:.1f}G" if n >= 2**30 else f"{n / 2 ** 20:.0f}M"


def dur(sec):
    sec = max(0, finite_integer(sec))
    d, h, m = sec // 86400, (sec % 86400) // 3600, (sec % 3600) // 60
    if d:
        return f"{d}d{h}h"
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m"
    return f"{sec}s"


def grade(p, warn=50, crit=80):
    p = finite_number(p)
    return RED if p >= crit else YEL if p >= warn else GRN


def bar(pct, width_=10, warn=50, crit=80):
    pct = max(0.0, min(100.0, finite_number(pct)))
    f = int(round(pct / 100 * width_))
    return f"{D}[{R}{grade(pct, warn, crit)}{'█' * f}{GRY}{'░' * (width_ - f)}{R}{D}]{R}"
