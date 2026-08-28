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
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
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


def commands(cdir=None):
    """(status-line command, hook-command builder) for whichever shape this is."""
    root = checkout_root()
    if root is None:
        exe = console_script()
        if exe is None:
            die("installed package but no `agent-statusline` executable found.\n"
                "       Reinstall with `uv tool install` / `pipx install`, or run "
                "install from a checkout.")
        quoted = shlex.quote(exe)
        return quoted, (lambda slug, _mod: f"{quoted} hook {slug}"), None
    link = os.path.join(cdir or claude_dir(), "statusline")
    python = shlex.quote(sys.executable)
    return (
        f"{python} {shlex.quote(os.path.join(link, 'statusline.py'))}",
        (
            lambda _slug, mod: (
                f"{python} {shlex.quote(os.path.join(link, 'hooks', mod + '.py'))}"
            )
        ),
        link,
    )


def _tokens(command):
    if not isinstance(command, str):
        return []
    try:
        return shlex.split(command)
    except ValueError:
        return []


def managed_hook_command(command):
    """Whether a hook command belongs to this package."""
    tokens = _tokens(command)
    if len(tokens) == 3 and os.path.basename(tokens[0]) == "agent-statusline":
        slugs = {slug for _, slug, _, _ in HOOKS + STOPGAP_HOOKS}
        return tokens[1] == "hook" and tokens[2] in slugs
    if len(tokens) != 2 or not os.path.basename(tokens[0]).startswith("python"):
        return False
    normalized = tokens[1].replace(os.sep, "/")
    modules = {mod for _, _, mod, _ in HOOKS + STOPGAP_HOOKS}
    return any(normalized.endswith(f"/statusline/hooks/{mod}.py") for mod in modules)


def managed_status_command(command):
    """Whether a status-line command belongs to this package."""
    tokens = _tokens(command)
    if len(tokens) == 1 and os.path.basename(tokens[0]) == "agent-statusline":
        return True
    if len(tokens) != 2 or not os.path.basename(tokens[0]).startswith("python"):
        return False
    return tokens[1].replace(os.sep, "/").endswith("/statusline/statusline.py")


def _remove_managed_hooks(cfg):
    hooks = cfg.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    removed = 0
    for event in {event for event, _, _, _ in HOOKS + STOPGAP_HOOKS}:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            kept = []
            for hook in group["hooks"]:
                command = hook.get("command") if isinstance(hook, dict) else None
                if managed_hook_command(command):
                    removed += 1
                else:
                    kept.append(hook)
            if kept:
                kept_groups.append({**group, "hooks": kept})
        if kept_groups:
            hooks[event] = kept_groups
        else:
            hooks.pop(event, None)
    if not hooks:
        cfg.pop("hooks", None)
    return removed


def _load_settings(path):
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        die(f"cannot safely read existing settings {path}: {exc}")
    if not isinstance(cfg, dict):
        die(f"cannot safely update {path}: top-level JSON value is not an object")
    return cfg


def _write_json_atomic(path, cfg):
    """Publish settings atomically, through a symlink rather than over it.

    A settings path is legitimately a symlink when someone keeps their Claude
    configuration in a dotfiles checkout. Replacing the link with a regular file
    would silently orphan the real file -- Claude Code would read the new one
    while the user kept editing the old -- so resolve it and publish to the
    target. The mode comes from the resolved file for the same reason: a
    symlink's own bits are 0o777 on most systems, and copying those onto real
    settings would widen them to world-readable.
    """
    target = os.path.realpath(path)
    directory = os.path.dirname(target)
    mode = 0o600
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode)
    except FileNotFoundError:
        pass
    fd, tmp = tempfile.mkstemp(prefix=".settings.json.", dir=directory, text=True)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        try:
            dfd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


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
    cfg = _load_settings(path)
    if not dry and os.path.exists(path):
        backup = f"{path}.bak.{time.strftime('%Y%m%d%H%M%S')}.{time.time_ns()}"
        shutil.copy2(path, backup)
        say(f"backup:   {backup}")

    removed = _remove_managed_hooks(cfg)
    if remove:
        status = cfg.get("statusLine")
        command = status.get("command") if isinstance(status, dict) else None
        if managed_status_command(command):
            cfg.pop("statusLine", None)
            status_msg = "managed statusLine removed"
        else:
            status_msg = "non-managed statusLine preserved"
        say(f"settings: {status_msg}; {removed} managed hook(s) removed")
    else:
        status_cmd, hook_cmd, _ = commands(cdir)
        cfg["statusLine"] = {"type": "command", "command": status_cmd, "padding": 0}
        wanted = list(HOOKS)
        if native_timestamps():
            say("hooks:    native timestamps live; stopgap hooks not installed")
        else:
            say("hooks:    native timestamps still gated; stopgap hooks installed")
            wanted += list(STOPGAP_HOOKS)
        hooks = cfg.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            die(f"cannot safely update {path}: hooks is not an object")
        for event, slug, mod, timeout in wanted:
            hooks.setdefault(event, []).append(
                {"hooks": [{"type": "command",
                            "command": hook_cmd(slug, mod),
                            "timeout": timeout}]})
        cfg.setdefault("showMessageTimestamps", True)
        say(f"settings: statusLine + {len(wanted)} managed hooks")

    if dry:
        return
    _write_json_atomic(path, cfg)


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
        if os.path.islink(link) and os.path.realpath(link) == PKG:
            if not dry_run:
                os.unlink(link)
            say(f"symlink:  removed {link}")
        elif os.path.lexists(link):
            say(f"symlink:  preserved non-managed path {link}")
        write_settings(cdir, dry_run, remove=True)
        print("\nDone. Your ledger and history are untouched.")
        return 0

    if sys.version_info < MIN_PYTHON:
        die(f"python {'.'.join(map(str, MIN_PYTHON))}+ required, "
            f"this is {sys.version.split()[0]}")
    say(f"python:   {sys.version.split()[0]} (stdlib only, no dependencies)")
    if not dry_run:
        os.makedirs(cdir, exist_ok=True)
    # Refuse before touching anything. write_settings would catch this too, but
    # by then the checkout symlink already exists, which leaves a half-installed
    # tree behind a failure that is supposed to change nothing.
    _load_settings(os.path.join(cdir, "settings.json"))
    _, _, link = commands(cdir)
    if link:
        link_checkout(link, dry_run)
    else:
        say(f"command:  {console_script()}")
    write_settings(cdir, dry_run)
    verify(cdir)
    print("\nDone. Restart Claude Code to pick it up.")
    return 0
