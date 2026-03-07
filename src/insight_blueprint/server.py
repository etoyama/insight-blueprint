"""FastMCP server with analysis design and catalog tools."""

from __future__ import annotations

import re

from fastmcp import FastMCP

from insight_blueprint._registry import (
    get_catalog_service,
    get_design_service,
    get_review_service,
    get_rules_service,
)

_DESIGN_ID_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")

mcp = FastMCP("insight-blueprint")


def _validate_design_id(design_id: str) -> dict | None:
    """Return an error dict if design_id contains invalid characters."""
    if not _DESIGN_ID_PATTERN.fullmatch(design_id):
        return {"error": f"Invalid design_id '{design_id}': must match [a-zA-Z0-9_-]+"}
    return None


def _validate_source_id(source_id: str) -> dict | None:
    """Return an error dict if source_id contains invalid characters."""
    if not _DESIGN_ID_PATTERN.fullmatch(source_id):
        return {"error": f"Invalid source_id '{source_id}': must match [a-zA-Z0-9_-]+"}
    return None


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
    referenced_knowledge: dict | None = None,
) -> dict:
    """Create a new analysis design document.

    Creates a YAML file in .insight/designs/ with 'in_review' status.
    theme_id must match [A-Z][A-Z0-9]* pattern (e.g., 'FP', 'TX', 'DEFAULT').

    Returns: dict with id, title, status, message
    """
    service = get_design_service()
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
            referenced_knowledge=referenced_knowledge,
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
    metrics: dict | None = None,
    explanatory: list[dict] | None = None,
    chart: list[dict] | None = None,
    next_action: dict | None = None,
    referenced_knowledge: dict | None = None,
) -> dict:
    """Partially update an existing analysis design.

    Only provided fields are updated. Returns the updated design as a dict,
    or an error dict if design_id not found.
    Status changes must go through transition_design_status.
    """
    if err := _validate_design_id(design_id):
        return err

    service = get_design_service()
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
            "referenced_knowledge": referenced_knowledge,
        }.items()
        if v is not None
    }

    design = service.update_design(design_id, **updates)
    if design is None:
        return {"error": f"Design '{design_id}' not found"}
    return design.model_dump(mode="json")


@mcp.tool()
async def get_analysis_design(design_id: str) -> dict:
    """Retrieve an analysis design by ID.

    Returns the full design as a dict, or an error dict if not found.
    """
    if err := _validate_design_id(design_id):
        return err
    service = get_design_service()
    design = service.get_design(design_id)
    if design is None:
        return {"error": f"Design '{design_id}' not found"}
    return design.model_dump(mode="json")


@mcp.tool()
async def list_analysis_designs(status: str | None = None) -> dict:
    """List all analysis designs, optionally filtered by status.

    Args:
        status: Optional filter (in_review|revision_requested|analyzing|supported|rejected|inconclusive)

    Returns: dict with 'designs' list and 'count' integer
    """
    from insight_blueprint.models.design import DesignStatus

    service = get_design_service()

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
    if err := _validate_source_id(source_id):
        return err
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
    if err := _validate_source_id(source_id):
        return err
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
    if err := _validate_source_id(source_id):
        return err
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
    if err := _validate_source_id(source_id):
        return err
    from insight_blueprint.models.catalog import KnowledgeCategory

    service = get_catalog_service()
    cat_filter = None
    if category is not None:
        try:
            cat_filter = KnowledgeCategory(category)
        except ValueError:
            return {
                "error": f"Invalid category '{category}'. "
                "Valid: methodology, caution, definition, context, finding"
            }

    dk = service.get_knowledge(source_id, category=cat_filter)
    if dk is None:
        return {"error": f"Source '{source_id}' not found"}
    return {
        "source_id": dk.source_id,
        "entries": [e.model_dump(mode="json") for e in dk.entries],
        "count": len(dk.entries),
    }


# ---------------------------------------------------------------------------
# Review workflow MCP tools (SPEC-3 Task 4.1)
# ---------------------------------------------------------------------------


@mcp.tool()
async def transition_design_status(design_id: str, status: str) -> dict:
    """Transition a design to the given target status.

    Valid transitions depend on the current status:
    - in_review -> revision_requested, analyzing, supported, rejected, inconclusive
    - revision_requested -> in_review
    - analyzing -> in_review
    - supported, rejected, inconclusive -> (terminal, no transitions)

    Returns: dict with design_id, status on success; {error} on failure
    """
    if err := _validate_design_id(design_id):
        return err
    svc = get_review_service()
    try:
        result = svc.transition_status(design_id, status)
    except ValueError as e:
        return {"error": str(e)}
    if result is None:
        return {"error": f"Design '{design_id}' not found"}
    return {
        "design_id": result.id,
        "status": result.status.value,
    }


