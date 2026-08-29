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
    for cand in (
        os.path.join(os.path.dirname(sys.executable), "agent-statusline"),
        shutil.which("agent-statusline"),
    ):
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
            die(
                "installed package but no `agent-statusline` executable found.\n"
                "       Reinstall with `uv tool install` / `pipx install`, or run "
                "install from a checkout."
            )
        quoted = shlex.quote(exe)
        return quoted, (lambda slug, _mod: f"{quoted} hook {slug}"), None
    link = os.path.join(cdir or claude_dir(), "statusline")
    python = shlex.quote(sys.executable)
    return (
        f"{python} {shlex.quote(os.path.join(link, 'statusline.py'))}",
        (lambda _slug, mod: (f"{python} {shlex.quote(os.path.join(link, 'hooks', mod + '.py'))}")),
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


def _checkout_script_match(candidate, expected):
    """Whether a checkout-shape script argument is the one written into `cdir`,
    and if so, by which form.

    The released v0.2.0 installer wrote a *literal* `~/.claude/statusline/...`
    argument and left the tilde for the shell to expand. Expanding a leading
    `~` here recognizes that shape while keeping the comparison anchored to the
    configuration directory: a legacy entry is claimed only when `~` resolves to
    the very path this installation manages, so a third-party
    `/opt/other/statusline/statusline.py` still does not match.

    Returns `"current"` for the absolute form this installer writes today,
    `"legacy"` for the v0.2.0 tilde form, or `None` for no match. Which one
    matched decides which interpreter is acceptable -- see
    `_checkout_interpreter_matches`.
    """
    if _same_path(candidate, expected):
        return "current"
    if _same_path(os.path.expanduser(candidate), expected):
        return "legacy"
    return None


def _checkout_interpreter_matches(candidate, shape):
    """Whether `candidate` is the interpreter this installer would have
    written for a checkout-shape command matched via `shape`.

    The current form always names the exact `sys.executable` this
    installation runs under -- not merely a program whose basename starts
    with "python", which would claim any interpreter on the system paired
    with the right script path. The one documented exception is the released
    v0.2.0 form, which wrote the literal bare name `python3` and relied on
    `PATH`; that exact string is recognized only alongside the matching
    legacy script-path form, not generalized to other "python*" names.
    """
    if shape == "legacy":
        return candidate == "python3"
    return candidate == sys.executable


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
    if len(tokens) != 2:
        return False
    root = os.path.join(cdir or claude_dir(), "statusline", "hooks")
    modules = {mod for _, _, mod, _ in HOOKS + STOPGAP_HOOKS}
    for mod in modules:
        shape = _checkout_script_match(tokens[1], os.path.join(root, f"{mod}.py"))
        if shape and _checkout_interpreter_matches(tokens[0], shape):
            return True
    return False


def managed_status_command(command, cdir=None):
    """Whether a status-line command belongs to this package."""
    tokens = _tokens(command)
    if len(tokens) == 1:
        return _managed_exe(tokens)
    if len(tokens) != 2:
        return False
    expected = os.path.join(cdir or claude_dir(), "statusline", "statusline.py")
    shape = _checkout_script_match(tokens[1], expected)
    return bool(shape) and _checkout_interpreter_matches(tokens[0], shape)


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
            kept = [
                hook
                for hook in group["hooks"]
                if not managed_hook_command(
                    hook.get("command") if isinstance(hook, dict) else None, cdir
                )
            ]
            taken = len(group["hooks"]) - len(kept)
            removed += taken
            if not taken:
                kept_groups.append(group)
            elif kept or set(group) - {"hooks"}:
                # Ownership covers the hook entry, not fields on its containing
                # group. A group holding only "hooks" and nothing else is debris
                # once its hooks are gone; a group carrying other data (a user's
                # `matcher`, say) is not, and survives with an empty list rather
                # than being dropped whole along with that data.
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


def _load_settings(path, cdir=None, cdir_fd=None):
    """Read existing settings. When `cdir_fd` is given -- an already-bound
    descriptor for `cdir`, see `_open_publish_dir` -- the read happens
    relative to it instead of by plain pathname, so it shares the same
    identity binding a backup or a write in the same operation uses.
    """
    if cdir_fd is None:
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

    target = _publish_target(path, cdir)
    name = os.path.basename(target)
    dfd = _open_publish_dir(target, cdir, cdir_fd)
    try:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
        except FileNotFoundError:
            return {}
        except OSError as exc:
            die(f"cannot safely read existing settings {path}: {exc}")
        try:
            with os.fdopen(fd, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            die(f"cannot safely read existing settings {path}: {exc}")
    finally:
        os.close(dfd)
    if not isinstance(cfg, dict):
        die(f"cannot safely update {path}: top-level JSON value is not an object")
    return cfg


def _backup_settings(path, cdir, cdir_fd=None):
    """Copy an existing settings file to a timestamped backup beside it.

    When `cdir_fd` is given, both the read of the existing file and the write
    of the backup happen relative to it, matching the read and the eventual
    publish in the same operation, instead of re-resolving `cdir` from a path
    string a second (and third) time. Returns the backup path, or raises via
    `die()` if there was nothing to back up (callers only reach this when a
    prior `os.path.exists` / read already found a file).
    """
    if cdir_fd is None:
        backup = f"{path}.bak.{time.strftime('%Y%m%d%H%M%S')}.{time.time_ns()}"
        try:
            shutil.copy2(path, backup)
        except OSError as exc:
            die(f"cannot back up {path}: {exc}")
        return backup

    target = _publish_target(path, cdir)
    name = os.path.basename(target)
    dfd = _open_publish_dir(target, cdir, cdir_fd)
    try:
        try:
            src_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
        except OSError as exc:
            die(f"cannot back up {path}: {exc}")
        try:
            mode = stat.S_IMODE(os.fstat(src_fd).st_mode)
            with os.fdopen(src_fd, "rb") as src:
                data = src.read()
        except OSError as exc:
            die(f"cannot back up {path}: {exc}")
    finally:
        os.close(dfd)

    backup_name = (
        f"{os.path.basename(path)}.bak." f"{time.strftime('%Y%m%d%H%M%S')}.{time.time_ns()}"
    )
    try:
        bfd = os.open(
            backup_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=cdir_fd
        )
    except OSError as exc:
        die(f"cannot create a backup of {path}: {exc}")
    published = False
    try:
        try:
            os.fchmod(bfd, mode)
        except OSError as exc:
            os.close(bfd)
            die(f"cannot set permissions on the backup of {path}: {exc}")
        with os.fdopen(bfd, "wb") as bf:
            bf.write(data)
            bf.flush()
            os.fsync(bf.fileno())
        published = True
    except OSError as exc:
        die(f"cannot create a backup of {path}: {exc}")
    finally:
        if not published:
            try:
                os.unlink(backup_name, dir_fd=cdir_fd)
            except OSError:
                pass
    return os.path.join(cdir, backup_name)


def _link_state(link, cdir_fd=None):
    """(is_symlink, target_or_None, exists) for `link`, read either by
    pathname or, when `cdir_fd` is given, relative to that already-bound
    directory descriptor -- so this check cannot be fooled by a directory
    swapped in at `cdir`'s pathname after the descriptor was opened.
    """
    name = os.path.basename(link)
    try:
        st = os.lstat(name, dir_fd=cdir_fd) if cdir_fd is not None else os.lstat(link)
    except FileNotFoundError:
        return False, None, False
    is_link = stat.S_ISLNK(st.st_mode)
    if not is_link:
        return False, None, True
    target = os.readlink(name, dir_fd=cdir_fd) if cdir_fd is not None else os.readlink(link)
    return True, target, True


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


def _check_install_ownership(cfg, link, cdir, path, cdir_fd=None):
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
        die(
            f"{path} already has a status line this package does not own:\n"
            f"       {shown}\n"
            "       Only one status line can be configured. Remove it first if "
            "you want to switch."
        )
    if not link:
        return
    is_link, target, exists = _link_state(link, cdir_fd)
    if is_link and target != PKG:
        die(
            f"{link} is a symlink this package does not own:\n"
            f"       -> {target}\n"
            "       Move it aside and re-run."
        )
    if not is_link and exists:
        die(f"{link} exists and is not a symlink. Move it aside and re-run.")


def _publish_target(path, cdir):
    """The real file settings will be written to, refusing to leave `cdir`."""
    target = os.path.realpath(path)
    root = os.path.realpath(cdir)
    if target != root and not target.startswith(root + os.sep):
        die(
            f"{path} resolves outside {cdir}:\n"
            f"       {target}\n"
            "       Refusing to write there. Point it inside the configuration "
            "directory, or move the file and remove the link."
        )
    return target


def _bind_directory(abs_path):
    """A descriptor for `abs_path`, reached by opening every path component --
    from the filesystem root down -- with `O_DIRECTORY | O_NOFOLLOW`.

    A resolved absolute path is a confinement *decision*; this walk is what
    makes it durable. Opening the resolved string directly (even just its final
    component) still trusts the OS to re-resolve every earlier component from
    scratch, and a symlink swapped in anywhere on the way -- including the very
    first component -- is followed silently. Refusing to follow a link at any
    step, starting at the root, closes that: the only way to redirect this walk
    is to replace a real directory with another real directory of the same
    name, not to point a link at one.
    """
    if not abs_path.startswith(os.sep):
        die(f"cannot safely resolve {abs_path}: not an absolute path.")
    parts = [part for part in abs_path.split(os.sep) if part]
    fd = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY)
    bound = False
    try:
        for part in parts:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        bound = True
    except OSError as exc:
        die(
            f"cannot safely reach {abs_path}: {exc}\n"
            "       A directory on the way changed while installing. Nothing "
            "was written."
        )
    finally:
        if not bound:
            os.close(fd)
    return fd


def _walk_from(fd, parts):
    """Descriptor for the directory reached by opening each of `parts`
    relative to `fd`, refusing to follow a symlink at any step. Always
    returns a descriptor the caller owns and must close -- even when `parts`
    is empty, in which case it is a dup of `fd` -- so closing it never closes
    the caller's own copy of `fd`.
    """
    cur = os.dup(fd)
    for part in parts:
        nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=cur)
        os.close(cur)
        cur = nxt
    return cur


