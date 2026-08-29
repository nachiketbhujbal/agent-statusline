"""The `agent-statusline` entry point and the two install shapes."""
import io
import json
import os
import shlex
import shutil
import stat

import pytest

from agent_statusline import cli, installer


def run(argv, monkeypatch, stdin="{}"):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    return cli.main(argv)


class TestDispatch:
    def test_no_arguments_renders(self, monkeypatch, capsys):
        assert run([], monkeypatch) == 0
        assert "PROJECT" in capsys.readouterr().out

    def test_render_subcommand_is_the_same(self, monkeypatch, capsys):
        assert run(["render"], monkeypatch) == 0
        assert "PROJECT" in capsys.readouterr().out

    def test_version(self, monkeypatch, capsys):
        from agent_statusline import __version__
        assert run(["version"], monkeypatch) == 0
        assert capsys.readouterr().out.strip() == __version__

    def test_help(self, monkeypatch, capsys):
        assert run(["--help"], monkeypatch) == 0
        assert "agent-statusline install" in capsys.readouterr().out

    def test_unknown_command_is_an_error(self, monkeypatch, capsys):
        assert run(["nonsense"], monkeypatch) == 2

    def test_unknown_install_option_is_an_error(self, monkeypatch, capsys):
        assert run(["install", "--wat"], monkeypatch) == 2


class TestHooks:
    @pytest.mark.parametrize("name", sorted(cli.HOOKS))
    def test_every_hook_is_reachable_and_exits_clean(self, name, monkeypatch, capsys):
        payload = json.dumps({"session_id": "cli-test", "transcript_path": "/nope"})
        assert run(["hook", name], monkeypatch, stdin=payload) == 0

    def test_unknown_hook_is_an_error(self, monkeypatch, capsys):
        assert run(["hook", "nope"], monkeypatch) == 2

    def test_hook_with_no_name_is_an_error(self, monkeypatch, capsys):
        assert run(["hook"], monkeypatch) == 2

    def test_every_advertised_hook_module_exists(self):
        for slug, mod in cli.HOOKS.items():
            m = __import__(f"agent_statusline.hooks.{mod}", fromlist=["main"])
            assert callable(m.main), slug


class TestInstallShape:
    def test_a_checkout_is_detected_as_a_checkout(self):
        """The test suite runs from the working tree, so this is one."""
        root = installer.checkout_root()
        assert root and os.path.exists(os.path.join(root, "pyproject.toml"))

    def test_a_checkout_wires_through_the_symlink(self):
        status_cmd, hook_cmd, link = installer.commands()
        assert status_cmd.endswith("/.claude/statusline/statusline.py")
        assert hook_cmd("session-end", "session_end").endswith("hooks/session_end.py")
        assert link and link.endswith("statusline")

    def test_checkout_commands_honor_a_custom_config_directory(self, tmp_path):
        status_cmd, hook_cmd, link = installer.commands(str(tmp_path))
        assert str(tmp_path) in status_cmd
        assert str(tmp_path) in hook_cmd("session-end", "session_end")
        assert link == str(tmp_path / "statusline")

    def test_an_installed_package_wires_through_the_console_script(self, monkeypatch,
                                                                   tmp_path):
        exe = tmp_path / "agent-statusline"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        monkeypatch.setattr(installer, "checkout_root", lambda: None)
        monkeypatch.setattr(installer, "console_script", lambda: str(exe))
        status_cmd, hook_cmd, link = installer.commands()
        assert status_cmd == shlex.quote(str(exe))
        assert hook_cmd("session-end", "session_end") == (
            f"{shlex.quote(str(exe))} hook session-end"
        )
        assert link is None, "an installed package must not symlink anything"

    def test_installed_with_no_executable_is_fatal(self, monkeypatch):
        monkeypatch.setattr(installer, "checkout_root", lambda: None)
        monkeypatch.setattr(installer, "console_script", lambda: None)
        with pytest.raises(SystemExit):
            installer.commands()


