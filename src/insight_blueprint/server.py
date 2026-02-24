"""FastMCP server with analysis design and catalog tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from insight_blueprint.core.catalog import CatalogService
    from insight_blueprint.core.designs import DesignService

mcp = FastMCP("insight-blueprint")

# Module-level service references, set by cli.py before mcp.run()
_service: DesignService | None = None
_catalog_service: CatalogService | None = None


def get_service() -> DesignService:
    """Get the initialized DesignService.

    Raises:
        RuntimeError: If init_project() has not been called yet.
    """
    if _service is None:
        raise RuntimeError("Service not initialized. Call init_project() first.")
    return _service


def get_catalog_service() -> CatalogService:
    """Get the initialized CatalogService.

    Raises:
        RuntimeError: If init_project() has not been called yet.
    """
    if _catalog_service is None:
        raise RuntimeError("CatalogService not initialized. Call init_project() first.")
    return _catalog_service


@mcp.tool()
async def create_analysis_design(
    title: str,
    hypothesis_statement: str,
    hypothesis_background: str,
    parent_id: str | None = None,
    theme_id: str = "DEFAULT",
    metrics: dict | None = None,
    explanatory: list[dict] | None = None,
    chart: list[dict] | None = None,
    next_action: dict | None = None,
) -> dict:
    """Create a new analysis design document.

    Creates a YAML file in .insight/designs/ with 'draft' status.
    theme_id must match [A-Z][A-Z0-9]* pattern (e.g., 'FP', 'TX', 'DEFAULT').

    Returns: dict with id, title, status, message
    """
    service = get_service()
    try:
        design = service.create_design(
            title=title,
            hypothesis_statement=hypothesis_statement,
            hypothesis_background=hypothesis_background,
            parent_id=parent_id,
            theme_id=theme_id,
            metrics=metrics,
            explanatory=explanatory,
            chart=chart,
            next_action=next_action,
        )
    except ValueError as e:
        return {"error": str(e)}

    return {
        "id": design.id,
        "title": design.title,
        "status": design.status.value,
        "message": f"Analysis design '{design.id}' created successfully.",
    }


@mcp.tool()
async def update_analysis_design(
    design_id: str,
    title: str | None = None,
    hypothesis_statement: str | None = None,
    hypothesis_background: str | None = None,
    status: str | None = None,
    metrics: dict | None = None,
    explanatory: list[dict] | None = None,
    chart: list[dict] | None = None,
    next_action: dict | None = None,
) -> dict:
    """Partially update an existing analysis design.

    Only provided fields are updated. Returns the updated design as a dict,
    or an error dict if design_id not found or status is invalid.
    """
    from insight_blueprint.models.design import DesignStatus

    service = get_service()
    updates: dict = {
        k: v
        for k, v in {
            "title": title,
            "hypothesis_statement": hypothesis_statement,
            "hypothesis_background": hypothesis_background,
            "metrics": metrics,
            "explanatory": explanatory,
            "chart": chart,
            "next_action": next_action,
        }.items()
        if v is not None
    }
    if status is not None:
        try:
            updates["status"] = DesignStatus(status)
        except ValueError:
            return {"error": f"Invalid status '{status}'"}

    design = service.update_design(design_id, **updates)
    if design is None:
        return {"error": f"Design '{design_id}' not found"}
    return design.model_dump(mode="json")


@mcp.tool()
async def get_analysis_design(design_id: str) -> dict:
    """Retrieve an analysis design by ID.

    Returns the full design as a dict, or an error dict if not found.
    """
    service = get_service()
    design = service.get_design(design_id)
    if design is None:
        return {"error": f"Design '{design_id}' not found"}
    return design.model_dump(mode="json")


@mcp.tool()
async def list_analysis_designs(status: str | None = None) -> dict:
    """List all analysis designs, optionally filtered by status.

    Args:
        status: Optional filter (draft|active|supported|rejected|inconclusive)

    Returns: dict with 'designs' list and 'count' integer
    """
    from insight_blueprint.models.design import DesignStatus

    service = get_service()

    status_filter = None
    if status is not None:
        try:
            status_filter = DesignStatus(status)
        except ValueError:
            return {"error": f"Invalid status '{status}'"}

    designs = service.list_designs(status=status_filter)
    return {
        "designs": [d.model_dump(mode="json") for d in designs],
        "count": len(designs),
    }


# ---------------------------------------------------------------------------
# Catalog MCP tools (SPEC-2 Tasks 3.1 + 3.2)
# ---------------------------------------------------------------------------


@mcp.tool()
async def add_catalog_entry(
    source_id: str,
    name: str,
    type: str,
    description: str,
    connection: dict,
    columns: list[dict] | None = None,
    tags: list[str] | None = None,
    primary_key: list[str] | None = None,
    row_count_estimate: int | None = None,
) -> dict:
    """Register a new data source in the catalog."""
    from insight_blueprint.models.catalog import DataSource, SourceType

    service = get_catalog_service()
    try:
        source_type = SourceType(type)
    except ValueError:
        return {"error": f"Invalid source type '{type}'. Valid types: csv, api, sql"}

    schema_info: dict = {"columns": columns or []}
    if primary_key is not None:
        schema_info["primary_key"] = primary_key
    if row_count_estimate is not None:
        schema_info["row_count_estimate"] = row_count_estimate

    try:
        source = DataSource(
            id=source_id,
            name=name,
            type=source_type,
            description=description,
            connection=connection,
            schema_info=schema_info,
            tags=tags or [],
        )
        result = service.add_source(source)
    except ValueError as e:
        return {"error": str(e)}

    return {
        "id": result.id,
        "name": result.name,
        "type": result.type.value,
        "message": f"Source '{result.id}' registered successfully.",
    }


@mcp.tool()
async def update_catalog_entry(
    source_id: str,
    name: str | None = None,
    description: str | None = None,
    connection: dict | None = None,
    columns: list[dict] | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Update an existing data source in the catalog."""
    service = get_catalog_service()
    updates: dict = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if connection is not None:
        updates["connection"] = connection
    if columns is not None:
        # Get current schema_info and update columns
        current = service.get_source(source_id)
        if current is None:
            return {"error": f"Source '{source_id}' not found"}
        schema_info = {**current.schema_info, "columns": columns}
        updates["schema_info"] = schema_info
    if tags is not None:
        updates["tags"] = tags

    result = service.update_source(source_id, **updates)
    if result is None:
        return {"error": f"Source '{source_id}' not found"}
    return result.model_dump(mode="json")


