"""Pydantic data models for analysis designs."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from insight_blueprint.models.common import now_jst


class DesignStatus(StrEnum):
    """Status of an analysis design."""

    in_review = "in_review"
    revision_requested = "revision_requested"
    analyzing = "analyzing"
    supported = "supported"
    rejected = "rejected"
    inconclusive = "inconclusive"


class AnalysisDesign(BaseModel):
    """Analysis design document for hypothesis-driven EDA."""

    id: str
    theme_id: str = "DEFAULT"
    title: str
    hypothesis_statement: str
    hypothesis_background: str
    status: DesignStatus = DesignStatus.in_review
    parent_id: str | None = None
    metrics: dict = Field(default_factory=dict)
    explanatory: list[dict] = Field(default_factory=list)
    chart: list[dict] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    next_action: dict | None = None
    referenced_knowledge: dict[str, list[str]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now_jst)
    updated_at: datetime = Field(default_factory=now_jst)