class TestSettings:
    def test_dry_run_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        installer.write_settings(str(tmp_path), dry=True)
        assert not (tmp_path / "settings.json").exists()

    def test_install_preserves_unrelated_settings(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({"theme": "dark", "model": "opus"}))
        installer.write_settings(str(tmp_path), dry=False)
        out = json.loads(cfg.read_text())
        assert out["theme"] == "dark" and out["model"] == "opus"
        assert out["statusLine"]["command"]
        assert "SessionEnd" in out["hooks"]

    def test_install_preserves_unrelated_hooks_in_managed_events(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(installer, "native_timestamps", lambda: False)
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({
            "hooks": {
                "SessionEnd": [{"hooks": [{"type": "command", "command": "keep-end"}]}],
                "UserPromptSubmit": [
                    {"matcher": "x", "hooks": [{"type": "command", "command": "keep-submit"}]}
                ],
                "Stop": [{"hooks": [{"type": "command", "command": "keep-stop"}]}],
                "PreToolUse": [{"hooks": [{"type": "command", "command": "keep-pre"}]}],
            }
        }))
        installer.write_settings(str(tmp_path), dry=False)
        out = json.loads(cfg.read_text())
        commands = {
            event: [hook["command"] for group in groups for hook in group["hooks"]]
            for event, groups in out["hooks"].items()
        }
        assert "keep-end" in commands["SessionEnd"]
        assert "keep-submit" in commands["UserPromptSubmit"]
        assert "keep-stop" in commands["Stop"]
        assert commands["PreToolUse"] == ["keep-pre"]

    def test_malformed_existing_settings_fail_closed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        original = b"{ malformed but valuable settings"
        cfg.write_bytes(original)
        with pytest.raises(SystemExit):
            installer.write_settings(str(tmp_path), dry=False)
        assert cfg.read_bytes() == original
        assert not list(tmp_path.glob("settings.json.bak.*"))

    def test_install_backs_the_file_up_first(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark"}))
        installer.write_settings(str(tmp_path), dry=False)
        assert list(tmp_path.glob("settings.json.bak.*"))

    def test_uninstall_removes_only_what_it_added(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(installer, "native_timestamps", lambda: False)
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({
            "theme": "dark",
            "hooks": {
                "SessionEnd": [{"hooks": [{"type": "command", "command": "keep-end"}]}],
                "Stop": [{"hooks": [{"type": "command", "command": "keep-stop"}]}],
            },
        }))
        installer.write_settings(str(tmp_path), dry=False)
        installer.write_settings(str(tmp_path), dry=False, remove=True)
        out = json.loads(cfg.read_text())
        assert out["theme"] == "dark"
        assert "statusLine" not in out
        commands = {
            event: [hook["command"] for group in groups for hook in group["hooks"]]
            for event, groups in out["hooks"].items()
        }
        assert commands == {"SessionEnd": ["keep-end"], "Stop": ["keep-stop"]}

    def test_uninstall_preserves_a_replaced_status_line(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({
            "statusLine": {"type": "command", "command": "some-other-statusline"}
        }))
        installer.write_settings(str(tmp_path), dry=False, remove=True)
        assert json.loads(cfg.read_text())["statusLine"]["command"] == "some-other-statusline"

    def test_reinstalling_does_not_duplicate_hooks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        for _ in range(3):
            installer.write_settings(str(tmp_path), dry=False)
        out = json.loads((tmp_path / "settings.json").read_text())
        total = sum(len(g["hooks"]) for v in out["hooks"].values() for g in v)
        assert total == len(installer.HOOKS) + len(installer.STOPGAP_HOOKS)

    def test_settings_symlink_is_published_through_not_replaced(self, tmp_path, monkeypatch):
        """A dotfiles checkout symlinked into ~/.claude must survive an install."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        dotfiles = tmp_path / "linked"
        dotfiles.mkdir()
        real = dotfiles / "settings.json"
        real.write_text(json.dumps({"theme": "dark"}))
        real.chmod(0o600)
        link = tmp_path / "settings.json"
        link.symlink_to(real)

        installer.write_settings(str(tmp_path), dry=False)

        assert link.is_symlink(), "the user's indirection must be preserved"
        assert os.path.realpath(link) == str(real)
        out = json.loads(real.read_text())
        assert out["theme"] == "dark", "the real file must receive the update"
        assert out["statusLine"]["command"]

    def test_settings_symlink_does_not_widen_permissions(self, tmp_path, monkeypatch):
        """A symlink's own 0o777 bits must never become the settings file's mode."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        dotfiles = tmp_path / "linked"
        dotfiles.mkdir()
        real = dotfiles / "settings.json"
        real.write_text(json.dumps({"theme": "dark"}))
        real.chmod(0o600)
        (tmp_path / "settings.json").symlink_to(real)

        installer.write_settings(str(tmp_path), dry=False)

        assert stat.S_IMODE(real.stat().st_mode) == 0o600

    def test_existing_settings_keep_their_mode_and_new_ones_are_private(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        installer.write_settings(str(tmp_path), dry=False)
        created = tmp_path / "settings.json"
        assert stat.S_IMODE(created.stat().st_mode) == 0o600

        created.chmod(0o640)
        installer.write_settings(str(tmp_path), dry=False)
        assert stat.S_IMODE(created.stat().st_mode) == 0o640

    def test_a_failed_publish_leaves_no_temp_file_and_preserves_bytes(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({"theme": "dark"}))
        original = cfg.read_bytes()

        def explode(*_args, **_kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(installer.os, "replace", explode)
        # An expected filesystem failure exits with a message, not a traceback.
        with pytest.raises(SystemExit):
            installer.write_settings(str(tmp_path), dry=False)

        assert cfg.read_bytes() == original
        assert not list(tmp_path.glob(".settings.json.*")), "no abandoned temp file"

    def test_repeated_cycles_never_collide_on_a_backup_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark"}))
        for _ in range(5):
            installer.write_settings(str(tmp_path), dry=False)
            installer.write_settings(str(tmp_path), dry=False, remove=True)
        backups = list(tmp_path.glob("settings.json.bak.*"))
        assert len(backups) == 10, "every cycle keeps its own backup"
        assert len({b.name for b in backups}) == len(backups)

    def test_a_configuration_path_containing_spaces_round_trips(self, tmp_path):
        spaced = tmp_path / "my claude config"
        spaced.mkdir()
        status, hook, link = installer.commands(str(spaced))
        assert installer.managed_status_command(status, str(spaced))
        assert installer.managed_hook_command(hook("session-end", "session_end"), str(spaced))
        assert shlex.split(status)[1].startswith(str(spaced))

    def test_settings_in_a_directory_containing_spaces_are_written(self, tmp_path, monkeypatch):
        spaced = tmp_path / "my claude config"
        spaced.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(spaced))
        installer.write_settings(str(spaced), dry=False)
        out = json.loads((spaced / "settings.json").read_text())
        assert installer.managed_status_command(out["statusLine"]["command"], str(spaced))

    def test_unparseable_commands_are_never_claimed_as_managed(self):
        for broken in ('python "unclosed', "python 'unclosed", '"', None, 42, ""):
            assert not installer.managed_status_command(broken)
            assert not installer.managed_hook_command(broken)

    def test_a_hook_command_with_spaces_is_preserved(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        keep = '"/opt/my tools/notify" --event session-end'
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({
            "hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": keep}]}]}
        }))
        installer.write_settings(str(tmp_path), dry=False)
        installer.write_settings(str(tmp_path), dry=False, remove=True)
        out = json.loads(cfg.read_text())
        kept = [h["command"] for g in out["hooks"]["SessionEnd"] for h in g["hooks"]]
        assert kept == [keep]

    def test_malformed_hook_containers_are_preserved(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({
            "hooks": {
                "SessionEnd": ["a valuable string a schema change introduced", {"hooks": "later"}],
            }
        }))
        installer.write_settings(str(tmp_path), dry=False, remove=True)
        out = json.loads(cfg.read_text())
        assert out["hooks"]["SessionEnd"][0] == "a valuable string a schema change introduced"
        assert out["hooks"]["SessionEnd"][1] == {"hooks": "later"}

    def test_a_non_object_hooks_container_fails_closed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        original = json.dumps({"hooks": ["not an object"]})
        cfg.write_text(original)
        with pytest.raises(SystemExit):
            installer.write_settings(str(tmp_path), dry=False)
        assert json.loads(cfg.read_text()) == {"hooks": ["not an object"]}

    def test_a_refused_install_creates_no_checkout_symlink(self, tmp_path, monkeypatch):
        """Failing closed must mean nothing changed, not 'settings survived'."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        original = b"{ malformed but valuable settings"
        cfg.write_bytes(original)

        with pytest.raises(SystemExit):
            installer.run()

        assert cfg.read_bytes() == original
        assert not (tmp_path / "statusline").exists(), "no half-installed symlink"
        assert not list(tmp_path.glob("settings.json.bak.*"))

    def test_ownership_is_anchored_to_the_configuration_directory(self, tmp_path):
        """A suffix match would claim any tool whose files live in a 'statusline' dir."""
        mine = installer.commands(str(tmp_path))
        assert installer.managed_status_command(mine[0], str(tmp_path))
        assert installer.managed_hook_command(mine[1]("session-end", "session_end"), str(tmp_path))

        for stranger in (
            "python3 /home/me/my-own-tool/statusline/statusline.py",
            "python /opt/other/statusline/statusline.py",
        ):
            assert not installer.managed_status_command(stranger, str(tmp_path))
        assert not installer.managed_hook_command(
            "python3 /home/me/my-own-tool/statusline/hooks/session_end.py", str(tmp_path)
        )

    def test_uninstall_preserves_a_third_party_status_line_and_hooks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        stranger_status = "python3 /home/me/my-own-tool/statusline/statusline.py"
        stranger_hook = "python3 /home/me/my-own-tool/statusline/hooks/session_end.py"
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({
            "statusLine": {"type": "command", "command": stranger_status},
            "hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": stranger_hook}]}]},
        }))

        installer.write_settings(str(tmp_path), dry=False, remove=True)

        out = json.loads(cfg.read_text())
        assert out["statusLine"]["command"] == stranger_status
        kept = [h["command"] for g in out["hooks"]["SessionEnd"] for h in g["hooks"]]
        assert kept == [stranger_hook]

    def test_settings_resolving_outside_the_config_directory_are_refused(
        self, tmp_path, monkeypatch
    ):
        """Following a link anywhere would make the installer a write-anywhere tool."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "unrelated.json"
        original = json.dumps({"registry": "https://example.invalid"})
        victim.write_text(original)
        (cdir / "settings.json").symlink_to(victim)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        with pytest.raises(SystemExit):
            installer.write_settings(str(cdir), dry=False)

        assert victim.read_text() == original, "an unrelated file must never be rewritten"

    def test_a_refused_uninstall_leaves_the_symlink_in_place(self, tmp_path, monkeypatch):
        """Uninstall must fail closed the same way install does."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        original = b"{ malformed but valuable settings"
        cfg.write_bytes(original)
        link = tmp_path / "statusline"
        link.symlink_to(installer.PKG)

        with pytest.raises(SystemExit):
            installer.run(uninstall=True)

        assert link.is_symlink(), "removing the link then refusing is worse than not starting"
        assert cfg.read_bytes() == original

    def test_uninstall_preserves_a_non_owned_checkout_symlink(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark"}))
        foreign = tmp_path / "somebody-elses-package"
        foreign.mkdir()
        link = tmp_path / "statusline"
        link.symlink_to(foreign)

        installer.run(uninstall=True)

        assert link.is_symlink() and os.path.realpath(link) == str(foreign.resolve())

    def test_uninstall_removes_its_own_checkout_symlink(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark"}))
        link = tmp_path / "statusline"
        link.symlink_to(installer.PKG)

        installer.run(uninstall=True)

        assert not link.exists() and not link.is_symlink()

    def test_a_non_object_settings_file_fails_closed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        original = json.dumps(["a", "list", "not", "an", "object"])
        cfg.write_text(original)
        with pytest.raises(SystemExit):
            installer.write_settings(str(tmp_path), dry=False)
        assert cfg.read_text() == original

    def test_the_suite_never_reads_a_live_claude_config(self):
        """Guards the README claim that no test touches the real ~/.claude."""
        home = os.environ["HOME"]
        assert os.path.basename(home).startswith("agent-statusline-home-")
        assert not os.path.exists(os.path.join(home, ".claude.json"))

    def test_an_out_of_tree_refusal_writes_no_backup(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "unrelated.json"
        victim.write_text(json.dumps({"registry": "https://example.invalid"}))
        (cdir / "settings.json").symlink_to(victim)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        with pytest.raises(SystemExit):
            installer.write_settings(str(cdir), dry=False)

        assert not list(cdir.glob("settings.json.bak.*")), "a refusal must change nothing"


def _snapshot(cdir):
    """Everything a refused operation promises not to change."""
    settings = cdir / "settings.json"
    return {
        "bytes": settings.read_bytes() if settings.exists() else None,
        "link": os.readlink(str(cdir / "statusline"))
        if os.path.islink(str(cdir / "statusline")) else None,
        "link_exists": os.path.lexists(str(cdir / "statusline")),
        "backups": sorted(p.name for p in cdir.glob("settings.json.bak.*")),
        "temps": sorted(p.name for p in cdir.glob(".settings.json.*")),
    }


class TestOwnershipIsAnchoredToAnExactCommand:
    """INSTALL-010: a shared basename is not ownership.

    `/opt/foreign/agent-statusline` is a different program from ours. Matching on
    the basename claimed it, and claiming it meant deleting it.
    """

    def _installed(self, monkeypatch, tmp_path):
        exe = tmp_path / "bin" / "agent-statusline"
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        monkeypatch.setattr(installer, "checkout_root", lambda: None)
        monkeypatch.setattr(installer, "console_script", lambda: str(exe))
        return exe

    def test_the_exact_installed_status_command_is_owned(self, monkeypatch, tmp_path):
        exe = self._installed(monkeypatch, tmp_path)
        assert installer.managed_status_command(shlex.quote(str(exe)))

    @pytest.mark.parametrize(
        "slug", sorted({s for _, s, _, _ in installer.HOOKS + installer.STOPGAP_HOOKS})
    )
    def test_every_installed_hook_slug_is_owned(self, slug, monkeypatch, tmp_path):
        exe = self._installed(monkeypatch, tmp_path)
        assert installer.managed_hook_command(f"{shlex.quote(str(exe))} hook {slug}")

    def test_a_same_basename_different_path_status_line_is_not_owned(
        self, monkeypatch, tmp_path
    ):
        self._installed(monkeypatch, tmp_path)
        assert not installer.managed_status_command("/opt/foreign/agent-statusline")

    @pytest.mark.parametrize(
        "slug", sorted({s for _, s, _, _ in installer.HOOKS + installer.STOPGAP_HOOKS})
    )
    def test_a_same_basename_different_path_hook_is_not_owned(
        self, slug, monkeypatch, tmp_path
    ):
        self._installed(monkeypatch, tmp_path)
        assert not installer.managed_hook_command(f"/opt/foreign/agent-statusline hook {slug}")

    def test_an_unrelated_tool_survives_a_full_uninstall(self, monkeypatch, tmp_path):
        """The whole point, proven through `run()` rather than the predicate."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        self._installed(monkeypatch, tmp_path)
        original = {
            "statusLine": {"type": "command",
                           "command": "/opt/foreign/agent-statusline", "padding": 0},
            "hooks": {"SessionEnd": [{"hooks": [
                {"type": "command",
                 "command": "/opt/foreign/agent-statusline hook session-end"}]}]},
            "keepMe": True,
        }
        settings = cdir / "settings.json"
        settings.write_text(json.dumps(original, indent=2))
        before = settings.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run(uninstall=True) == 0

        assert json.loads(settings.read_text()) == original
        assert settings.read_bytes() == before, "a pure no-op rewrites nothing"


