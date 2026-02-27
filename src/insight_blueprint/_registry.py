"""Centralized service registry for insight-blueprint.

cli.py wires services once at startup; server.py and web.py both read
through the typed getters defined here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insight_blueprint.core.catalog import CatalogService
    from insight_blueprint.core.designs import DesignService
    from insight_blueprint.core.reviews import ReviewService
    from insight_blueprint.core.rules import RulesService

# Module-level service references (set by cli.py before server startup)
design_service: DesignService | None = None
catalog_service: CatalogService | None = None
review_service: ReviewService | None = None
rules_service: RulesService | None = None


def get_design_service() -> DesignService:
    """Return the wired DesignService or raise RuntimeError."""
    if design_service is None:
        raise RuntimeError("design_service not initialized. Wire via cli.py first.")
    return design_service


def get_catalog_service() -> CatalogService:
    """Return the wired CatalogService or raise RuntimeError."""
    if catalog_service is None:
        raise RuntimeError("catalog_service not initialized. Wire via cli.py first.")
    return catalog_service


def get_review_service() -> ReviewService:
    """Return the wired ReviewService or raise RuntimeError."""
    if review_service is None:
        raise RuntimeError("review_service not initialized. Wire via cli.py first.")
    return review_service


def get_rules_service() -> RulesService:
    """Return the wired RulesService or raise RuntimeError."""
    if rules_service is None:
        raise RuntimeError("rules_service not initialized. Wire via cli.py first.")
    return rules_service
