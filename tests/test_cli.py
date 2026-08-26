"""The `agent-statusline` entry point and the two install shapes."""
import io
import json
import os

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
        assert status_cmd == "python3 ~/.claude/statusline/statusline.py"
        assert hook_cmd("session-end", "session_end").endswith("hooks/session_end.py")
        assert link and link.endswith("statusline")

    def test_an_installed_package_wires_through_the_console_script(self, monkeypatch,
                                                                   tmp_path):
        exe = tmp_path / "agent-statusline"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        monkeypatch.setattr(installer, "checkout_root", lambda: None)
        monkeypatch.setattr(installer, "console_script", lambda: str(exe))
        status_cmd, hook_cmd, link = installer.commands()
        assert status_cmd == f'"{exe}"'
        assert hook_cmd("session-end", "session_end") == f'"{exe}" hook session-end'
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

    def test_install_backs_the_file_up_first(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark"}))
        installer.write_settings(str(tmp_path), dry=False)
        assert list(tmp_path.glob("settings.json.bak.*"))

    def test_uninstall_removes_only_what_it_added(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({"theme": "dark"}))
        installer.write_settings(str(tmp_path), dry=False)
        installer.write_settings(str(tmp_path), dry=False, remove=True)
        out = json.loads(cfg.read_text())
        assert out["theme"] == "dark"
        assert "statusLine" not in out and "hooks" not in out

    def test_reinstalling_does_not_duplicate_hooks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        for _ in range(3):
            installer.write_settings(str(tmp_path), dry=False)
        out = json.loads((tmp_path / "settings.json").read_text())
        total = sum(len(g["hooks"]) for v in out["hooks"].values() for g in v)
        assert total == len(installer.HOOKS) + len(installer.STOPGAP_HOOKS)