class TestLegacyReleaseCompatibility:
    """INSTALL-015: v0.2.0 wrote a literal `~/.claude/...` command.

    Those installations must still be recognized, or a reinstall stacks a second
    set of hooks on top and an uninstall leaves the first set behind.
    """

    LEGACY_STATUS = "python3 ~/.claude/statusline/statusline.py"

    @pytest.fixture
    def home_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        cdir = tmp_path / ".claude"
        cdir.mkdir()
        return cdir

    def test_the_released_status_command_is_recognized(self, home_config):
        assert installer.managed_status_command(self.LEGACY_STATUS, str(home_config))

    @pytest.mark.parametrize(
        "mod", sorted({m for _, _, m, _ in installer.HOOKS + installer.STOPGAP_HOOKS})
    )
    def test_every_released_hook_command_is_recognized(self, mod, home_config):
        cmd = f"python3 ~/.claude/statusline/hooks/{mod}.py"
        assert installer.managed_hook_command(cmd, str(home_config))

    @pytest.mark.parametrize("cmd", [
        "python3 /opt/other/statusline/statusline.py",
        "python3 ~/.config/statusline/statusline.py",
        "python3 ~/elsewhere/statusline/statusline.py",
    ])
    def test_a_lookalike_path_is_not_claimed(self, cmd, home_config):
        """The tilde is expanded, not treated as a wildcard suffix."""
        assert not installer.managed_status_command(cmd, str(home_config))

    def test_a_legacy_config_dir_does_not_claim_a_custom_one(self, tmp_path):
        """`~/.claude/...` is not owned when the config dir is somewhere else."""
        assert not installer.managed_status_command(self.LEGACY_STATUS, str(tmp_path))

    def _legacy_settings(self):
        def hook(mod, timeout):
            return {"hooks": [{"type": "command",
                               "command": f"python3 ~/.claude/statusline/hooks/{mod}.py",
                               "timeout": timeout}]}
        return {
            "statusLine": {"type": "command", "command": self.LEGACY_STATUS, "padding": 0},
            "hooks": {
                "SessionEnd": [hook("session_end", 10)],
                "UserPromptSubmit": [hook("context_guard", 10), hook("timestamp_user", 5)],
                "Stop": [hook("timestamp_stop", 5)],
            },
            "keepMe": True,
        }

    def test_upgrading_from_the_release_does_not_stack_hooks(self, home_config):
        settings = home_config / "settings.json"
        settings.write_text(json.dumps(self._legacy_settings(), indent=2))

        assert installer.run() == 0

        cfg = json.loads(settings.read_text())
        total = sum(len(g["hooks"]) for groups in cfg["hooks"].values() for g in groups)
        assert total == 4, "the released hooks were replaced, not appended to"
        assert cfg["keepMe"] is True

    def test_uninstalling_a_release_installation_leaves_nothing_behind(self, home_config):
        settings = home_config / "settings.json"
        settings.write_text(json.dumps(self._legacy_settings(), indent=2))

        assert installer.run(uninstall=True) == 0

        cfg = json.loads(settings.read_text())
        assert "statusLine" not in cfg
        assert "hooks" not in cfg
        assert cfg["keepMe"] is True


