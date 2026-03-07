"""CLI entry point for insight-blueprint."""

import sys
import threading
import webbrowser
from pathlib import Path

import click

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


@click.group(invoke_without_command=True)
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
@click.pass_context
def main(ctx: click.Context, project: str | None, headless: bool) -> None:
    """Start the insight-blueprint MCP server for analysis design management."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project

    # If a subcommand was invoked, skip the default server startup
    if ctx.invoked_subcommand is not None:
        return

    project_path = _resolve_project(project)
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
    db_path = project_path / ".insight" / "catalog.db"
    registry.rules_service = RulesService(
        project_path, registry.catalog_service, registry.design_service, db_path
    )

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


@main.command()
@click.pass_context
def upgrade_templates(ctx: click.Context) -> None:
    """Upgrade bundled skill and rule templates to the latest version."""
    import importlib.resources

    from insight_blueprint.storage.project import (
        _copy_rules_template,
        _copy_skills_template,
        _discover_bundled_rules,
        _discover_bundled_skills,
        _generate_claude_md,
        _get_skill_version_from_traversable,
        _hash_content,
        _hash_skill_directory,
        _load_claude_md_state,
        _load_skill_state,
        _parse_version_from_content,
    )

    project_path = _resolve_project(ctx.obj.get("project"))
    pkg_files = importlib.resources.files("insight_blueprint")

    # --- Skills ---
    click.echo("=== Skills ===")
    skills_found = False
    for skill_name in _discover_bundled_skills():
        bundled_src = pkg_files / "_skills" / skill_name
        dest = project_path / ".claude" / "skills" / skill_name

        bundled_version = _get_skill_version_from_traversable(bundled_src / "SKILL.md")

        if not dest.exists():
            click.echo(f"  {skill_name}: not installed (will be installed)")
            skills_found = True
            continue

        installed_version = None
        state = _load_skill_state(dest)
        installed_version = state.get("installed_version")
        installed_hash = _hash_skill_directory(dest, exclude_managed=True)
        prev_bundled_hash = state.get("installed_bundled_hash")

        if (
            bundled_version
            and installed_version
            and bundled_version == installed_version
        ):
            click.echo(f"  {skill_name}: up to date (v{installed_version})")
            continue

        customized = prev_bundled_hash and installed_hash != prev_bundled_hash
        status = "customized" if customized else "unmodified"
        click.echo(
            f"  {skill_name}: v{installed_version or '?'} -> v{bundled_version or '?'} ({status})"
        )
        skills_found = True

    # --- Rules ---
    click.echo("\n=== Rules ===")
    rules_found = False
    for rule_name in _discover_bundled_rules():
        dest_file = project_path / ".claude" / "rules" / rule_name
        bundled_file = pkg_files / "_rules" / rule_name
        bundled_content = bundled_file.read_text(encoding="utf-8")
        bundled_version = _parse_version_from_content(bundled_content)

        if not dest_file.exists():
            click.echo(f"  {rule_name}: not installed (will be installed)")
            rules_found = True
            continue

        state = _load_claude_md_state(project_path)
        rules_state = state.get("rules", {})
        file_state = rules_state.get(rule_name, {})
        installed_version = file_state.get("installed_version")

        if (
            bundled_version
            and installed_version
            and bundled_version == installed_version
        ):
            click.echo(f"  {rule_name}: up to date (v{installed_version})")
            continue

        installed_hash = _hash_content(dest_file.read_text(encoding="utf-8"))
        prev_hash = file_state.get("installed_bundled_hash")
        customized = prev_hash and installed_hash != prev_hash
        status = "customized" if customized else "unmodified"
        click.echo(
            f"  {rule_name}: v{installed_version or '?'} -> v{bundled_version or '?'} ({status})"
        )
        rules_found = True

    # --- CLAUDE.md ---
    click.echo("\n=== CLAUDE.md ===")
    claude_md_path = project_path / "CLAUDE.md"
    if claude_md_path.exists():
        click.echo("  CLAUDE.md: exists (managed section will be updated)")
    else:
        click.echo("  CLAUDE.md: absent (will be created)")

    if not skills_found and not rules_found:
        click.echo("\nAll templates are up to date.")
        return

    # Confirm
    if not click.confirm("\nProceed with upgrade?"):
        click.echo("Aborted.")
        return

    # Execute upgrade
    _copy_skills_template(project_path)
    _copy_rules_template(project_path)
    _generate_claude_md(project_path)

    click.echo("Upgrade complete.")
