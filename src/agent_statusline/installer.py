#!/usr/bin/env python3
"""Wire the status line into Claude Code's settings.

Two supported shapes, detected rather than configured:

**Installed** (`uv tool install`, `pipx install`, `pip install`) -- settings
point at the `agent-statusline` console script by absolute path, and nothing is
symlinked. This is the normal path for someone who just wants the status line.

**Checkout** -- for hacking on it. A single symlink,
`~/.claude/statusline -> <repo>/src/agent_statusline`, lets settings refer to
`~/.claude/statusline/...` so the working tree stays the source of truth and
edits take effect with no reinstall.

Either way `settings.json` is backed up first and unrelated settings are
preserved. Stdlib only: this runs before anything is installed.
"""
import json
import os
import shutil
import subprocess
import sys
import time

PKG = os.path.dirname(os.path.realpath(__file__))
MIN_PYTHON = (3, 9)

HOOKS = (
    ("SessionEnd", "session-end", "session_end", 10),
    ("UserPromptSubmit", "context-guard", "context_guard", 10),
)
STOPGAP_HOOKS = (
    ("UserPromptSubmit", "timestamp-user", "timestamp_user", 5),
    ("Stop", "timestamp-stop", "timestamp_stop", 5),
)


def say(msg):
    print(f"  {msg}")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def claude_dir():
    return os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")


def checkout_root():
    """The repository root if this package is a working tree, else None.

    An installed package sits in site-packages with no pyproject beside it, so
    the presence of one two levels up is what distinguishes the two shapes.
    """
    root = os.path.dirname(os.path.dirname(PKG))
    return root if os.path.exists(os.path.join(root, "pyproject.toml")) else None


def console_script():
    """Absolute path to the installed `agent-statusline` entry point.

    Resolved to an absolute path rather than relying on PATH: the status line
    and the hooks are spawned by Claude Code, whose environment is not
    guaranteed to include the tool directory.
    """
    for cand in (os.path.join(os.path.dirname(sys.executable), "agent-statusline"),
                 shutil.which("agent-statusline")):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def native_timestamps():
    """True once Claude Code's own message timestamps are ungated (ADR 0015)."""
    try:
        with open(os.path.expanduser("~/.claude.json")) as fh:
            flags = json.load(fh).get("cachedGrowthBookFeatures") or {}
        return bool(flags.get("tengu_silk_hinge"))
    except Exception:
        return False


def commands():
    """(status-line command, hook-command builder) for whichever shape this is."""
    root = checkout_root()
    if root is None:
        exe = console_script()
        if exe is None:
            die("installed package but no `agent-statusline` executable found.\n"
                "       Reinstall with `uv tool install` / `pipx install`, or run "
                "install from a checkout.")
        return f'"{exe}"', (lambda slug, _mod: f'"{exe}" hook {slug}'), None
    link = os.path.join(claude_dir(), "statusline")
    return ("python3 ~/.claude/statusline/statusline.py",
            (lambda _slug, mod: f"python3 ~/.claude/statusline/hooks/{mod}.py"),
            link)


def link_checkout(link, dry):
    if os.path.islink(link):
        say(f"symlink:  replacing existing -> {os.readlink(link)}")
        if not dry:
            os.unlink(link)
    elif os.path.exists(link):
        die(f"{link} exists and is not a symlink. Move it aside and re-run.")
    if not dry:
        os.makedirs(os.path.dirname(link), exist_ok=True)
        os.symlink(PKG, link)
    say(f"symlink:  {link} -> {PKG}")


def write_settings(cdir, dry, remove=False):
    path = os.path.join(cdir, "settings.json")
    try:
        with open(path) as fh:
            cfg = json.load(fh)
    except Exception:
        cfg = {}
    if not dry and os.path.exists(path):
        backup = f"{path}.bak.{time.strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(path, backup)
        say(f"backup:   {backup}")

    hooks = cfg.setdefault("hooks", {})
    if remove:
        cfg.pop("statusLine", None)
        for event in ("SessionEnd", "UserPromptSubmit", "Stop"):
            hooks.pop(event, None)
        say("settings: statusLine and hook entries removed")
    else:
        status_cmd, hook_cmd, _ = commands()
        cfg["statusLine"] = {"type": "command", "command": status_cmd, "padding": 0}
        for event in ("SessionEnd", "UserPromptSubmit", "Stop"):
            hooks.pop(event, None)
        wanted = list(HOOKS)
        if native_timestamps():
            say("hooks:    native timestamps live; stopgap hooks not installed")
        else:
            say("hooks:    native timestamps still gated; stopgap hooks installed")
            wanted += list(STOPGAP_HOOKS)
        for event, slug, mod, timeout in wanted:
            hooks.setdefault(event, []).append(
                {"hooks": [{"type": "command",
                            "command": hook_cmd(slug, mod),
                            "timeout": timeout}]})
        cfg.setdefault("showMessageTimestamps", True)
        say(f"settings: statusLine + {len(hooks)} hook events")

    if not hooks:
        cfg.pop("hooks", None)
    if dry:
        return
    tmp = f"{path}.tmp"
    with open(tmp, "w") as fh:
        json.dump(cfg, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def verify(cdir):
    """Render the last real payload against a throwaway state dir (ADR 0014)."""
    sample = os.path.join(cdir, "statusline-last-payload.json")
    scratch = os.path.join(cdir, ".verify-state")
    payload = b"{}"
    if os.path.exists(sample):
        with open(sample, "rb") as fh:
            payload = fh.read()
    proc = subprocess.run([sys.executable, os.path.join(PKG, "statusline.py")],
                          input=payload, capture_output=True,
                          env=dict(os.environ, AGENT_STATUSLINE_STATE=scratch))
    shutil.rmtree(scratch, ignore_errors=True)
    if proc.returncode != 0:
        die("render failed:\n" + proc.stderr.decode("utf-8", "replace"))
    if os.path.exists(sample):
        print("verify (rendered from your last real payload):")
        for line in proc.stdout.decode("utf-8", "replace").rstrip("\n").split("\n"):
            print("    " + line)
    else:
        say("verify:   runs clean (full output appears once Claude Code starts)")


def run(dry_run=False, uninstall=False):
    cdir = claude_dir()
    root = checkout_root()
    print("agent-statusline installer")
    say(f"mode:     {'checkout at ' + root if root else 'installed package'}")
    say(f"target:   {cdir}")
    if dry_run:
        say("MODE:     dry run, nothing will be written")

    if uninstall:
        link = os.path.join(cdir, "statusline")
        if os.path.islink(link):
            if not dry_run:
                os.unlink(link)
            say(f"symlink:  removed {link}")
        write_settings(cdir, dry_run, remove=True)
        print("\nDone. Your ledger and history are untouched.")
        return 0

    if sys.version_info < MIN_PYTHON:
        die(f"python {'.'.join(map(str, MIN_PYTHON))}+ required, "
            f"this is {sys.version.split()[0]}")
    say(f"python:   {sys.version.split()[0]} (stdlib only, no dependencies)")
    if not dry_run:
        os.makedirs(cdir, exist_ok=True)
    _, _, link = commands()
    if link:
        link_checkout(link, dry_run)
    else:
        say(f"command:  {console_script()}")
    write_settings(cdir, dry_run)
    verify(cdir)
    print("\nDone. Restart Claude Code to pick it up.")
    return 0