class TestInstallRefusesBeforeMutating:
    """INSTALL-011/012: nothing is created before every refusal has had its say."""

    def test_a_foreign_status_line_is_never_overwritten(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps(
            {"statusLine": {"type": "command", "command": "some-other-statusline"}}))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        before = _snapshot(cdir)

        with pytest.raises(SystemExit):
            installer.run()

        assert _snapshot(cdir) == before

    @pytest.mark.parametrize("entry", [
        pytest.param("some-other-tool", id="a-bare-string"),
        pytest.param(["some-other-tool"], id="a-list"),
        pytest.param({"type": "command", "padding": 0}, id="a-dict-with-no-command"),
        pytest.param({"type": "command", "command": 12345}, id="a-non-string-command"),
        pytest.param({"type": "text", "text": "hello"}, id="a-different-shaped-dict"),
        pytest.param({"command": None}, id="an-explicit-null-command"),
    ])
    def test_a_status_line_we_cannot_read_is_never_overwritten(
        self, entry, tmp_path, monkeypatch
    ):
        """Unprovable is not unowned.

        Refusing only when a command string can be parsed out left every other
        shape to be silently replaced -- the same unrecoverable loss, reached by
        a `statusLine` the matcher simply could not read.
        """
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"statusLine": entry, "keepMe": True}))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        before = _snapshot(cdir)

        with pytest.raises(SystemExit):
            installer.run()

        assert _snapshot(cdir) == before
        assert json.loads(settings.read_text())["statusLine"] == entry

    def test_a_null_status_line_is_treated_as_absent(self, tmp_path, monkeypatch):
        """JSON null is nothing configured, not something to protect."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        (cdir / "settings.json").write_text(json.dumps({"statusLine": None}))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run() == 0

        cfg = json.loads((cdir / "settings.json").read_text())
        assert installer.managed_status_command(cfg["statusLine"]["command"], str(cdir))

    def test_an_unreadable_status_line_is_preserved_by_uninstall_too(
        self, tmp_path, monkeypatch
    ):
        """Install and uninstall must agree about what they cannot prove."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"statusLine": "some-other-tool", "keepMe": True}))
        before = settings.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run(uninstall=True) == 0

        assert settings.read_bytes() == before

    def test_a_foreign_checkout_symlink_is_never_replaced(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        other = tmp_path / "other-package"
        other.mkdir()
        os.symlink(str(other), str(cdir / "statusline"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        before = _snapshot(cdir)

        with pytest.raises(SystemExit):
            installer.run()

        assert _snapshot(cdir) == before
        assert os.path.realpath(str(cdir / "statusline")) == str(other)

    def test_reinstalling_over_our_own_configuration_is_idempotent(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        assert installer.run() == 0
        first = json.loads((cdir / "settings.json").read_text())

        assert installer.run() == 0

        assert json.loads((cdir / "settings.json").read_text()) == first

    def test_a_non_object_hooks_container_stops_before_the_symlink(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        (cdir / "settings.json").write_text(json.dumps({"hooks": ["valuable"]}))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        before = _snapshot(cdir)

        with pytest.raises(SystemExit):
            installer.run()

        assert _snapshot(cdir) == before
        assert not before["link_exists"] and not before["backups"]

    def test_a_non_object_hooks_container_also_fails_uninstall_closed(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        (cdir / "settings.json").write_text(json.dumps({"hooks": ["valuable"]}))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        before = _snapshot(cdir)

        with pytest.raises(SystemExit):
            installer.run(uninstall=True)

        assert _snapshot(cdir) == before

    @pytest.mark.parametrize("uninstall", [False, True])
    def test_a_non_list_event_container_is_refused_before_any_mutation(
        self, uninstall, tmp_path, monkeypatch
    ):
        """`{"SessionEnd": "valuable"}` used to reach `.append` and raise."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        (cdir / "settings.json").write_text(json.dumps({"hooks": {"SessionEnd": "valuable"}}))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        before = _snapshot(cdir)

        with pytest.raises(SystemExit):
            installer.run(uninstall=uninstall)

        assert _snapshot(cdir) == before

    def test_settings_reached_through_an_outside_link_stop_before_the_symlink(
        self, tmp_path, monkeypatch
    ):
        """INSTALL-015: confinement is checked before the link is touched."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "other-tool.json"
        victim.write_text(json.dumps({"registry": "https://example.invalid"}))
        original = victim.read_bytes()
        (cdir / "settings.json").symlink_to(victim)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        with pytest.raises(SystemExit):
            installer.run()

        assert victim.read_bytes() == original
        assert not os.path.lexists(str(cdir / "statusline"))

    def test_an_outside_link_stops_uninstall_before_removing_the_symlink(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "other-tool.json"
        victim.write_text(json.dumps({"registry": "https://example.invalid"}))
        (cdir / "settings.json").symlink_to(victim)
        os.symlink(installer.PKG, str(cdir / "statusline"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        with pytest.raises(SystemExit):
            installer.run(uninstall=True)

        assert os.path.islink(str(cdir / "statusline")), "the link survives a refusal"


class TestUninstallIsATrueNoOp:
    """Removing nothing must write nothing."""

    def test_uninstall_with_no_settings_creates_no_file(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run(uninstall=True) == 0

        assert not (cdir / "settings.json").exists(), "no empty {} left behind"
        assert not list(cdir.glob("settings.json.bak.*"))

    def test_uninstall_with_nothing_owned_writes_no_backup(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"theme": "dark", "hooks": {"Notification": []}}))
        before = settings.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run(uninstall=True) == 0

        assert settings.read_bytes() == before
        assert not list(cdir.glob("settings.json.bak.*"))

    def test_an_empty_foreign_hook_group_keeps_its_shape(self, tmp_path, monkeypatch):
        """Unrelated entries keep their order and shape, not just their commands."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        assert installer.run() == 0
        cfg = json.loads((cdir / "settings.json").read_text())
        cfg["hooks"]["SessionEnd"].insert(0, {"matcher": "keep-me", "hooks": []})
        cfg["hooks"]["Notification"] = []
        (cdir / "settings.json").write_text(json.dumps(cfg, indent=2))

        assert installer.run(uninstall=True) == 0

        after = json.loads((cdir / "settings.json").read_text())
        assert after["hooks"]["SessionEnd"] == [{"matcher": "keep-me", "hooks": []}]
        assert after["hooks"]["Notification"] == []


class TestVerificationIsolation:
    """INSTALL-013/016: verification is a preview, not a mutation."""

    def test_a_pre_existing_verify_state_directory_survives(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        scratch = cdir / ".verify-state"
        scratch.mkdir()
        precious = scratch / "user-data.json"
        precious.write_text(json.dumps({"keep": "me"}))
        original = precious.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run() == 0

        assert precious.read_bytes() == original, "verification deleted user data"

    def test_a_dry_run_against_an_absent_directory_creates_nothing(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "absent"
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run(dry_run=True) == 0

        assert not cdir.exists(), "dry run promised to write nothing"

    def test_verification_scratch_state_never_lands_in_the_config_dir(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        assert installer.run() == 0

        assert not (cdir / ".verify-state").exists()


class TestExpectedFilesystemFailures:
    """INSTALL-014: an expected `OSError` is a message, not a traceback."""

    def test_a_read_only_configuration_directory_is_reported(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"theme": "dark"}))
        original = settings.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        cdir.chmod(0o500)
        try:
            with pytest.raises(SystemExit):
                installer.write_settings(str(cdir), dry=False)
        finally:
            cdir.chmod(0o700)

        assert settings.read_bytes() == original
        assert not list(cdir.glob(".settings.json.*"))

    def test_a_missing_configuration_directory_is_reported(self, tmp_path, monkeypatch):
        cdir = tmp_path / "gone"
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        with pytest.raises(SystemExit):
            installer.write_settings(str(cdir), dry=False)

    def test_a_failed_backup_is_reported_and_changes_nothing(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"theme": "dark"}))
        original = settings.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        def explode(*_args, **_kwargs):
            raise OSError("no space left on device")

        monkeypatch.setattr(installer.shutil, "copy2", explode)
        with pytest.raises(SystemExit):
            installer.write_settings(str(cdir), dry=False)

        assert settings.read_bytes() == original
        assert not list(cdir.glob(".settings.json.*"))

    def test_a_failed_symlink_publication_is_reported(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        def explode(*_args, **_kwargs):
            raise OSError("operation not permitted")

        monkeypatch.setattr(installer.os, "symlink", explode)
        with pytest.raises(SystemExit):
            installer.run()


class TestPublicationCannotBeRedirected:
    """INSTALL-017: the confinement decision is bound to a descriptor.

    A path check followed by path-named writes leaves a window: swap a checked
    directory for a symlink inside it and publication follows the attacker's
    link. Every write below happens relative to an already-opened descriptor,
    and the walk that produces it refuses to traverse a link at all.
    """

    def test_a_directory_swapped_after_the_check_fails_closed(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        (cdir / "sub").mkdir(parents=True)
        real = cdir / "sub" / "real.json"
        real.write_text(json.dumps({"theme": "dark"}))
        (cdir / "settings.json").symlink_to(real)

        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "real.json"
        victim.write_text(json.dumps({"registry": "https://example.invalid"}))
        original = victim.read_bytes()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        real_publish_target = installer._publish_target
        swapped = []

        def swap_then_return(path, cdir_arg):
            """Stand in for losing the race, deterministically.

            The swap lands *after* confinement is decided and before the
            descriptor is opened -- the exact window a second `realpath()` check
            cannot see, because it would simply re-run the same race.
            """
            target = real_publish_target(path, cdir_arg)
            sub = cdir / "sub"
            if not swapped:
                swapped.append(True)
                shutil.rmtree(str(sub))
                os.symlink(str(elsewhere), str(sub))
            return target

        monkeypatch.setattr(installer, "_publish_target", swap_then_return)

        # Called directly: `write_settings` resolves the path twice, so going
        # through it would let the second resolution catch the swap and prove
        # nothing about the descriptor.
        with pytest.raises(SystemExit):
            installer._write_json_atomic(
                str(cdir / "settings.json"), {"ours": True}, str(cdir))

        assert swapped, "the injected swap never ran; the test proves nothing"

        assert victim.read_bytes() == original, "publication followed the swapped link"
        assert not list(elsewhere.glob(".real.json.*")), "no temp file outside the tree"

    def test_publication_uses_directory_relative_operations(self):
        """The guarantee above rests on openat; say so if it is unavailable."""
        assert os.open in os.supports_dir_fd


class TestConfigurationRootCannotBeRedirected:
    """INSTALL-018: the confinement root itself is bound by descriptor too.

    `_open_publish_dir`'s directory walk only protected components *below* the
    already-opened root. The root was still reached with a plain, path-named
    `os.open()` -- no `O_NOFOLLOW`, no walk from `/` -- so swapping the
    configuration directory itself for a symlink, right before that call,
    redirected publication exactly as the nested-component race did before
    INSTALL-017.
    """

    def _inject_root_swap(self, cdir, elsewhere, monkeypatch):
        """Land a directory swap deterministically between the two points that
        matter: after the root is resolved to a path, before it is opened.

        `os.path.realpath(cdir)` is called once inside `_publish_target` (via
        `write_settings`/`run`) and once more inside `_open_publish_dir`. The
        swap must land after the *second* call -- the one immediately
        preceding the vulnerable open -- or it only proves the outer
        `_publish_target` check works, which INSTALL-017's fix already covers.
        """
        real_realpath = os.path.realpath
        calls = []

        def spy(path, *args, **kwargs):
            result = real_realpath(path, *args, **kwargs)
            if path == str(cdir):
                calls.append(True)
                if len(calls) == 2:
                    shutil.rmtree(str(cdir))
                    os.symlink(str(elsewhere), str(cdir))
            return result

        monkeypatch.setattr(installer.os.path, "realpath", spy)
        return calls

    def _victim(self, tmp_path):
        cdir = tmp_path / "config"
        cdir.mkdir()
        (cdir / "settings.json").write_text(json.dumps({"theme": "dark"}))
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "settings.json"
        victim.write_text(json.dumps({"registry": "https://example.invalid"}))
        return cdir, elsewhere, victim, victim.read_bytes()

    def test_a_root_swap_before_open_fails_closed(self, tmp_path, monkeypatch):
        cdir, elsewhere, victim, original = self._victim(tmp_path)
        calls = self._inject_root_swap(cdir, elsewhere, monkeypatch)

        with pytest.raises(SystemExit):
            installer._write_json_atomic(
                str(cdir / "settings.json"), {"ours": True}, str(cdir))

        assert len(calls) >= 2, "the injected swap never ran; the test proves nothing"
        assert victim.read_bytes() == original, "publication followed the swapped root"

    def test_the_replaced_root_open_is_exploitable_on_its_own(self, tmp_path, monkeypatch):
        """Restore the exact pre-fix root-open -- a bare, path-named `os.open`
        with no walk from `/` and no `O_NOFOLLOW` -- and confirm the same
        injected swap succeeds against it. This is the mutation this
        regression exists to kill: revert `_bind_directory` to this shape and
        `test_a_root_swap_before_open_fails_closed` above starts failing.
        """
        cdir, elsewhere, victim, original = self._victim(tmp_path)

        def unsafe_bind_directory(root):
            return os.open(root, os.O_RDONLY | os.O_DIRECTORY)

        monkeypatch.setattr(installer, "_bind_directory", unsafe_bind_directory)
        calls = self._inject_root_swap(cdir, elsewhere, monkeypatch)

        try:
            installer._write_json_atomic(
                str(cdir / "settings.json"), {"ours": True}, str(cdir))
            outcome = "WRITE_COMPLETED"
        except SystemExit:
            outcome = "REFUSED"

        assert len(calls) >= 2, "the injected swap never ran; the test proves nothing"
        assert outcome == "WRITE_COMPLETED", (
            "expected the pre-fix root-open to be exploitable; if it refused, "
            "the injected swap is no longer landing in the vulnerable window"
        )
        assert victim.read_bytes() != original, "expected the outside victim to be overwritten"
        assert json.loads(victim.read_text()) == {"ours": True}


class TestSettingsAreNotReadBeforeConfinementIsChecked:
    """Advisory (v0.2.1 review continued at 7f70a3b): `_load_settings` used to
    open and parse `settings.json` by plain pathname before `_publish_target`
    decided whether that path even resolves inside the configuration
    directory, so an out-of-tree symlink target had its content read into
    memory before the refusal that follows ever ran.
    """

    def test_an_out_of_tree_settings_symlink_is_refused_before_it_is_read(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / "other.json"
        victim.write_text(json.dumps({"registry": "https://example.invalid"}))
        (cdir / "settings.json").symlink_to(victim)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))

        real_open = open
        reads = []

        def spy_open(path, *args, **kwargs):
            if os.path.realpath(str(path)) == os.path.realpath(str(victim)):
                reads.append(path)
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", spy_open)

        with pytest.raises(SystemExit):
            installer.run()

        assert not reads, "the out-of-tree target was read before confinement was checked"


class TestInstallUninstallAreTransactional:
    """INSTALL-019: the checkout symlink and the settings rewrite are two
    separate mutations with no shared commit point. A failure between them
    used to leave whichever one had already happened, uncorrected.
    """

    def _fresh(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        return cdir

    def test_a_failed_reinstall_restores_the_pre_existing_managed_link(
        self, tmp_path, monkeypatch
    ):
        cdir = self._fresh(tmp_path, monkeypatch)
        assert installer.run() == 0
        link = cdir / "statusline"
        assert link.is_symlink()
        original_target = os.readlink(str(link))
        before = _snapshot(cdir)

        real_symlink = os.symlink
        calls = []

        def flaky_symlink(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise OSError("operation not permitted")
            return real_symlink(*args, **kwargs)

        monkeypatch.setattr(installer.os, "symlink", flaky_symlink)

        with pytest.raises(SystemExit):
            installer.run()

        assert calls, "the injected failure never ran; the test proves nothing"
        assert link.is_symlink(), "the pre-existing managed link was not restored"
        assert os.readlink(str(link)) == original_target
        assert _snapshot(cdir) == before

    def test_a_failed_backup_on_fresh_install_removes_the_new_link(
        self, tmp_path, monkeypatch
    ):
        cdir = self._fresh(tmp_path, monkeypatch)
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"theme": "dark"}))
        original = settings.read_bytes()
        link = cdir / "statusline"
        assert not link.exists() and not link.is_symlink()

        def explode(*_args, **_kwargs):
            raise OSError("no space left on device")

        monkeypatch.setattr(installer.shutil, "copy2", explode)

        with pytest.raises(SystemExit):
            installer.run()

        assert not link.is_symlink(), "a newly created link was left behind"
        assert not os.path.lexists(str(link))
        assert settings.read_bytes() == original
        assert not list(cdir.glob("settings.json.bak.*"))
        assert not list(cdir.glob(".settings.json.*"))

    def test_a_failed_uninstall_backup_restores_the_removed_link(
        self, tmp_path, monkeypatch
    ):
        cdir = self._fresh(tmp_path, monkeypatch)
        assert installer.run() == 0
        link = cdir / "statusline"
        original_target = os.readlink(str(link))
        settings = cdir / "settings.json"
        before = settings.read_bytes()

        def explode(*_args, **_kwargs):
            raise OSError("no space left on device")

        monkeypatch.setattr(installer.shutil, "copy2", explode)

        with pytest.raises(SystemExit):
            installer.run(uninstall=True)

        assert link.is_symlink(), "the managed link was removed and never restored"
        assert os.readlink(str(link)) == original_target
        assert settings.read_bytes() == before

    def test_a_link_guard_that_never_rolls_back_leaves_the_failures_visible(
        self, tmp_path, monkeypatch
    ):
        """Mutation check: a `_LinkGuard.rollback` that does nothing must make
        the scenario above observably fail, so this suite is not merely
        checking that `run()` raises `SystemExit` (which the pre-fix code
        also did) without checking what it left behind.
        """
        cdir = self._fresh(tmp_path, monkeypatch)
        assert installer.run() == 0
        link = cdir / "statusline"
        assert link.is_symlink()

        monkeypatch.setattr(installer._LinkGuard, "rollback", lambda self: None)

        def explode(*_args, **_kwargs):
            raise OSError("no space left on device")

        monkeypatch.setattr(installer.shutil, "copy2", explode)

        with pytest.raises(SystemExit):
            installer.run(uninstall=True)

        assert not link.is_symlink(), (
            "expected the link to stay removed with rollback disabled; if it "
            "is still present, _LinkGuard is not what is restoring it"
        )


class TestTemporaryDescriptorIsClosed:
    """INSTALL-021: a failure between `os.open` and `os.fdopen` taking
    ownership of the descriptor used to leak it -- the temp file's directory
    entry was removed, but the raw file descriptor stayed open for the life of
    the process.
    """

    def test_a_failed_fchmod_closes_the_descriptor_and_removes_the_temp_file(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        settings = cdir / "settings.json"
        settings.write_text(json.dumps({"theme": "dark"}))

        captured = []

        def explode_fchmod(fd, _mode):
            captured.append(fd)
            raise OSError("permission denied")

        monkeypatch.setattr(installer.os, "fchmod", explode_fchmod)

        with pytest.raises(SystemExit):
            installer._write_json_atomic(str(settings), {"ours": True}, str(cdir))

        assert captured, "fchmod was never reached; the test proves nothing"
        with pytest.raises(OSError):
            os.fstat(captured[0])
        assert not list(cdir.glob(".settings.json.*")), "the temp file was not removed"

    def test_an_unclosed_descriptor_is_detectable(self, tmp_path, monkeypatch):
        """Mutation check: confirm the assertion above actually distinguishes a
        leak from a clean close, by leaking a descriptor on purpose.
        """
        cdir = tmp_path / "config"
        cdir.mkdir()
        leaked = os.open(str(cdir), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fstat(leaked)  # still open: proves the assertion style is meaningful
        finally:
            os.close(leaked)
        with pytest.raises(OSError):
            os.fstat(leaked)  # closed: this is what the real regression checks for


class TestHookGroupMetadataSurvivesRemoval:
    """INSTALL-022: ownership covers the managed hook entry, not fields on its
    containing group. Removing the last managed hook from a group that also
    carries a user's `matcher` used to drop the whole group, taking the
    matcher with it.
    """

    def _managed_command(self, cdir):
        exe = installer.console_script()
        if exe:
            return f"{shlex.quote(exe)} hook session-end"
        link = str(cdir / "statusline")
        return f"{shlex.quote(installer.sys.executable)} " \
               f"{shlex.quote(os.path.join(link, 'hooks', 'session_end.py'))}"

    def test_uninstall_preserves_a_matcher_on_an_emptied_group(self, tmp_path, monkeypatch):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        managed = self._managed_command(cdir)
        settings = {
            "hooks": {
                "SessionEnd": [
                    {"matcher": "user-kept-matcher",
                     "hooks": [{"type": "command", "command": managed}]}
                ]
            }
        }
        (cdir / "settings.json").write_text(json.dumps(settings))

        assert installer.run(uninstall=True) == 0

        after = json.loads((cdir / "settings.json").read_text())
        groups = after["hooks"]["SessionEnd"]
        assert groups == [{"matcher": "user-kept-matcher", "hooks": []}]

    def test_a_group_with_no_other_fields_is_still_dropped_when_emptied(
        self, tmp_path, monkeypatch
    ):
        """The existing v0.2.0-migration promise -- a plain managed group
        leaves nothing behind -- must not regress while fixing the above."""
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        managed = self._managed_command(cdir)
        settings = {"hooks": {"SessionEnd": [
            {"hooks": [{"type": "command", "command": managed}]}
        ]}}
        (cdir / "settings.json").write_text(json.dumps(settings))

        assert installer.run(uninstall=True) == 0

        after = json.loads((cdir / "settings.json").read_text())
        assert "SessionEnd" not in after.get("hooks", {})

    def test_reinstall_then_uninstall_round_trips_a_foreign_matcher(
        self, tmp_path, monkeypatch
    ):
        cdir = tmp_path / "config"
        cdir.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cdir))
        settings = {"hooks": {"SessionEnd": [
            {"matcher": "keep-me", "hooks": [{"type": "command", "command": "third-party"}]}
        ]}}
        (cdir / "settings.json").write_text(json.dumps(settings))

        assert installer.run() == 0
        assert installer.run() == 0
        assert installer.run(uninstall=True) == 0

        after = json.loads((cdir / "settings.json").read_text())
        groups = after["hooks"]["SessionEnd"]
        assert {"matcher": "keep-me", "hooks": [{"type": "command", "command": "third-party"}]} \
            in groups
