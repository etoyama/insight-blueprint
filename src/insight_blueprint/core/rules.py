"""Knowledge aggregation and caution suggestion (SPEC-3)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.models.catalog import (
    DomainKnowledge,
    DomainKnowledgeEntry,
    KnowledgeCategory,
)
from insight_blueprint.storage import sqlite_store
from insight_blueprint.storage.yaml_store import read_yaml

if TYPE_CHECKING:
    from insight_blueprint.core.designs import DesignService

SECTION_KNOWLEDGE_MAP: dict[str, list[KnowledgeCategory]] = {
    "hypothesis_statement": [KnowledgeCategory.finding],
    "hypothesis_background": [KnowledgeCategory.finding, KnowledgeCategory.context],
    "source_ids": [KnowledgeCategory.caution, KnowledgeCategory.definition],
    "metrics": [KnowledgeCategory.methodology],
    "explanatory": [KnowledgeCategory.methodology, KnowledgeCategory.caution],
    "chart": [KnowledgeCategory.methodology],
    "next_action": [KnowledgeCategory.finding],
}


def _merge_unique_by_key(existing: list[dict], additions: list[dict]) -> list[dict]:
    """Merge two lists of dicts, deduplicating by 'key' field."""
    seen = {e["key"] for e in existing}
    result = list(existing)
    for item in additions:
        if item["key"] not in seen:
            result.append(item)
            seen.add(item["key"])
    return result


class RulesService:
    """Service for aggregating domain knowledge and suggesting cautions."""

    def __init__(
        self,
        project_path: Path,
        catalog_service: CatalogService,
        design_service: DesignService | None = None,
        db_path: Path | None = None,
    ) -> None:
        self._project_path = project_path
        self._catalog_service = catalog_service
        self._design_service = design_service
        self._db_path = db_path
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

    def suggest_knowledge_for_design(
        self,
        section: str | None = None,
        theme_id: str | None = None,
        source_ids: list[str] | None = None,
        hypothesis_text: str | None = None,
        parent_id: str | None = None,
    ) -> dict:
        """Suggest knowledge entries relevant to a design section.

        Filters by category via SECTION_KNOWLEDGE_MAP, then applies
        per-category matching strategies (theme_id, source_ids, FTS5, lineage).
        """
        if section is not None and section not in SECTION_KNOWLEDGE_MAP:
            valid = ", ".join(SECTION_KNOWLEDGE_MAP.keys())
            return {"error": f"Unknown section '{section}'. Valid: {valid}"}

        target_categories: list[KnowledgeCategory] = (
            SECTION_KNOWLEDGE_MAP[section]
            if section is not None
            else list(KnowledgeCategory)
        )

        all_entries = self._collect_all_knowledge_entries()
        suggestions: dict[str, list[dict]] = {}
        source_id_set = set(source_ids) if source_ids else set()

        for category in target_categories:
            matched = self._match_by_category(
                category, all_entries, theme_id, source_id_set, hypothesis_text
            )
            if matched:
                suggestions[category.value] = matched

        # Lineage walking for finding category
        if parent_id and KnowledgeCategory.finding in target_categories:
            lineage_findings = self._walk_ancestor_findings(parent_id, all_entries)
            if lineage_findings:
                existing = suggestions.get("finding", [])
                suggestions["finding"] = _merge_unique_by_key(
                    existing, lineage_findings
                )

        total = sum(len(v) for v in suggestions.values())
        return {"section": section, "suggestions": suggestions, "total": total}

    def _match_by_category(
        self,
        category: KnowledgeCategory,
        entries: list[DomainKnowledgeEntry],
        theme_id: str | None,
        source_id_set: set[str],
        hypothesis_text: str | None = None,
    ) -> list[dict]:
        """Apply category-specific matching strategy."""
        if category in (KnowledgeCategory.finding, KnowledgeCategory.context):
            return self._match_by_theme_id(category, entries, theme_id)
        if category in (KnowledgeCategory.caution, KnowledgeCategory.definition):
            return self._match_by_source_ids(category, entries, source_id_set)
        if category == KnowledgeCategory.methodology:
            return self._match_methodology_fts5(entries, hypothesis_text)
        return []

    def _match_by_theme_id(
        self,
        category: KnowledgeCategory,
        entries: list[DomainKnowledgeEntry],
        theme_id: str | None,
    ) -> list[dict]:
        """Match entries by theme_id via design source reference."""
        if not theme_id or self._design_service is None:
            return []
        matched: list[dict] = []
        for entry in entries:
            if entry.category != category:
                continue
            if not entry.source or not entry.source.startswith("design:"):
                continue
            design_id = entry.source[len("design:") :]
            design = self._design_service.get_design(design_id)
            if design is not None and design.theme_id == theme_id:
                d = entry.model_dump(mode="json")
                d["relevance"] = f"theme_id match: {theme_id}"
                matched.append(d)
        return matched

    def _match_methodology_fts5(
        self,
        entries: list[DomainKnowledgeEntry],
        hypothesis_text: str | None,
    ) -> list[dict]:
        """Match methodology entries via FTS5 full-text search."""
        if not hypothesis_text or not self._db_path:
            return []

        # Build title lookup for methodology entries
        methodology_by_title: dict[str, DomainKnowledgeEntry] = {
            e.title: e for e in entries if e.category == KnowledgeCategory.methodology
        }
        if not methodology_by_title:
            return []

        try:
            fts_results = sqlite_store.search_index(self._db_path, hypothesis_text)
        except Exception:
            return []

        matched: list[dict] = []
        for hit in fts_results:
            if hit.get("doc_type") != "knowledge":
                continue
            title = hit.get("title", "")
            entry = methodology_by_title.get(title)
            if entry is None:
                continue
            d = entry.model_dump(mode="json")
            d["relevance"] = "FTS5 match"
            matched.append(d)

        return matched

    _MAX_LINEAGE_DEPTH = 10

    def _walk_ancestor_findings(
        self,
        parent_id: str,
        all_entries: list[DomainKnowledgeEntry],
    ) -> list[dict]:
        """Walk up parent_id chain and collect ancestor findings."""
        if self._design_service is None:
            return []

        # Build a lookup: key -> entry for finding entries
        finding_by_key: dict[str, DomainKnowledgeEntry] = {
            e.key: e for e in all_entries if e.category == KnowledgeCategory.finding
        }

        matched: list[dict] = []
        visited: set[str] = set()
        current_id: str | None = parent_id

        for _ in range(self._MAX_LINEAGE_DEPTH):
            if current_id is None or current_id in visited:
                break
            visited.add(current_id)

            finding_key = f"{current_id}-finding"
            if finding_key in finding_by_key:
                entry = finding_by_key[finding_key]
                d = entry.model_dump(mode="json")
                d["relevance"] = f"ancestor design: {current_id}"
                matched.append(d)

            design = self._design_service.get_design(current_id)
            if design is None:
                break
            current_id = design.parent_id

        return matched

    def _match_by_source_ids(
        self,
        category: KnowledgeCategory,
        entries: list[DomainKnowledgeEntry],
        source_id_set: set[str],
    ) -> list[dict]:
        """Match entries by source_ids intersection with affects_columns."""
        if not source_id_set:
            return []
        matched: list[dict] = []
        for entry in entries:
            if entry.category != category:
                continue
            if not entry.affects_columns:
                continue
            intersection = set(entry.affects_columns) & source_id_set
            if intersection:
                d = entry.model_dump(mode="json")
                d["relevance"] = f"source_id match: {', '.join(sorted(intersection))}"
                matched.append(d)
        return matched

    def _read_extracted_knowledge(self) -> list[DomainKnowledgeEntry]:
        """Read extracted knowledge from rules/extracted_knowledge.yaml."""
        ek_path = self._rules_dir / "extracted_knowledge.yaml"
        data = read_yaml(ek_path)
        if not data or "entries" not in data:
            return []
        dk = DomainKnowledge(**data)
        return list(dk.entries)