def _open_publish_dir(target, cdir, cdir_fd=None):
    """A descriptor for the directory that will receive settings.

    `_publish_target` checks a *path*; this binds that decision to an object.
    Every later step -- create, chmod, replace -- happens relative to this
    descriptor and never names a directory again, so swapping a checked
    directory for a symlink afterwards cannot redirect publication. The walk
    refuses to traverse a link at all (`O_NOFOLLOW`), all the way from `/`
    (`_bind_directory`), so a swap that lands inside the window -- at the
    configuration root or at any parent, not only below it -- fails closed
    instead of following the attacker's link.

    A second `realpath()` check would not close this: it would re-open the
    same race it is meant to detect -- and neither does binding the root
    correctly on *this call alone*, if the directory at that pathname was
    swapped for an unrelated *ordinary* directory (no symlink at all) between
    an earlier read of `cdir` and this write. `O_NOFOLLOW` cannot catch a
    plain rename; only never re-deriving the root from a path string a second
    time can. Passing an already-bound `cdir_fd` -- opened once at the start
    of an operation via `_bind_directory` and reused for every read, backup,
    link mutation, and publication inside it -- is what closes that gap: this
    call then only walks *below* the already-trusted root, never re-resolving
    the root itself.
    """
    root = os.path.realpath(cdir)
    rel = os.path.relpath(os.path.dirname(target), root)
    parts = [] if rel == os.curdir else rel.split(os.sep)
    if any(part == os.pardir for part in parts):
        die(f"refusing to publish settings outside {cdir}")
    if cdir_fd is not None:
        try:
            return _walk_from(cdir_fd, parts)
        except OSError as exc:
            die(
                f"cannot safely reach {target}: {exc}\n"
                "       A directory on the way changed while installing. "
                "Nothing was written."
            )
    if os.open not in os.supports_dir_fd:
        die("this platform cannot publish settings safely: openat is unavailable.")
    fd = _bind_directory(root)
    bound = False
    try:
        for part in parts:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        bound = True
    except OSError as exc:
        die(
            f"cannot safely reach {target}: {exc}\n"
            "       A directory on the way changed while installing. Nothing "
            "was written."
        )
    finally:
        if not bound:
            os.close(fd)
    return fd


