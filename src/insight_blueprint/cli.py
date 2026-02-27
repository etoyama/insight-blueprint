"""CLI entry point for insight-blueprint."""

import sys
import threading
import webbrowser
from pathlib import Path

import click

from insight_blueprint.server import mcp
from insight_blueprint.storage.project import init_project


@click.command()
@click.option(
    "--project",
    default=None,
    help="Path to the analysis project directory (default: current directory)",
)
@click.option(
    "--headless",
    is_flag=True,
    default=False,
    help="Suppress browser launch (for automation/CI use)",
)
def main(project: str | None, headless: bool) -> None:
    """Start the insight-blueprint MCP server for analysis design management."""
    project_path = Path(project).resolve() if project else Path.cwd()

    if not project_path.exists():
        raise click.ClickException(
            f"Project path does not exist: {project_path}\n"
            "Please create the directory first or specify a valid path."
        )

    init_project(project_path)

    # Wire services into centralized registry
    import insight_blueprint._registry as registry
    from insight_blueprint.core.catalog import CatalogService
    from insight_blueprint.core.designs import DesignService
    from insight_blueprint.core.reviews import ReviewService
    from insight_blueprint.core.rules import RulesService

    registry.design_service = DesignService(project_path)

    registry.catalog_service = CatalogService(project_path)
    registry.catalog_service.rebuild_index()

    registry.review_service = ReviewService(project_path, registry.design_service)
    registry.rules_service = RulesService(project_path, registry.catalog_service)

    # Start HTTP server (daemon thread)
    from insight_blueprint.web import start_server

    port = start_server(host="127.0.0.1", port=3000)
    url = f"http://127.0.0.1:{port}"
    print(f"WebUI: {url}", file=sys.stderr)

    # Browser auto-open (suppressed with --headless)
    if not headless:
        threading.Timer(1.5, webbrowser.open, args=[url]).start()

    # Start MCP server (MUST be last -- blocks main thread)
    mcp.run()
