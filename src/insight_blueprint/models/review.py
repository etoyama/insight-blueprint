"""Pydantic data models for review comments (SPEC-3)."""

from datetime import datetime

from pydantic import BaseModel, Field

from insight_blueprint.models.common import now_jst
from insight_blueprint.models.design import DesignStatus


class ReviewComment(BaseModel):
    """A structured review comment on an analysis design."""

    id: str
    design_id: str
    comment: str
    reviewer: str = "analyst"
    status_after: DesignStatus
    created_at: datetime = Field(default_factory=now_jst)
    extracted_knowledge: list[str] = Field(default_factory=list)
