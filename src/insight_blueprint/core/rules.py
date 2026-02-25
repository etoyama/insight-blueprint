"""Knowledge aggregation and caution suggestion (SPEC-3)."""

from pathlib import Path

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.models.catalog import (
    DomainKnowledge,
    DomainKnowledgeEntry,
)
from insight_blueprint.storage.yaml_store import read_yaml


class RulesService:
    """Service for aggregating domain knowledge and suggesting cautions."""

    def __init__(self, project_path: Path, catalog_service: CatalogService) -> None:
        self._project_path = project_path
        self._catalog_service = catalog_service
        self._rules_dir = project_path / ".insight" / "rules"

    def get_project_context(self) -> dict:
        """Aggregate all domain knowledge into a structured summary.

        Returns a dict with:
        - sources: list of DataSource summaries
        - knowledge_entries: all DomainKnowledgeEntry items (catalog + extracted)
        - rules: raw rule file contents
        - total_sources, total_knowledge, total_rules: counts
        """
        # 1. Catalog sources
        sources = self._catalog_service.list_sources()
        source_summaries = [
            {
                "id": s.id,
                "name": s.name,
                "type": str(s.type),
                "description": s.description,
                "tags": s.tags,
            }
            for s in sources
        ]

        # 2. Catalog knowledge entries (per source)
        knowledge_entries: list[dict] = []
        for source in sources:
            dk = self._catalog_service.get_knowledge(source.id)
            if dk is not None:
                for entry in dk.entries:
                    knowledge_entries.append(entry.model_dump(mode="json"))

        # 3. Extracted knowledge from rules/extracted_knowledge.yaml
        extracted_entries = self._read_extracted_knowledge()
        for entry in extracted_entries:
            knowledge_entries.append(entry.model_dump(mode="json"))

        # 4. Rule files (review_rules.yaml, analysis_rules.yaml, etc.)
        rules: list[dict] = []
        if self._rules_dir.exists():
            for rule_file in sorted(self._rules_dir.glob("*.yaml")):
                if rule_file.name == "extracted_knowledge.yaml":
                    continue
                data = read_yaml(rule_file)
                if data:
                    rules.append(data)

        return {
            "sources": source_summaries,
            "knowledge_entries": knowledge_entries,
            "rules": rules,
            "total_sources": len(source_summaries),
            "total_knowledge": len(knowledge_entries),
            "total_rules": len(rules),
        }

    def suggest_cautions(self, table_names: list[str]) -> list[dict]:
        """Find knowledge entries whose affects_columns match any of table_names.

        Uses unified affects_columns matching for both catalog and extracted
        knowledge. Entries with affects_columns=[] (unscoped) are excluded.
        """
        table_set = set(table_names)
        all_entries = self._collect_all_knowledge_entries()
        matches: list[dict] = []

        for entry in all_entries:
            if not entry.affects_columns:
                continue
            if set(entry.affects_columns) & table_set:
                matches.append(entry.model_dump(mode="json"))

        return matches

    def _collect_all_knowledge_entries(self) -> list[DomainKnowledgeEntry]:
        """Collect all knowledge entries from catalog and extracted sources."""
        entries: list[DomainKnowledgeEntry] = []

        # Catalog knowledge
        for source in self._catalog_service.list_sources():
            dk = self._catalog_service.get_knowledge(source.id)
            if dk is not None:
                entries.extend(dk.entries)

        # Extracted knowledge
        entries.extend(self._read_extracted_knowledge())

        return entries

    def _read_extracted_knowledge(self) -> list[DomainKnowledgeEntry]:
        """Read extracted knowledge from rules/extracted_knowledge.yaml."""
        ek_path = self._rules_dir / "extracted_knowledge.yaml"
        data = read_yaml(ek_path)
        if not data or "entries" not in data:
            return []
        dk = DomainKnowledge(**data)
        return list(dk.entries)