@mcp.tool()
async def save_review_comment(
    design_id: str,
    comment: str,
    status: str,
    reviewer: str = "analyst",
) -> dict:
    """Save a review comment and transition the design status.

    The design must be in 'in_review' status. Valid post-review statuses:
    revision_requested, analyzing, supported, rejected, inconclusive.

    Returns: dict with comment_id, design_id, status_after, message
    """
    if err := _validate_design_id(design_id):
        return err
    svc = get_review_service()
    try:
        result = svc.save_review_comment(design_id, comment, status, reviewer)
    except ValueError as e:
        return {"error": str(e)}
    if result is None:
        return {"error": f"Design '{design_id}' not found"}
    return {
        "comment_id": result.id,
        "design_id": result.design_id,
        "status_after": result.status_after.value,
        "message": f"Review comment saved. Design status: {result.status_after.value}.",
    }


@mcp.tool()
async def save_review_batch(
    design_id: str,
    status_after: str,
    comments: list[dict],
    reviewer: str = "analyst",
) -> dict:
    """Save a batch of review comments and transition the design status.

    The design must be in 'in_review' status. Each comment can optionally
    include target_section and target_content for inline anchoring.

    Valid status_after values: revision_requested, analyzing, supported, rejected, inconclusive.

    Returns: dict with batch_id and status_after on success; {error} on failure
    """
    if err := _validate_design_id(design_id):
        return err
    svc = get_review_service()
    try:
        result = svc.save_review_batch(design_id, status_after, comments, reviewer)
    except ValueError as e:
        return {"error": str(e)}
    except Exception:
        return {"error": "Failed to save review batch"}
    if result is None:
        return {"error": f"Design '{design_id}' not found"}
    return {
        "batch_id": result.id,
        "status_after": result.status_after.value,
    }


@mcp.tool()
async def extract_domain_knowledge(design_id: str) -> dict:
    """Extract domain knowledge from review comments as preview.

    Returns extracted entries for user review before persistence.
    Call save_extracted_knowledge() to persist confirmed entries.

    Returns: dict with design_id, entries, count, message
    """
    if err := _validate_design_id(design_id):
        return err
    svc = get_review_service()
    try:
        entries = svc.extract_domain_knowledge(design_id)
    except ValueError as e:
        return {"error": str(e)}
    return {
        "design_id": design_id,
        "entries": [e.model_dump(mode="json") for e in entries],
        "count": len(entries),
        "message": f"Extracted {len(entries)} knowledge entries (preview).",
    }


@mcp.tool()
async def save_extracted_knowledge(
    design_id: str,
    entries: list[dict],
) -> dict:
    """Persist user-confirmed knowledge entries to extracted_knowledge.yaml.

    Call extract_domain_knowledge() first to get preview entries,
    then pass confirmed (optionally adjusted) entries here.

    Args:
        design_id: The design ID the entries were extracted from
        entries: List of dicts with keys: key, content, category, affects_columns

    Returns: dict with design_id, saved_entries, count, message
    """
    if err := _validate_design_id(design_id):
        return err
    from insight_blueprint.models.catalog import DomainKnowledgeEntry

    svc = get_review_service()
    try:
        parsed_entries = [DomainKnowledgeEntry(**e) for e in entries]
    except Exception as e:
        return {"error": f"Invalid entry format: {e}"}
    try:
        saved = svc.save_extracted_knowledge(design_id, parsed_entries)
    except ValueError as e:
        return {"error": str(e)}
    return {
        "design_id": design_id,
        "saved_entries": [e.model_dump(mode="json") for e in saved],
        "count": len(saved),
        "message": f"Saved {len(saved)} knowledge entries.",
    }


@mcp.tool()
async def get_project_context() -> dict:
    """Get aggregated project context including all domain knowledge.

    Returns sources, knowledge entries, rules, and counts from
    both catalog and review-extracted knowledge.
    """
    svc = get_rules_service()
    return svc.get_project_context()


@mcp.tool()
async def suggest_cautions(table_names: str) -> dict:
    """Suggest cautions for the given table/source names.

    Searches all domain knowledge entries (catalog and extracted) by
    matching affects_columns against provided table names.

    Args:
        table_names: Comma-separated string of table/source names

    Returns: dict with table_names, cautions, count
    """
    svc = get_rules_service()
    names = [t.strip() for t in table_names.split(",") if t.strip()]
    cautions = svc.suggest_cautions(names)
    return {
        "table_names": names,
        "cautions": cautions,
        "count": len(cautions),
    }


@mcp.tool()
async def suggest_knowledge_for_design(
    section: str | None = None,
    theme_id: str | None = None,
    source_ids: str | None = None,
    hypothesis_text: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """Suggest knowledge entries relevant to a design section.

    Filters by category via SECTION_KNOWLEDGE_MAP, then applies
    per-category matching strategies (theme_id, source_ids, FTS5, lineage).

    Args:
        section: Design section name (e.g., hypothesis_statement, metrics)
        theme_id: Theme ID to match findings/context by
        source_ids: Comma-separated source IDs for caution/definition matching
        hypothesis_text: Text to search via FTS5 for methodology matching
        parent_id: Design ID to walk ancestor chain for finding collection

    Returns: dict with section, suggestions, total
    """
    svc = get_rules_service()
    ids_list = (
        [s.strip() for s in source_ids.split(",") if s.strip()] if source_ids else None
    )
    return svc.suggest_knowledge_for_design(
        section=section,
        theme_id=theme_id,
        source_ids=ids_list,
        hypothesis_text=hypothesis_text,
        parent_id=parent_id,
    )
