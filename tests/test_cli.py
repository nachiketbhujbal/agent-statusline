"""The `agent-statusline` entry point and the two install shapes."""
import io
import json
import os
import shlex
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
        dotfiles = tmp_path / "dotfiles"
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
        dotfiles = tmp_path / "dotfiles"
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
        with pytest.raises(OSError, match="disk full"):
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
        assert installer.managed_status_command(status)
        assert installer.managed_hook_command(hook("session-end", "session_end"))
        assert shlex.split(status)[1].startswith(str(spaced))

    def test_settings_in_a_directory_containing_spaces_are_written(self, tmp_path, monkeypatch):
        spaced = tmp_path / "my claude config"
        spaced.mkdir()
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(spaced))
        installer.write_settings(str(spaced), dry=False)
        out = json.loads((spaced / "settings.json").read_text())
        assert installer.managed_status_command(out["statusLine"]["command"])

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
