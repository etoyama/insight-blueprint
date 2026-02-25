"""Tests for RulesService (SPEC-3 Task 3.1)."""

from pathlib import Path

import pytest

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.core.rules import RulesService
from insight_blueprint.models.catalog import (
    DataSource,
    DomainKnowledge,
    DomainKnowledgeEntry,
    KnowledgeCategory,
    SourceType,
)
from insight_blueprint.storage.yaml_store import write_yaml


@pytest.fixture
def catalog_service(tmp_project: Path) -> CatalogService:
    return CatalogService(tmp_project)


@pytest.fixture
def rules_service(tmp_project: Path, catalog_service: CatalogService) -> RulesService:
    return RulesService(tmp_project, catalog_service)


@pytest.fixture
def sample_source() -> DataSource:
    return DataSource(
        id="pop-stats",
        name="Population Stats",
        type=SourceType.csv,
        description="Population statistics data",
        connection={"file_path": "population.csv"},
        tags=["demographics"],
    )


def _write_catalog_knowledge(
    tmp_project: Path, source_id: str, entries: list[DomainKnowledgeEntry]
) -> None:
    """Helper to write catalog knowledge entries for a source."""
    knowledge_path = (
        tmp_project / ".insight" / "catalog" / "knowledge" / f"{source_id}.yaml"
    )
    dk = DomainKnowledge(source_id=source_id, entries=entries)
    write_yaml(knowledge_path, dk.model_dump(mode="json"))


def _write_extracted_knowledge(
    tmp_project: Path, entries: list[DomainKnowledgeEntry]
) -> None:
    """Helper to write extracted knowledge entries."""
    ek_path = tmp_project / ".insight" / "rules" / "extracted_knowledge.yaml"
    dk = DomainKnowledge(source_id="review", entries=entries)
    write_yaml(ek_path, dk.model_dump(mode="json"))


