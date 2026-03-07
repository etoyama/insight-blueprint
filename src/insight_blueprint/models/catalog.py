"""Pydantic data models for the data catalog (SPEC-2)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from insight_blueprint.models.common import now_jst


class SourceType(StrEnum):
    """Supported data source types."""

    csv = "csv"
    api = "api"
    sql = "sql"


class KnowledgeCategory(StrEnum):
    """Category of domain knowledge entry."""

    methodology = "methodology"
    caution = "caution"
    definition = "definition"
    context = "context"
    finding = "finding"


class KnowledgeImportance(StrEnum):
    """Importance level of domain knowledge entry."""

    high = "high"
    medium = "medium"
    low = "low"


class ColumnSchema(BaseModel):
    """Schema definition for a single column."""

    name: str
    type: str
    description: str
    nullable: bool = True
    examples: list[str] | None = None
    range: dict | None = None
    unit: str | None = None


class DataSource(BaseModel):
    """A registered data source in the catalog."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    type: SourceType
    description: str
    connection: dict
    schema_info: dict = Field(default_factory=lambda: {"columns": []})
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_jst)
    updated_at: datetime = Field(default_factory=now_jst)


class DomainKnowledgeEntry(BaseModel):
    """A single domain knowledge entry for a data source."""

    key: str
    title: str
    content: str
    category: KnowledgeCategory
    importance: KnowledgeImportance = KnowledgeImportance.medium
    created_at: datetime = Field(default_factory=now_jst)
    source: str | None = None
    affects_columns: list[str] = Field(default_factory=list)


class DomainKnowledge(BaseModel):
    """Container for domain knowledge entries of a data source."""

    source_id: str
    entries: list[DomainKnowledgeEntry] = Field(default_factory=list)
