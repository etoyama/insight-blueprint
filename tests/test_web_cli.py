"""Tests for CLI integration with web server (FR-11)."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from insight_blueprint.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_headless_suppresses_browser(runner: CliRunner, tmp_path: str) -> None:
    """--headless flag prevents browser from opening."""
    with (
        patch("insight_blueprint.web.start_server", return_value=4000) as mock_start,
        patch("insight_blueprint.cli.webbrowser"),
        patch("insight_blueprint.cli.threading") as mock_threading,
        patch("insight_blueprint.cli.mcp") as mock_mcp,
    ):
        mock_mcp.run = MagicMock()
        result = runner.invoke(main, ["--project", str(tmp_path), "--headless"])

    assert result.exit_code == 0
    mock_start.assert_called_once()
    # Timer should NOT be created when headless
    mock_threading.Timer.assert_not_called()


def test_cli_default_opens_browser(runner: CliRunner, tmp_path: str) -> None:
    """Default (no --headless) opens browser via Timer."""
    with (
        patch("insight_blueprint.web.start_server", return_value=4000) as mock_start,
        patch("insight_blueprint.cli.threading") as mock_threading,
        patch("insight_blueprint.cli.mcp") as mock_mcp,
    ):
        mock_mcp.run = MagicMock()
        mock_timer = MagicMock()
        mock_threading.Timer.return_value = mock_timer
        result = runner.invoke(main, ["--project", str(tmp_path)])

    assert result.exit_code == 0
    mock_start.assert_called_once()
    mock_threading.Timer.assert_called_once_with(
        1.5, mock_threading.Timer.call_args[0][1], args=["http://127.0.0.1:4000"]
    )
    mock_timer.start.assert_called_once()


def test_cli_outputs_url_to_stderr(runner: CliRunner, tmp_path: str) -> None:
    """WebUI URL is printed to stderr (not stdout)."""
    with (
        patch("insight_blueprint.web.start_server", return_value=5555),
        patch("insight_blueprint.cli.threading"),
        patch("insight_blueprint.cli.mcp") as mock_mcp,
    ):
        mock_mcp.run = MagicMock()
        result = runner.invoke(main, ["--project", str(tmp_path), "--headless"])

    # Click test runner captures stderr in result.output
    assert "WebUI: http://127.0.0.1:5555" in result.output


def test_cli_start_server_uses_localhost(runner: CliRunner, tmp_path: str) -> None:
    """start_server is called with host=127.0.0.1 (not 0.0.0.0)."""
    with (
        patch("insight_blueprint.web.start_server", return_value=3000) as mock_start,
        patch("insight_blueprint.cli.threading"),
        patch("insight_blueprint.cli.mcp") as mock_mcp,
    ):
        mock_mcp.run = MagicMock()
        runner.invoke(main, ["--project", str(tmp_path), "--headless"])

    mock_start.assert_called_once_with(host="127.0.0.1", port=3000)
