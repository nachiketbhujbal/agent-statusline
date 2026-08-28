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

What this owns, and nothing else: the `statusLine` entry, the hook entries whose
command is exactly one this installer wrote, and the checkout symlink. One
deliberate exception: `showMessageTimestamps` is added when absent (ADR 0015)
and is *not* reclaimed on uninstall, because a value already present cannot be
distinguished from one we set. That exception is stated rather than folded into
the ownership claim.
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
MANAGED_EVENTS = tuple(dict.fromkeys(event for event, _, _, _ in HOOKS + STOPGAP_HOOKS))


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


# --------------------------------------------------------------------------
# Ownership
#
# Every predicate below answers one question: did *this* installation write
# that exact command? Anything short of an exact path -- a bare basename, a
# trailing fragment -- claims commands belonging to other tools, and claiming
# one means deleting it on uninstall.
# --------------------------------------------------------------------------

def _tokens(command):
    if not isinstance(command, str):
        return []
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _same_path(candidate, expected):
    return os.path.normpath(candidate) == os.path.normpath(expected)


def _checkout_path_matches(candidate, expected):
    """Whether a checkout-shape script argument is the one written into `cdir`.

    The released v0.2.0 installer wrote a *literal* `~/.claude/statusline/...`
    argument and left the tilde for the shell to expand. Expanding a leading
    `~` here recognizes that shape while keeping the comparison anchored to the
    configuration directory: a legacy entry is claimed only when `~` resolves to
    the very path this installation manages, so a third-party
    `/opt/other/statusline/statusline.py` still does not match.
    """
    return (_same_path(candidate, expected)
            or _same_path(os.path.expanduser(candidate), expected))


def _managed_exe(command_tokens):
    """Whether an installed-shape command names this installation's executable."""
    exe = console_script()
    return exe is not None and _same_path(command_tokens[0], exe)


def managed_hook_command(command, cdir=None):
    """Whether a hook command belongs to this package."""
    tokens = _tokens(command)
    slugs = {slug for _, slug, _, _ in HOOKS + STOPGAP_HOOKS}
    if len(tokens) == 3:
        return tokens[1] == "hook" and tokens[2] in slugs and _managed_exe(tokens)
    if len(tokens) != 2 or not os.path.basename(tokens[0]).startswith("python"):
        return False
    root = os.path.join(cdir or claude_dir(), "statusline", "hooks")
    modules = {mod for _, _, mod, _ in HOOKS + STOPGAP_HOOKS}
    return any(_checkout_path_matches(tokens[1], os.path.join(root, f"{mod}.py"))
               for mod in modules)


def managed_status_command(command, cdir=None):
    """Whether a status-line command belongs to this package."""
    tokens = _tokens(command)
    if len(tokens) == 1:
        return _managed_exe(tokens)
    if len(tokens) != 2 or not os.path.basename(tokens[0]).startswith("python"):
        return False
    expected = os.path.join(cdir or claude_dir(), "statusline", "statusline.py")
    return _checkout_path_matches(tokens[1], expected)


def _status_command(cfg):
    status = cfg.get("statusLine")
    return status.get("command") if isinstance(status, dict) else None


def _count_managed_hooks(cfg, cdir):
    """How many managed hook commands are present, without mutating anything."""
    hooks = cfg.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    found = 0
    for event in MANAGED_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                continue
            for hook in group["hooks"]:
                command = hook.get("command") if isinstance(hook, dict) else None
                if managed_hook_command(command, cdir):
                    found += 1
    return found


def _remove_managed_hooks(cfg, cdir=None):
    """Drop managed hook commands, leaving every foreign entry's shape intact.

    A group we took nothing from is passed through unchanged -- including an
    empty one. Normalizing those away would rewrite a shape the release promises
    to preserve.
    """
    hooks = cfg.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    removed = 0
    for event in MANAGED_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups = []
        emptied = 0
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            kept = [hook for hook in group["hooks"]
                    if not managed_hook_command(
                        hook.get("command") if isinstance(hook, dict) else None, cdir)]
            taken = len(group["hooks"]) - len(kept)
            removed += taken
            if not taken:
                kept_groups.append(group)
            elif kept:
                kept_groups.append({**group, "hooks": kept})
            else:
                emptied += 1
        if kept_groups or not emptied:
            hooks[event] = kept_groups
        else:
            hooks.pop(event, None)
    if removed and not hooks:
        cfg.pop("hooks", None)
    return removed


# --------------------------------------------------------------------------
# Validation -- everything the chosen operation needs, checked before the
# first mutation. Refusing after a backup or a symlink already exists is not
# "nothing changed".
# --------------------------------------------------------------------------

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


def _validate_schema(cfg, path):
    """Every structural assumption the hook rewrite makes, checked up front."""
    hooks = cfg.get("hooks")
    if hooks is None:
        return
    if not isinstance(hooks, dict):
        die(f"cannot safely update {path}: hooks is not an object")
    for event in MANAGED_EVENTS:
        groups = hooks.get(event)
        if groups is not None and not isinstance(groups, list):
            die(f"cannot safely update {path}: hooks.{event} is not a list")


