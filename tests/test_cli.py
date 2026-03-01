"""Tests for CLI entry point."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from insight_blueprint.cli import main


def test_cli_nonexistent_project_exits_with_error() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--project", "/nonexistent/path/xyz"])
    assert result.exit_code != 0
    assert "does not exist" in result.output or "Error" in result.output


def test_cli_default_project_uses_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--project omitted: uses current working directory."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    import insight_blueprint.server as server_module

    with patch.object(server_module.mcp, "run"):
        result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert (tmp_path / ".insight").exists()


def test_cli_upgrade_templates_shows_status(tmp_path: Path) -> None:
    """upgrade-templates subcommand shows template status."""
    from insight_blueprint.storage.project import init_project

    init_project(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--project", str(tmp_path), "upgrade-templates"])
    assert result.exit_code == 0
    assert "Skills" in result.output
    assert "Rules" in result.output
    assert "up to date" in result.output


def test_cli_upgrade_templates_installs_missing(tmp_path: Path) -> None:
    """upgrade-templates installs templates not yet present."""
    # Create minimal project without running full init
    (tmp_path / ".insight").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--project", str(tmp_path), "upgrade-templates"],
        input="y\n",
    )
    assert result.exit_code == 0
    assert "not installed" in result.output
    assert "Upgrade complete" in result.output
    assert (tmp_path / ".claude" / "skills" / "analysis-design" / "SKILL.md").exists()
