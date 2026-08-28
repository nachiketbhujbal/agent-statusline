"""The `agent-statusline` entry point and the two install shapes."""

import io
import json
import os
import shlex
import subprocess

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

    def test_selftest_uses_an_isolated_renderer(self, monkeypatch, capsys):
        assert run(["selftest"], monkeypatch) == 0
        assert "all 10 approved rows with private state" in capsys.readouterr().out

    def test_selftest_rejects_options(self, monkeypatch, capsys):
        assert run(["selftest", "--live"], monkeypatch) == 2
        assert "unknown option" in capsys.readouterr().err

    def test_selftest_never_relays_child_output_on_failure(self, monkeypatch, capsys):
        from agent_statusline import selftest

        failed = subprocess.CompletedProcess(
            ["python", "-m", "agent_statusline"],
            1,
            stdout="private rendered payload",
            stderr="private traceback and path",
        )
        monkeypatch.setattr(selftest.subprocess, "run", lambda *args, **kwargs: failed)

        assert run(["selftest"], monkeypatch) == 1
        output = capsys.readouterr()
        assert "isolated renderer exited non-zero" in output.err
        assert "private" not in output.out + output.err

    def test_selftest_isolates_home_as_well_as_runtime_state(self, monkeypatch, capsys):
        from agent_statusline import selftest

        seen = {}

        def succeed(*args, **kwargs):
            seen.update(kwargs["env"])
            os.makedirs(seen["AGENT_STATUSLINE_STATE"], mode=0o700)
            return subprocess.CompletedProcess(
                args[0],
                0,
                stdout="\n".join(selftest.EXPECTED_ROWS),
                stderr="",
            )

        monkeypatch.setattr(selftest.subprocess, "run", succeed)

        assert run(["selftest"], monkeypatch) == 0
        assert seen["HOME"] != os.environ["HOME"]
        assert os.path.dirname(seen["HOME"]) == os.path.dirname(seen["AGENT_STATUSLINE_STATE"])
        assert "selftest ok" in capsys.readouterr().out

    def test_selftest_rejects_non_private_state_and_symlinks(self, tmp_path):
        from agent_statusline import selftest

        state = tmp_path / "state"
        state.mkdir(mode=0o700)
        private_file = state / "private.json"
        private_file.write_text("{}")
        private_file.chmod(0o600)
        assert selftest._private_state(str(state))

        state.chmod(0o755)
        assert not selftest._private_state(str(state))
        state.chmod(0o700)
        private_file.chmod(0o644)
        assert not selftest._private_state(str(state))
        private_file.chmod(0o600)

        link = state / "linked.json"
        link.symlink_to(private_file)
        assert not selftest._private_state(str(state))

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

    def test_an_installed_package_wires_through_the_console_script(self, monkeypatch, tmp_path):
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
        cfg.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionEnd": [{"hooks": [{"type": "command", "command": "keep-end"}]}],
                        "UserPromptSubmit": [
                            {
                                "matcher": "x",
                                "hooks": [{"type": "command", "command": "keep-submit"}],
                            }
                        ],
                        "Stop": [{"hooks": [{"type": "command", "command": "keep-stop"}]}],
                        "PreToolUse": [{"hooks": [{"type": "command", "command": "keep-pre"}]}],
                    }
                }
            )
        )
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
        cfg.write_text(
            json.dumps(
                {
                    "theme": "dark",
                    "hooks": {
                        "SessionEnd": [{"hooks": [{"type": "command", "command": "keep-end"}]}],
                        "Stop": [{"hooks": [{"type": "command", "command": "keep-stop"}]}],
                    },
                }
            )
        )
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
        cfg.write_text(
            json.dumps({"statusLine": {"type": "command", "command": "some-other-statusline"}})
        )
        installer.write_settings(str(tmp_path), dry=False, remove=True)
        assert json.loads(cfg.read_text())["statusLine"]["command"] == "some-other-statusline"

    def test_reinstalling_does_not_duplicate_hooks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        for _ in range(3):
            installer.write_settings(str(tmp_path), dry=False)
        out = json.loads((tmp_path / "settings.json").read_text())
        total = sum(len(g["hooks"]) for v in out["hooks"].values() for g in v)
        assert total == len(installer.HOOKS) + len(installer.STOPGAP_HOOKS)