def _check_install_ownership(cfg, link, cdir, path):
    """Refuse to install over configuration this package does not own.

    The settings format holds exactly one `statusLine`, so installing over a
    foreign one destroys it with no way to put it back. Reinstalling our own
    entry, or over our own link, stays idempotent.
    """
    status = cfg.get("statusLine")
    if status is not None and not managed_status_command(_status_command(cfg), cdir):
        # Keyed on the entry, not on a command we managed to parse out of it. A
        # `statusLine` we cannot read is one we certainly cannot prove we own,
        # and overwriting it destroys it just as thoroughly as overwriting a
        # well-formed one.
        command = _status_command(cfg)
        shown = command if isinstance(command, str) else json.dumps(status)
        die(f"{path} already has a status line this package does not own:\n"
            f"       {shown}\n"
            "       Only one status line can be configured. Remove it first if "
            "you want to switch.")
    if link and os.path.islink(link) and os.path.realpath(link) != PKG:
        die(f"{link} is a symlink this package does not own:\n"
            f"       -> {os.readlink(link)}\n"
            "       Move it aside and re-run.")
    if link and not os.path.islink(link) and os.path.exists(link):
        die(f"{link} exists and is not a symlink. Move it aside and re-run.")


def _publish_target(path, cdir):
    """The real file settings will be written to, refusing to leave `cdir`."""
    target = os.path.realpath(path)
    root = os.path.realpath(cdir)
    if target != root and not target.startswith(root + os.sep):
        die(f"{path} resolves outside {cdir}:\n"
            f"       {target}\n"
            "       Refusing to write there. Point it inside the configuration "
            "directory, or move the file and remove the link.")
    return target


def _open_publish_dir(target, cdir):
    """A descriptor for the directory that will receive settings.

    `_publish_target` checks a *path*; this binds that decision to an object.
    Every later step -- create, chmod, replace -- happens relative to this
    descriptor and never names a directory again, so swapping a checked
    directory for a symlink afterwards cannot redirect publication. The walk
    refuses to traverse a link at all (`O_NOFOLLOW`), so a swap that lands
    inside the window fails closed instead of following the attacker's link.

    A second `realpath()` check would not close this: it would re-open the same
    race it is meant to detect.
    """
    if os.open not in os.supports_dir_fd:
        die("this platform cannot publish settings safely: openat is unavailable.")
    root = os.path.realpath(cdir)
    rel = os.path.relpath(os.path.dirname(target), root)
    parts = [] if rel == os.curdir else rel.split(os.sep)
    if any(part == os.pardir for part in parts):
        die(f"refusing to publish settings outside {cdir}")
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as exc:
        die(f"cannot open the configuration directory {root}: {exc}")
    bound = False
    try:
        for part in parts:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        bound = True
    except OSError as exc:
        die(f"cannot safely reach {target}: {exc}\n"
            "       A directory on the way changed while installing. Nothing "
            "was written.")
    finally:
        if not bound:
            os.close(fd)
    return fd


def _write_json_atomic(path, cfg, cdir):
    """Publish settings atomically, through a symlink rather than over it.

    A settings path is legitimately a symlink when someone links it within their
    Claude configuration directory. Replacing the link with a regular file would
    silently orphan the real file -- Claude Code would read the new one while the
    user kept editing the old -- so resolve it and publish to the target.

    The resolution is confined to `cdir`. Following a link anywhere the user
    happens to point it turns an installer into a write-anywhere primitive: a
    link into a dotfiles checkout, another user's home, or an unrelated
    configuration file would be silently rewritten with our keys.

    The mode comes from the resolved file, because a symlink's own bits (measured
    0o755 on macOS, commonly 0o777 elsewhere) would otherwise be copied onto real
    settings and widen them.
    """
    target = _publish_target(path, cdir)
    name = os.path.basename(target)
    dfd = _open_publish_dir(target, cdir)
    try:
        mode = 0o600
        try:
            mode = stat.S_IMODE(os.stat(name, dir_fd=dfd, follow_symlinks=False).st_mode)
        except FileNotFoundError:
            pass
        except OSError as exc:
            die(f"cannot read the permissions of {target}: {exc}")
        tmp = f".{name}.{os.getpid()}.{time.time_ns()}.tmp"
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=dfd)
        except OSError as exc:
            die(f"cannot create a temporary file beside {target}: {exc}")
        published = False
        try:
            os.fchmod(fd, mode)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
            published = True
        except NotImplementedError:
            die("this platform cannot publish settings safely: renameat is "
                "unavailable.")
        except OSError as exc:
            die(f"cannot write {target}: {exc}")
        finally:
            if not published:
                try:
                    os.unlink(tmp, dir_fd=dfd)
                except OSError:
                    pass
        try:
            os.fsync(dfd)
        except OSError:
            pass
    finally:
        os.close(dfd)


