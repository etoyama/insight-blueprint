"""CLI entry point for insight-blueprint."""

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

    # Wire DesignService into server module
    import insight_blueprint.server as server_module
    from insight_blueprint.core.designs import DesignService

    server_module._service = DesignService(project_path)

    # Wire CatalogService into server module
    from insight_blueprint.core.catalog import CatalogService

    catalog_service = CatalogService(project_path)
    server_module._catalog_service = catalog_service

    # Rebuild FTS5 search index from YAML files
    catalog_service.rebuild_index()

    # Start MCP server (MUST be last -- blocks main thread)
    mcp.run()
