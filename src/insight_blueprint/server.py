"""FastMCP server with 3 analysis design tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from insight_blueprint.core.designs import DesignService

mcp = FastMCP("insight-blueprint")

# Module-level service reference, set by cli.py before mcp.run()
_service: DesignService | None = None


def get_service() -> DesignService:
    """Get the initialized DesignService.

    Raises:
        RuntimeError: If init_project() has not been called yet.
    """
    if _service is None:
        raise RuntimeError("Service not initialized. Call init_project() first.")
    return _service


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
