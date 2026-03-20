"""CLI entry point for insight-blueprint."""

import sys
import threading
import webbrowser
from pathlib import Path

import click
from click.core import ParameterSource

from insight_blueprint.server import mcp
from insight_blueprint.storage.project import init_project


def _resolve_project(project: str | None) -> Path:
    """Resolve and validate the project path."""
    project_path = Path(project).resolve() if project else Path.cwd()
    if not project_path.exists():
        raise click.ClickException(
            f"Project path does not exist: {project_path}\n"
            "Please create the directory first or specify a valid path."
        )
    return project_path


def _wire_registry(project_path: Path) -> None:
    """Wire services into the centralized registry."""
    import insight_blueprint._registry as registry
    from insight_blueprint.core.catalog import CatalogService
    from insight_blueprint.core.designs import DesignService
    from insight_blueprint.core.reviews import ReviewService
    from insight_blueprint.core.rules import RulesService

    registry.design_service = DesignService(project_path)

    registry.catalog_service = CatalogService(project_path)
    registry.catalog_service.rebuild_index()

    registry.review_service = ReviewService(project_path, registry.design_service)
    db_path = project_path / ".insight" / "catalog.db"
    registry.rules_service = RulesService(
        project_path, registry.catalog_service, registry.design_service, db_path
    )


def _start_full_mode(project_path: Path, no_browser: bool) -> None:
    """Start full mode: WebUI (daemon thread) + MCP stdio (main thread)."""
    from insight_blueprint.web import start_server

    port = start_server(host="127.0.0.1", port=3000)
    url = f"http://127.0.0.1:{port}"
    print(f"WebUI: {url}", file=sys.stderr)

    if not no_browser:
        threading.Timer(1.5, webbrowser.open, args=[url]).start()

    # Start MCP server (MUST be last -- blocks main thread)
    mcp.run()


def _start_server_mode(host: str, port: int) -> None:
    """Start server mode: WebUI + MCP SSE on the same HTTP port."""
    from insight_blueprint.server import get_mcp_sse_app
    from insight_blueprint.web import mount_mcp_sse, run_server

    mount_mcp_sse(get_mcp_sse_app())
    print(f"MCP SSE: http://{host}:{port}/mcp/sse", file=sys.stderr)
    print(f"WebUI: http://{host}:{port}/", file=sys.stderr)
    run_server(host, port)


def _start_headless_mode(host: str, port: int) -> None:
    """Start headless mode: MCP SSE only (no WebUI)."""
    print(f"MCP SSE: http://{host}:{port}/mcp/sse", file=sys.stderr)
    mcp.run(transport="sse", host=host, port=port)


@click.group(invoke_without_command=True)
@click.version_option(package_name="insight-blueprint")
@click.option(
    "--project",
    default=None,
    help="Path to the analysis project directory (default: current directory)",
)
@click.option(
    "--mode",
    type=click.Choice(["full", "server", "headless"]),
    default="full",
    help="Startup mode: full (stdio MCP + WebUI), server (HTTP MCP + WebUI), headless (HTTP MCP only)",
)
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
    help="Bind address for server/headless mode (default: 0.0.0.0)",
)
@click.option(
    "--port",
    type=int,
    default=4000,
    help="Listen port for server/headless mode (default: 4000)",
)
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Suppress browser auto-open in full mode",
)
@click.option(
    "--headless",
    "headless_flag",
    is_flag=True,
    default=False,
    help="[Deprecated] Use --no-browser instead",
)
@click.pass_context
def main(
    ctx: click.Context,
    project: str | None,
    mode: str,
    host: str,
    port: int,
    no_browser: bool,
    headless_flag: bool,
) -> None:
    """Start the insight-blueprint MCP server for analysis design management."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project

    # If a subcommand was invoked, skip the default server startup
    if ctx.invoked_subcommand is not None:
        return

    # Handle deprecated --headless flag
    if headless_flag:
        click.echo("Warning: --headless is deprecated, use --no-browser", err=True)
        no_browser = True

    project_path = _resolve_project(project)
    init_project(project_path)
    _wire_registry(project_path)

    if mode == "full":
        # Warn if --host/--port explicitly provided in full mode
        if (
            ctx.get_parameter_source("host") == ParameterSource.COMMANDLINE
            or ctx.get_parameter_source("port") == ParameterSource.COMMANDLINE
        ):
            click.echo("Warning: --host/--port are ignored in full mode", err=True)
        _start_full_mode(project_path, no_browser)
    elif mode == "server":
        _start_server_mode(host, port)
    elif mode == "headless":
        _start_headless_mode(host, port)