def link_checkout(link, dry):
    """Publish the checkout symlink. Ownership is settled before this runs."""
    if os.path.islink(link):
        if not dry:
            try:
                os.unlink(link)
            except OSError as exc:
                die(f"cannot replace {link}: {exc}")
        say(f"symlink:  refreshing {link}")
    if not dry:
        try:
            os.makedirs(os.path.dirname(link), exist_ok=True)
            os.symlink(PKG, link)
        except OSError as exc:
            die(f"cannot create {link}: {exc}")
    say(f"symlink:  {link} -> {PKG}")


def write_settings(cdir, dry, remove=False, cfg=None):
    path = os.path.join(cdir, "settings.json")
    if cfg is None:
        cfg = _load_settings(path)
        _publish_target(path, cdir)
        _validate_schema(cfg, path)

    if remove:
        command = _status_command(cfg)
        owned_status = managed_status_command(command, cdir)
        if not owned_status and not _count_managed_hooks(cfg, cdir):
            say("settings: nothing owned by this package; left untouched")
            return
    if not dry and os.path.exists(path):
        backup = f"{path}.bak.{time.strftime('%Y%m%d%H%M%S')}.{time.time_ns()}"
        try:
            shutil.copy2(path, backup)
        except OSError as exc:
            die(f"cannot back up {path}: {exc}")
        say(f"backup:   {backup}")

    removed = _remove_managed_hooks(cfg, cdir)
    if remove:
        if owned_status:
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
        for event, slug, mod, timeout in wanted:
            hooks.setdefault(event, []).append(
                {"hooks": [{"type": "command",
                            "command": hook_cmd(slug, mod),
                            "timeout": timeout}]})
        # Added when absent, never reclaimed on uninstall (ADR 0015/0020): a
        # value already there cannot be told apart from one we set.
        cfg.setdefault("showMessageTimestamps", True)
        say(f"settings: statusLine + {len(wanted)} managed hooks")

    if dry:
        return
    _write_json_atomic(path, cfg, cdir)


def verify(cdir):
    """Render the last real payload against a throwaway state dir (ADR 0014).

    The scratch state lives in the system temporary directory, uniquely created
    and removed again. An earlier fixed path under `cdir` meant a normal install
    recursively deleted whatever happened to sit there, and created `cdir` itself
    during a dry run that promised to write nothing.
    """
    sample = os.path.join(cdir, "statusline-last-payload.json")
    payload = b"{}"
    if os.path.exists(sample):
        with open(sample, "rb") as fh:
            payload = fh.read()
    scratch = tempfile.mkdtemp(prefix="agent-statusline-verify-")
    try:
        proc = subprocess.run([sys.executable, os.path.join(PKG, "statusline.py")],
                              input=payload, capture_output=True,
                              env=dict(os.environ, AGENT_STATUSLINE_STATE=scratch))
    finally:
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
    path = os.path.join(cdir, "settings.json")
    print("agent-statusline installer")
    say(f"mode:     {'checkout at ' + root if root else 'installed package'}")
    say(f"target:   {cdir}")
    if dry_run:
        say("MODE:     dry run, nothing will be written")

    if uninstall:
        # Full pre-flight before the first mutation. Removing the symlink and
        # then refusing on malformed settings leaves settings pointing at a link
        # that no longer exists, which is worse than not starting.
        cfg = _load_settings(path)
        _publish_target(path, cdir)
        _validate_schema(cfg, path)
        link = os.path.join(cdir, "statusline")
        if os.path.islink(link) and os.path.realpath(link) == PKG:
            if not dry_run:
                try:
                    os.unlink(link)
                except OSError as exc:
                    die(f"cannot remove {link}: {exc}")
            say(f"symlink:  removed {link}")
        elif os.path.lexists(link):
            say(f"symlink:  preserved non-managed path {link}")
        write_settings(cdir, dry_run, remove=True, cfg=cfg)
        print("\nDone. Your ledger and history are untouched.")
        return 0

    if sys.version_info < MIN_PYTHON:
        die(f"python {'.'.join(map(str, MIN_PYTHON))}+ required, "
            f"this is {sys.version.split()[0]}")
    say(f"python:   {sys.version.split()[0]} (stdlib only, no dependencies)")
    # Everything that can refuse, refuses here -- before a directory, a backup,
    # a symlink, or a temporary file exists.
    cfg = _load_settings(path)
    _publish_target(path, cdir)
    _validate_schema(cfg, path)
    _, _, link = commands(cdir)
    _check_install_ownership(cfg, link, cdir, path)
    if not dry_run:
        try:
            os.makedirs(cdir, exist_ok=True)
        except OSError as exc:
            die(f"cannot create {cdir}: {exc}")
    if link:
        link_checkout(link, dry_run)
    else:
        say(f"command:  {console_script()}")
    write_settings(cdir, dry_run, cfg=cfg)
    verify(cdir)
    print("\nDone. Restart Claude Code to pick it up.")
    return 0
