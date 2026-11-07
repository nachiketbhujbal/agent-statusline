"""Synthetic configuration previews share formatting without using live evidence."""

import pytest

from agent_statusline import render, statusline
from agent_statusline.cli import main


@pytest.fixture
def isolated_preview(tmp_path, monkeypatch):
    state = tmp_path / "state"
    claude = tmp_path / "claude"
    monkeypatch.setenv("AGENT_STATUSLINE_STATE", str(state))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    def unexpected(*args, **kwargs):
        pytest.fail("preview requested live data")

    for name in ("_find_git", "ledger_update", "rl_log", "transcript_totals"):
        monkeypatch.setattr(statusline, name, unexpected)
    monkeypatch.setattr(statusline.pr, "probe", unexpected)
    monkeypatch.setattr(statusline.session_metrics, "write_snapshot", unexpected)

    yield tmp_path / "agent-statusline/config.toml"
    assert not state.exists() and not claude.exists()


def test_preview_renders_synthetic_rows_in_display_order(isolated_preview, capsys):
    assert main(["config", "preview", "--width", "240"]) == 0
    output = capsys.readouterr().out
    assert "\033" in output and "Synthetic preview" in output
    physical = [render.plain(line) for line in output.splitlines()]
    assert [line.split()[0] for line in physical if not line.startswith(" ")] == statusline.ORDER
    assert all(render.vis(line) <= 240 for line in physical)


@pytest.mark.parametrize("columns", [1, 18, 80])
def test_preview_applies_plain_rows_and_fields(isolated_preview, capsys, columns):
    path = isolated_preview
    path.parent.mkdir()
    path.write_text(
        'schema_version = 1\n[display]\ncolor = "plain"\n[display.rows]\nCOST = "hide"\n'
        '[display.fields]\nPROJECT = ["branch"]\n'
    )
    assert main(["config", "preview", "--width", str(columns)]) == 0
    output = capsys.readouterr().out
    assert output and "\033" not in output
    assert all(render.vis(line) <= columns for line in output.splitlines())
    assert "COST" not in output and "example-project" not in output
    if columns >= 18:
        assert "PROJECT example" in output


@pytest.mark.parametrize("width", ["0", "-1", "wide"])
def test_preview_rejects_invalid_width(isolated_preview, capsys, width):
    with pytest.raises(SystemExit) as error:
        main(["config", "preview", "--width", width])
    assert error.value.code == 2
    assert "--width" in capsys.readouterr().err


def test_preview_is_silent_when_all_rows_are_hidden(isolated_preview, capsys):
    path = isolated_preview
    path.parent.mkdir()
    path.write_text(
        "schema_version = 1\n[display.rows]\n"
        + "".join(f'{row} = "hide"\n' for row in statusline.ORDER)
    )
    assert main(["config", "preview"]) == 0
    assert not capsys.readouterr().out


def test_preview_has_sample_evidence_for_optional_fields(isolated_preview, capsys):
    path = isolated_preview
    path.parent.mkdir()
    path.write_text(
        'schema_version = 1\n[display]\ncolor = "plain"\n'
        '[display.fields]\nMODEL = ["output_style"]\nTOOLS = ["commands"]\n'
        'CACHE = ["relative_cost"]\n'
    )
    assert main(["config", "preview", "--width", "80"]) == 0
    output = capsys.readouterr().out
    assert "MODEL   review" in output
    assert "TOOLS   cmds /compact1" in output
    assert "CACHE   0.06x vs all-uncached (list)" in output
