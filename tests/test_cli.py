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


# ---------------------------------------------------------------------------
# Task 2.2: TestCliModeDispatch (Unit-01)
# ---------------------------------------------------------------------------


class TestCliModeDispatch:
    """Test --mode dispatch routes to the correct startup function."""

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_default_mode_is_full(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """No --mode flag defaults to full mode."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path)])
        assert result.exit_code == 0
        assert mock_full.called  # type: ignore[union-attr]

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_mode_full_explicit(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """--mode full explicitly routes to _start_full_mode."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--mode", "full"])
        assert result.exit_code == 0
        assert mock_full.called  # type: ignore[union-attr]

    @patch("insight_blueprint.cli._start_server_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_mode_server(
        self,
        mock_init: object,
        mock_wire: object,
        mock_server: object,
        tmp_path: Path,
    ) -> None:
        """--mode server routes to _start_server_mode with host and port."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--mode", "server"])
        assert result.exit_code == 0
        mock_server.assert_called_once_with("0.0.0.0", 4000)  # type: ignore[union-attr]

    @patch("insight_blueprint.cli._start_headless_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_mode_headless(
        self,
        mock_init: object,
        mock_wire: object,
        mock_headless: object,
        tmp_path: Path,
    ) -> None:
        """--mode headless routes to _start_headless_mode with host and port."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--mode", "headless"])
        assert result.exit_code == 0
        mock_headless.assert_called_once_with("0.0.0.0", 4000)  # type: ignore[union-attr]

    def test_mode_invalid_value(self, tmp_path: Path) -> None:
        """--mode invalid produces a Click error."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--mode", "invalid"])
        assert result.exit_code != 0

    @patch("insight_blueprint.cli._start_server_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_host_default(
        self,
        mock_init: object,
        mock_wire: object,
        mock_server: object,
        tmp_path: Path,
    ) -> None:
        """--mode server without --host uses default 0.0.0.0."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--mode", "server"])
        assert result.exit_code == 0
        args = mock_server.call_args[0]  # type: ignore[union-attr]
        assert args[0] == "0.0.0.0"

    @patch("insight_blueprint.cli._start_server_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_port_default(
        self,
        mock_init: object,
        mock_wire: object,
        mock_server: object,
        tmp_path: Path,
    ) -> None:
        """--mode server without --port uses default 4000."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--mode", "server"])
        assert result.exit_code == 0
        args = mock_server.call_args[0]  # type: ignore[union-attr]
        assert args[1] == 4000

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_host_port_ignored_in_full_mode(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """--host/--port in full mode emits warning, still calls _start_full_mode."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--project",
                str(tmp_path),
                "--mode",
                "full",
                "--host",
                "1.2.3.4",
                "--port",
                "9999",
            ],
        )
        assert result.exit_code == 0
        # click.echo(err=True) output captured in result.output by CliRunner
        assert "ignored in full mode" in (result.output + (result.stderr or ""))
        assert mock_full.called  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Task 2.2: TestCliFlags (Unit-02)
# ---------------------------------------------------------------------------


