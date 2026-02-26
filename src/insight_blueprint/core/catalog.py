"""Data catalog CRUD business logic (SPEC-2)."""

import logging
import re
from pathlib import Path

from insight_blueprint.models.catalog import (
    ColumnSchema,
    DataSource,
    DomainKnowledge,
    KnowledgeCategory,
    SourceType,
)
from insight_blueprint.models.common import now_jst
from insight_blueprint.storage.sqlite_store import (
    build_index,
    build_source_content,
    insert_document,
    replace_source_documents,
    search_index,
)
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

logger = logging.getLogger(__name__)

_SAFE_ID_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")


def _validate_id(value: str, name: str = "id") -> None:
    """Raise ValueError if *value* contains characters outside [a-zA-Z0-9_-]."""
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid {name} '{value}': must match [a-zA-Z0-9_-]+")


class CatalogService:
    """Service for managing data catalog entries."""

    def __init__(self, project_path: Path) -> None:
        self._sources_dir = project_path / ".insight" / "catalog" / "sources"
        self._knowledge_dir = project_path / ".insight" / "catalog" / "knowledge"
        self._db_path = project_path / ".insight" / ".sqlite" / "catalog_fts.db"

    def add_source(self, source: DataSource) -> DataSource:
        """Add a new data source to the catalog.

        Creates source YAML, empty knowledge YAML, and inserts into FTS5.
        Raises ValueError if source ID already exists.
        """
        _validate_id(source.id, "source_id")
        source_path = self._sources_dir / f"{source.id}.yaml"
        if source_path.exists():
            raise ValueError(f"Source '{source.id}' already exists")

        # Write source YAML
        self._sources_dir.mkdir(parents=True, exist_ok=True)
        write_yaml(source_path, source.model_dump(mode="json"))

        # Write empty knowledge YAML
        knowledge_path = self._knowledge_dir / f"{source.id}.yaml"
        if not knowledge_path.exists():
            self._knowledge_dir.mkdir(parents=True, exist_ok=True)
            dk = DomainKnowledge(source_id=source.id)
            write_yaml(knowledge_path, dk.model_dump(mode="json"))

        # FTS5 incremental insert (failure must not crash add_source)
        try:
            content = build_source_content(
                {
                    "description": source.description,
                    "columns": source.schema_info.get("columns", []),
                }
            )
            insert_document(self._db_path, "source", source.id, source.name, content)
        except Exception as exc:
            logger.warning("FTS5 insert failed for source '%s': %s", source.id, exc)

        return source

    def get_source(self, source_id: str) -> DataSource | None:
        """Get a source by ID. Returns None if not found."""
        _validate_id(source_id, "source_id")
        source_path = self._sources_dir / f"{source_id}.yaml"
        data = read_yaml(source_path)
        if not data:
            return None
        return DataSource(**data)

    def list_sources(self) -> list[DataSource]:
        """List all data sources, sorted by filename."""
        if not self._sources_dir.exists():
            return []
        files = sorted(self._sources_dir.glob("*.yaml"))
        sources: list[DataSource] = []
        for file_path in files:
            data = read_yaml(file_path)
            if not data:
                continue
            sources.append(DataSource(**data))
        return sources

    def get_schema(self, source_id: str) -> list[ColumnSchema] | None:
        """Get column schema for a source. Returns None if source not found."""
        _validate_id(source_id, "source_id")
        source = self.get_source(source_id)
        if source is None:
            return None
        columns_data = source.schema_info.get("columns", [])
        return [ColumnSchema(**col) for col in columns_data]

    def get_knowledge(
        self,
        source_id: str,
        category: KnowledgeCategory | None = None,
    ) -> DomainKnowledge | None:
        """Get domain knowledge for a source, optionally filtered by category."""
        _validate_id(source_id, "source_id")
        knowledge_path = self._knowledge_dir / f"{source_id}.yaml"
        data = read_yaml(knowledge_path)
        if not data:
            return None
        dk = DomainKnowledge(**data)
        if category is not None:
            dk = DomainKnowledge(
                source_id=dk.source_id,
                entries=[e for e in dk.entries if e.category == category],
            )
        return dk

    def update_source(self, source_id: str, **fields: object) -> DataSource | None:
        """Update a source by ID with the given fields.

        Returns the updated DataSource, or None if source not found.
        """
        _validate_id(source_id, "source_id")
        source = self.get_source(source_id)
        if source is None:
            return None
        updated = source.model_copy(update={**fields, "updated_at": now_jst()})
        file_path = self._sources_dir / f"{source_id}.yaml"
        write_yaml(file_path, updated.model_dump(mode="json"))

        # Atomic FTS5 re-index
        try:
            content = build_source_content(
                {
                    "description": updated.description,
                    "columns": updated.schema_info.get("columns", []),
                }
            )
            rows = [
                {
                    "doc_type": "source",
                    "source_id": source_id,
                    "title": updated.name,
                    "content": content,
                }
            ]
            replace_source_documents(self._db_path, source_id, rows)
        except Exception as exc:
            logger.warning("FTS5 re-index failed for source '%s': %s", source_id, exc)

        return updated

    def search(
        self,
        query: str,
        source_type: SourceType | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Search the FTS5 index with optional post-filtering.

        Args:
            query: Search query string.
            source_type: If set, only return results matching this source type.
            tags: If set, only return results whose source has at least one
                  of the given tags.

        Returns:
            List of result dicts from the FTS5 index.
        """
        results = search_index(self._db_path, query)

        if source_type is None and tags is None:
            return results

        filtered: list[dict] = []
        for result in results:
            source = self.get_source(result["source_id"])
            if source is None:
                # Knowledge-only entry with no source YAML — skip filter
                continue
            if source_type is not None and source.type != source_type:
                continue
            if tags is not None and not any(t in source.tags for t in tags):
                continue
            filtered.append(result)

        return filtered

    def rebuild_index(self) -> None:
        """Rebuild the FTS5 index from all sources and knowledge entries."""
        # Collect source dicts
        source_dicts: list[dict] = []
        for s in self.list_sources():
            source_dicts.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "columns": s.schema_info.get("columns", []),
                }
            )

        # Collect knowledge entry dicts
        knowledge_dicts: list[dict] = []
        if self._knowledge_dir.exists():
            for kf in sorted(self._knowledge_dir.glob("*.yaml")):
                data = read_yaml(kf)
                if not data:
                    continue
                dk = DomainKnowledge(**data)
                for entry in dk.entries:
                    knowledge_dicts.append(
                        {
                            "source_id": dk.source_id,
                            "title": entry.title,
                            "content": entry.content,
                        }
                    )

        build_index(self._db_path, source_dicts, knowledge_dicts)