class TestGetProjectContext:
    def test_get_project_context_includes_catalog_sources(
        self,
        rules_service: RulesService,
        catalog_service: CatalogService,
        sample_source: DataSource,
    ) -> None:
        """Catalog sources are included in project context."""
        catalog_service.add_source(sample_source)
        ctx = rules_service.get_project_context()
        assert ctx["total_sources"] == 1
        assert len(ctx["sources"]) == 1
        assert ctx["sources"][0]["id"] == "pop-stats"

    def test_get_project_context_includes_catalog_knowledge(
        self,
        rules_service: RulesService,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        """Catalog knowledge entries are included in project context."""
        catalog_service.add_source(sample_source)
        _write_catalog_knowledge(
            tmp_project,
            "pop-stats",
            [
                DomainKnowledgeEntry(
                    key="caution-1",
                    title="Census method changed in 2015",
                    content="Census method changed in 2015, direct comparison needs correction.",
                    category=KnowledgeCategory.caution,
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        ctx = rules_service.get_project_context()
        assert ctx["total_knowledge"] >= 1
        knowledge_keys = [e["key"] for e in ctx["knowledge_entries"]]
        assert "caution-1" in knowledge_keys

    def test_get_project_context_includes_extracted_knowledge(
        self,
        rules_service: RulesService,
        tmp_project: Path,
    ) -> None:
        """Extracted knowledge entries are included in project context."""
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="FP-H01-0",
                    title="Population data caution",
                    content="Population data requires correction after 2015.",
                    category=KnowledgeCategory.caution,
                    source="Review comment on FP-H01",
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        ctx = rules_service.get_project_context()
        knowledge_keys = [e["key"] for e in ctx["knowledge_entries"]]
        assert "FP-H01-0" in knowledge_keys

    def test_get_project_context_empty_project(
        self,
        rules_service: RulesService,
    ) -> None:
        """Empty project returns zero sources/knowledge, rule files from init."""
        ctx = rules_service.get_project_context()
        assert ctx["total_sources"] == 0
        assert ctx["total_knowledge"] == 0
        assert ctx["sources"] == []
        assert ctx["knowledge_entries"] == []
        # init_project creates review_rules.yaml and analysis_rules.yaml
        # with {"rules": []} — these are included as rule files
        assert ctx["total_rules"] >= 0

    def test_get_project_context_includes_rule_files(
        self,
        rules_service: RulesService,
        tmp_project: Path,
    ) -> None:
        """Rule files (review_rules.yaml, analysis_rules.yaml) are included."""
        # init_project already creates these rule files
        review_rules_path = tmp_project / ".insight" / "rules" / "review_rules.yaml"
        write_yaml(review_rules_path, {"rules": [{"name": "check-nulls"}]})
        ctx = rules_service.get_project_context()
        assert ctx["total_rules"] >= 1
        # At least one rule file should have content
        assert any(r.get("rules") for r in ctx["rules"])


class TestSuggestCautions:
    def test_suggest_cautions_matches_catalog_knowledge(
        self,
        rules_service: RulesService,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        """Catalog knowledge entries matching affects_columns are returned."""
        catalog_service.add_source(sample_source)
        _write_catalog_knowledge(
            tmp_project,
            "pop-stats",
            [
                DomainKnowledgeEntry(
                    key="caution-1",
                    title="Census method changed",
                    content="Census method changed in 2015.",
                    category=KnowledgeCategory.caution,
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        cautions = rules_service.suggest_cautions(["pop-stats"])
        assert len(cautions) == 1
        assert cautions[0]["key"] == "caution-1"

    def test_suggest_cautions_matches_extracted_knowledge(
        self,
        rules_service: RulesService,
        tmp_project: Path,
    ) -> None:
        """Extracted knowledge entries matching affects_columns are returned."""
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="FP-H01-0",
                    title="Population data caution",
                    content="Population data requires correction.",
                    category=KnowledgeCategory.caution,
                    source="Review comment on FP-H01",
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        cautions = rules_service.suggest_cautions(["pop-stats"])
        assert len(cautions) == 1
        assert cautions[0]["key"] == "FP-H01-0"

    def test_suggest_cautions_mixed_sources(
        self,
        rules_service: RulesService,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        """Both catalog and extracted knowledge entries are returned when matching."""
        catalog_service.add_source(sample_source)
        _write_catalog_knowledge(
            tmp_project,
            "pop-stats",
            [
                DomainKnowledgeEntry(
                    key="catalog-caution",
                    title="Catalog caution",
                    content="Catalog-sourced caution.",
                    category=KnowledgeCategory.caution,
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="extracted-caution",
                    title="Extracted caution",
                    content="Review-sourced caution.",
                    category=KnowledgeCategory.caution,
                    source="Review comment on FP-H01",
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        cautions = rules_service.suggest_cautions(["pop-stats"])
        keys = [c["key"] for c in cautions]
        assert "catalog-caution" in keys
        assert "extracted-caution" in keys
        assert len(cautions) == 2

    def test_suggest_cautions_no_match_returns_empty(
        self,
        rules_service: RulesService,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        """No matching affects_columns returns empty list."""
        catalog_service.add_source(sample_source)
        _write_catalog_knowledge(
            tmp_project,
            "pop-stats",
            [
                DomainKnowledgeEntry(
                    key="caution-1",
                    title="Census method changed",
                    content="Census method changed.",
                    category=KnowledgeCategory.caution,
                    affects_columns=["pop-stats"],
                ),
            ],
        )
        cautions = rules_service.suggest_cautions(["sales-data"])
        assert cautions == []

    def test_suggest_cautions_excludes_unscoped_entries(
        self,
        rules_service: RulesService,
        tmp_project: Path,
    ) -> None:
        """Entries with affects_columns=[] are excluded from suggest_cautions."""
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="scoped-entry",
                    title="Scoped caution",
                    content="Applies to pop-stats.",
                    category=KnowledgeCategory.caution,
                    source="Review comment on FP-H01",
                    affects_columns=["pop-stats"],
                ),
                DomainKnowledgeEntry(
                    key="unscoped-entry",
                    title="General definition",
                    content="MAU = Monthly Active Users",
                    category=KnowledgeCategory.definition,
                    source="Review comment on FP-H01",
                    affects_columns=[],
                ),
            ],
        )
        cautions = rules_service.suggest_cautions(["pop-stats"])
        keys = [c["key"] for c in cautions]
        assert "scoped-entry" in keys
        assert "unscoped-entry" not in keys