@mcp.tool()
async def get_table_schema(source_id: str) -> dict:
    """Get the column schema for a data source."""
    service = get_catalog_service()
    source = service.get_source(source_id)
    if source is None:
        return {"error": f"Source '{source_id}' not found"}
    schema = service.get_schema(source_id)
    return {
        "source_id": source_id,
        "columns": [col.model_dump() for col in (schema or [])],
        "primary_key": source.schema_info.get("primary_key"),
        "row_count_estimate": source.schema_info.get("row_count_estimate"),
    }


@mcp.tool()
async def search_catalog(
    query: str,
    source_type: str | None = None,
    tags: str | None = None,
) -> dict:
    """Search the data catalog using full-text search."""
    from insight_blueprint.models.catalog import SourceType

    service = get_catalog_service()
    type_filter = None
    if source_type is not None:
        try:
            type_filter = SourceType(source_type)
        except ValueError:
            return {"error": f"Invalid source type '{source_type}'"}

    tags_list = None
    if tags is not None:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    results = service.search(query, source_type=type_filter, tags=tags_list)
    return {"results": results, "count": len(results)}


@mcp.tool()
async def get_domain_knowledge(
    source_id: str,
    category: str | None = None,
) -> dict:
    """Get domain knowledge entries for a data source."""
    from insight_blueprint.models.catalog import KnowledgeCategory

    service = get_catalog_service()
    cat_filter = None
    if category is not None:
        try:
            cat_filter = KnowledgeCategory(category)
        except ValueError:
            return {
                "error": f"Invalid category '{category}'. "
                "Valid: methodology, caution, definition, context"
            }

    dk = service.get_knowledge(source_id, category=cat_filter)
    if dk is None:
        return {"error": f"Source '{source_id}' not found"}
    return {
        "source_id": dk.source_id,
        "entries": [e.model_dump(mode="json") for e in dk.entries],
        "count": len(dk.entries),
    }