def _write_json_atomic(path, cfg, cdir, cdir_fd=None):
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

    `cdir_fd`, when given, is an already-bound descriptor for `cdir` reused
    from an earlier read or backup in the same operation -- see
    `_open_publish_dir` for why reuse is what actually closes INSTALL-023/025
    rather than merely repeating the same check.
    """
    target = _publish_target(path, cdir)
    name = os.path.basename(target)
    dfd = _open_publish_dir(target, cdir, cdir_fd)
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
            fd = os.open(
                tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd
            )
        except OSError as exc:
            die(f"cannot create a temporary file beside {target}: {exc}")
        published = False
        try:
            try:
                os.fchmod(fd, mode)
            except OSError as exc:
                # `fd` is still a raw descriptor here -- `os.fdopen` below is
                # what will make the temp file's lifecycle own and close it.
                # Failing before that handoff must close it explicitly, or it
                # leaks past the `SystemExit` this raises.
                os.close(fd)
                die(f"cannot set permissions on the temporary file beside {target}: {exc}")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
            published = True
        except NotImplementedError:
            die("this platform cannot publish settings safely: renameat is " "unavailable.")
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


class _LinkGuard:
    """Snapshots a checkout symlink before it is touched, so a mutation that
    fails partway through -- the link changed but settings did not, or the
    other way around -- can be rolled back to exactly what was there before.

    Install and uninstall are not one filesystem transaction; there is no way
    to make `os.symlink` and a settings write commit or fail together. What
    this buys instead: capture the prior state up front, mutate, and if
    anything downstream in the same operation dies, put the link back rather
    than leaving whatever partial change happened to land.

    Every operation is relative to `cdir_fd` -- the same bound descriptor the
    settings read, backup, and write in the same operation use -- so this
    guard cannot be fooled by a directory swapped in at `cdir`'s pathname
    after that descriptor was opened either.
    """

    def __init__(self, link, cdir_fd):
        self.link = link
        self.name = os.path.basename(link)
        self.cdir_fd = cdir_fd
        is_link, target, _ = _link_state(link, cdir_fd)
        self.existed = is_link
        self.target = target
        self.touched = False
        self.error = None

    def note_mutation(self):
        self.touched = True

    def remove(self):
        self.touched = True
        try:
            os.unlink(self.name, dir_fd=self.cdir_fd)
        except OSError as exc:
            die(f"cannot remove {self.link}: {exc}")

    def rollback(self):
        """Best-effort restoration to the pre-mutation state. Returns True if
        the prior state was restored (or nothing needed restoring), False if
        restoration itself failed -- `self.error` then names why.

        This never raises and never prints: a secondary failure here must not
        replace or mask the original error that triggered the rollback. The
        caller owns surfacing a False result -- silently discarding it is
        exactly the defect this shape exists to avoid repeating.
        """
        if not self.touched:
            return True
        try:
            _, _, exists = _link_state(self.link, self.cdir_fd)
        except OSError as exc:
            self.error = f"cannot inspect {self.link} while restoring: {exc}"
            return False
        if exists:
            try:
                os.unlink(self.name, dir_fd=self.cdir_fd)
            except OSError as exc:
                self.error = f"cannot remove {self.link} while restoring: {exc}"
                return False
        if self.existed:
            try:
                os.symlink(self.target, self.name, dir_fd=self.cdir_fd)
            except OSError as exc:
                self.error = f"cannot restore {self.link} -> {self.target}: {exc}"
                return False
        return True


def link_checkout(link, dry, guard=None, cdir_fd=None):
    """Publish the checkout symlink. Ownership is settled before this runs."""
    if dry:
        if os.path.islink(link):
            say(f"symlink:  refreshing {link}")
        say(f"symlink:  {link} -> {PKG}")
        return
    name = os.path.basename(link)
    is_link, _, _ = _link_state(link, cdir_fd)
    if is_link:
        if guard:
            guard.note_mutation()
        try:
            os.unlink(name, dir_fd=cdir_fd)
        except OSError as exc:
            die(f"cannot replace {link}: {exc}")
        say(f"symlink:  refreshing {link}")
    if guard:
        guard.note_mutation()
    try:
        os.symlink(PKG, name, dir_fd=cdir_fd)
    except OSError as exc:
        die(f"cannot create {link}: {exc}")
    say(f"symlink:  {link} -> {PKG}")


def write_settings(cdir, dry, remove=False, cfg=None, cdir_fd=None):
    path = os.path.join(cdir, "settings.json")
    if cfg is None:
        # Confinement is decided before anything is read, not only before
        # anything is written -- an out-of-tree settings.json symlink is
        # refused here rather than having its content read first.
        _publish_target(path, cdir)
        cfg = _load_settings(path, cdir, cdir_fd)
        _validate_schema(cfg, path)

    if remove:
        command = _status_command(cfg)
        owned_status = managed_status_command(command, cdir)
        if not owned_status and not _count_managed_hooks(cfg, cdir):
            say("settings: nothing owned by this package; left untouched")
            return
    if not dry and os.path.exists(path):
        backup = _backup_settings(path, cdir, cdir_fd)
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
                {"hooks": [{"type": "command", "command": hook_cmd(slug, mod), "timeout": timeout}]}
            )
        # Added when absent, never reclaimed on uninstall (ADR 0015/0020): a
        # value already there cannot be told apart from one we set.
        cfg.setdefault("showMessageTimestamps", True)
        say(f"settings: statusLine + {len(wanted)} managed hooks")

    if dry:
        return
    _write_json_atomic(path, cfg, cdir, cdir_fd)


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
        proc = subprocess.run(
            [sys.executable, os.path.join(PKG, "statusline.py")],
            input=payload,
            capture_output=True,
            env=dict(os.environ, AGENT_STATUSLINE_STATE=scratch),
        )
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


def _report_rollback_failure(guard, link):
    """Surface a failed restoration rather than let a caught `SystemExit`
    stand in as false proof the link was put back. Printed, not raised: the
    original error already reported the primary failure and must not be
    replaced by this one.
    """
    print(
        f"error: rollback also failed -- {guard.error}\n"
        f"       {link} may not match settings.json; check it by hand.",
        file=sys.stderr,
    )


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
        link = os.path.join(cdir, "statusline")
        if dry_run:
            # Full pre-flight before the first mutation. Removing the symlink
            # and then refusing on malformed settings leaves settings
            # pointing at a link that no longer exists, which is worse than
            # not starting.
            _publish_target(path, cdir)
            cfg = _load_settings(path)
            _validate_schema(cfg, path)
            is_link, target, exists = _link_state(link)
            if is_link and target == PKG:
                say(f"symlink:  removed {link}")
            elif exists:
                say(f"symlink:  preserved non-managed path {link}")
            write_settings(cdir, dry_run, remove=True, cfg=cfg)
            print("\nDone. Your ledger and history are untouched.")
            return 0
        if not os.path.isdir(cdir):
            # Nothing was ever installed into a configuration directory that
            # does not exist yet; there is nothing to bind or protect.
            say("settings: nothing owned by this package; left untouched")
            print("\nDone. Your ledger and history are untouched.")
            return 0
        # Bound once, here, and reused for every read, backup, link removal,
        # and settings write below -- the identity binding INSTALL-023/025
        # require. Re-deriving the root from `cdir` a second time anywhere
        # after this would reopen exactly the gap it closes: `O_NOFOLLOW`
        # stops a symlink swap, but not `cdir`'s pathname being handed to an
        # unrelated ordinary directory between an earlier check and a later
        # mutation.
        cdir_fd = _bind_directory(os.path.realpath(cdir))
        try:
            _publish_target(path, cdir)
            cfg = _load_settings(path, cdir, cdir_fd)
            _validate_schema(cfg, path)
            is_link, target, exists = _link_state(link, cdir_fd)
            owns_link = is_link and target == PKG
            guard = _LinkGuard(link, cdir_fd)
            # The link removal and the settings rewrite are not one atomic
            # operation. If the settings half dies -- an expected filesystem
            # failure, not a bug -- the guard restores exactly the link state
            # that existed before this uninstall began, rather than leaving a
            # removed link with settings that still name it. A failure while
            # restoring is itself reported rather than swallowed.
            try:
                if owns_link:
                    guard.remove()
                    say(f"symlink:  removed {link}")
                elif exists:
                    say(f"symlink:  preserved non-managed path {link}")
                write_settings(cdir, dry_run, remove=True, cfg=cfg, cdir_fd=cdir_fd)
            except SystemExit:
                if not guard.rollback():
                    _report_rollback_failure(guard, link)
                raise
        finally:
            os.close(cdir_fd)
        print("\nDone. Your ledger and history are untouched.")
        return 0

    if sys.version_info < MIN_PYTHON:
        die(
            f"python {'.'.join(map(str, MIN_PYTHON))}+ required, "
            f"this is {sys.version.split()[0]}"
        )
    say(f"python:   {sys.version.split()[0]} (stdlib only, no dependencies)")
    _, _, link = commands(cdir)

    if dry_run:
        # Everything that can refuse, refuses here -- before a directory, a
        # backup, a symlink, or a temporary file exists.
        _publish_target(path, cdir)
        cfg = _load_settings(path)
        _validate_schema(cfg, path)
        _check_install_ownership(cfg, link, cdir, path)
        if link:
            link_checkout(link, dry_run)
        else:
            say(f"command:  {console_script()}")
        write_settings(cdir, dry_run, cfg=cfg)
        verify(cdir)
        print("\nDone. Restart Claude Code to pick it up.")
        return 0

    try:
        os.makedirs(cdir, exist_ok=True)
    except OSError as exc:
        die(f"cannot create {cdir}: {exc}")
    # See the uninstall branch above for why this is bound once and reused
    # rather than re-derived from `cdir` at each step.
    cdir_fd = _bind_directory(os.path.realpath(cdir))
    try:
        _publish_target(path, cdir)
        cfg = _load_settings(path, cdir, cdir_fd)
        _validate_schema(cfg, path)
        _check_install_ownership(cfg, link, cdir, path, cdir_fd)
        install_guard = _LinkGuard(link, cdir_fd) if link else None
        # The checkout symlink and the settings rewrite are two separate
        # mutations with no shared commit point. If the settings half dies
        # after the link has already been created or replaced, the guard
        # undoes exactly that link change -- restoring a pre-existing link to
        # its original target, or removing one this run just created --
        # rather than leaving a link with no matching settings, or settings
        # unchanged behind a link that moved. A failure while restoring is
        # itself reported rather than swallowed.
        try:
            if link:
                link_checkout(link, dry_run, install_guard, cdir_fd)
            else:
                say(f"command:  {console_script()}")
            write_settings(cdir, dry_run, cfg=cfg, cdir_fd=cdir_fd)
        except SystemExit:
            if install_guard and not install_guard.rollback():
                _report_rollback_failure(install_guard, link)
            raise
        verify(cdir)
    finally:
        os.close(cdir_fd)
    print("\nDone. Restart Claude Code to pick it up.")
    return 0