class TestCliFlags:
    """Test --no-browser and --headless flag behavior."""

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_no_browser_suppresses_browser(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """--no-browser passes no_browser=True to _start_full_mode."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--no-browser"])
        assert result.exit_code == 0
        mock_full.assert_called_once()  # type: ignore[union-attr]
        _, kwargs = mock_full.call_args  # type: ignore[union-attr]
        # no_browser is the second positional arg
        args = mock_full.call_args[0]  # type: ignore[union-attr]
        assert args[1] is True  # no_browser=True

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_no_browser_keeps_webui_and_mcp(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """--no-browser still invokes _start_full_mode (WebUI + MCP)."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--no-browser"])
        assert result.exit_code == 0
        assert mock_full.called  # type: ignore[union-attr]

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_headless_flag_deprecation_warning(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """--headless emits deprecation warning."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--headless"])
        assert result.exit_code == 0
        assert "deprecated" in (result.output + (result.stderr or ""))

    @patch("insight_blueprint.cli._start_full_mode")
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_headless_flag_suppresses_browser(
        self,
        mock_init: object,
        mock_wire: object,
        mock_full: object,
        tmp_path: Path,
    ) -> None:
        """--headless passes no_browser=True to _start_full_mode."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path), "--headless"])
        assert result.exit_code == 0
        mock_full.assert_called_once()  # type: ignore[union-attr]
        args = mock_full.call_args[0]  # type: ignore[union-attr]
        assert args[1] is True  # no_browser=True


# ---------------------------------------------------------------------------
# Task 5.1: TestFullModeBackwardCompat (Integ-06)
# ---------------------------------------------------------------------------


class TestFullModeBackwardCompat:
    """Regression tests: full mode preserves pre-refactor behavior."""

    @patch("insight_blueprint.cli.mcp")
    @patch("insight_blueprint.cli.webbrowser")
    @patch("insight_blueprint.web.start_server", return_value=3000)
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_full_mode_calls_start_server_then_mcp_run(
        self,
        mock_init: object,
        mock_wire: object,
        mock_start_server: object,
        mock_webbrowser: object,
        mock_mcp: object,
        tmp_path: Path,
    ) -> None:
        """start_server is called (daemon thread), then mcp.run() blocks."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path)])
        assert result.exit_code == 0
        mock_start_server.assert_called_once()  # type: ignore[union-attr]
        mock_mcp.run.assert_called_once()  # type: ignore[union-attr]

    @patch("insight_blueprint.cli.mcp")
    @patch("insight_blueprint.cli.webbrowser")
    @patch("insight_blueprint.web.start_server", return_value=3000)
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_full_mode_webui_port_3000(
        self,
        mock_init: object,
        mock_wire: object,
        mock_start_server: object,
        mock_webbrowser: object,
        mock_mcp: object,
        tmp_path: Path,
    ) -> None:
        """start_server receives port=3000 (backward compat)."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path)])
        assert result.exit_code == 0
        mock_start_server.assert_called_once_with(  # type: ignore[union-attr]
            host="127.0.0.1", port=3000
        )

    @patch("insight_blueprint.cli.mcp")
    @patch("insight_blueprint.cli.webbrowser")
    @patch("insight_blueprint.web.start_server", return_value=3000)
    @patch("insight_blueprint.cli._wire_registry")
    @patch("insight_blueprint.cli.init_project")
    def test_full_mode_mcp_run_no_transport_arg(
        self,
        mock_init: object,
        mock_wire: object,
        mock_start_server: object,
        mock_webbrowser: object,
        mock_mcp: object,
        tmp_path: Path,
    ) -> None:
        """mcp.run() called with no arguments (stdio default)."""
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_path)])
        assert result.exit_code == 0
        mock_mcp.run.assert_called_once_with()  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Q-M01: Tests for _start_server_mode / _start_headless_mode / run_server
# ---------------------------------------------------------------------------


class TestServerModeStartup:
    """Verify _start_server_mode calls mount_mcp_sse + run_server."""

    @patch("insight_blueprint.web.run_server")
    @patch("insight_blueprint.web.mount_mcp_sse")
    @patch("insight_blueprint.server.get_mcp_sse_app", return_value="<sse_app>")
    def test_server_mode_calls_mount_then_run(
        self,
        mock_get_app: object,
        mock_mount: object,
        mock_run: object,
    ) -> None:
        from insight_blueprint.cli import _start_server_mode

        _start_server_mode("0.0.0.0", 4000)
        mock_mount.assert_called_once_with("<sse_app>")  # type: ignore[union-attr]
        mock_run.assert_called_once_with("0.0.0.0", 4000)  # type: ignore[union-attr]

    @patch("insight_blueprint.web.run_server")
    @patch("insight_blueprint.web.mount_mcp_sse")
    @patch("insight_blueprint.server.get_mcp_sse_app", return_value="<sse_app>")
    def test_server_mode_prints_urls(
        self,
        mock_get_app: object,
        mock_mount: object,
        mock_run: object,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from insight_blueprint.cli import _start_server_mode

        _start_server_mode("0.0.0.0", 4000)
        err = capsys.readouterr().err
        assert "http://0.0.0.0:4000/mcp/sse" in err
        assert "http://0.0.0.0:4000/" in err


class TestHeadlessModeStartup:
    """Verify _start_headless_mode calls mcp.run with SSE transport."""

    @patch("insight_blueprint.cli.mcp")
    def test_headless_mode_calls_mcp_run_sse(self, mock_mcp: object) -> None:
        from insight_blueprint.cli import _start_headless_mode

        _start_headless_mode("0.0.0.0", 4000)
        mock_mcp.run.assert_called_once_with(  # type: ignore[union-attr]
            transport="sse", host="0.0.0.0", port=4000
        )

    @patch("insight_blueprint.cli.mcp")
    def test_headless_mode_prints_sse_url(
        self,
        mock_mcp: object,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from insight_blueprint.cli import _start_headless_mode

        _start_headless_mode("0.0.0.0", 4000)
        err = capsys.readouterr().err
        assert "http://0.0.0.0:4000/mcp/sse" in err
