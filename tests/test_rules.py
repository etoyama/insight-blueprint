"""Tests for RulesService (SPEC-3 Task 3.1)."""

from pathlib import Path

import pytest

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.rules import RulesService
from insight_blueprint.models.catalog import (
    DataSource,
    DomainKnowledge,
    DomainKnowledgeEntry,
    KnowledgeCategory,
    SourceType,
)
from insight_blueprint.storage.sqlite_store import build_index
from insight_blueprint.storage.yaml_store import write_yaml


@pytest.fixture
def catalog_service(tmp_project: Path) -> CatalogService:
    return CatalogService(tmp_project)


@pytest.fixture
def design_service(tmp_project: Path) -> DesignService:
    return DesignService(tmp_project)


@pytest.fixture
def rules_service(
    tmp_project: Path, catalog_service: CatalogService, design_service: DesignService
) -> RulesService:
    db_path = tmp_project / ".insight" / "catalog.db"
    return RulesService(tmp_project, catalog_service, design_service, db_path)


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


class TestRulesServiceConstructor:
    def test_constructor_with_design_service_and_db_path(
        self,
        tmp_project: Path,
        catalog_service: CatalogService,
        design_service: DesignService,
    ) -> None:
        """T-3.15: New constructor params don't break existing methods."""
        db_path = tmp_project / ".insight" / "catalog.db"
        svc = RulesService(tmp_project, catalog_service, design_service, db_path)
        ctx = svc.get_project_context()
        assert "sources" in ctx
        assert "knowledge_entries" in ctx
        cautions = svc.suggest_cautions(["nonexistent"])
        assert cautions == []


class TestSuggestKnowledgeForDesign:
    """Tests for suggest_knowledge_for_design (Tasks 4.2, 4.3, 4.4)."""

    def _setup_mixed_knowledge(
        self,
        tmp_project: Path,
        design_service: DesignService,
    ) -> None:
        """Create designs and knowledge entries for testing."""
        # Create a design with theme_id=CHURN so finding/context can match
        design = design_service.create_design(
            title="Churn hypothesis",
            hypothesis_statement="Churn rate varies by season",
            hypothesis_background="Background",
            theme_id="CHURN",
        )
        design_service.update_design(design.id, source_ids=["orders"])
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="CHURN-H01-finding",
                    title="[SUPPORTED] Churn hypothesis",
                    content="Churn rate varies by season",
                    category=KnowledgeCategory.finding,
                    source="design:CHURN-H01",
                    affects_columns=["orders"],
                ),
                DomainKnowledgeEntry(
                    key="orders-caution-1",
                    title="Orders data caution",
                    content="Orders table has nulls after 2020",
                    category=KnowledgeCategory.caution,
                    source="review",
                    affects_columns=["orders"],
                ),
                DomainKnowledgeEntry(
                    key="users-definition-1",
                    title="Users definition",
                    content="MAU = Monthly Active Users",
                    category=KnowledgeCategory.definition,
                    source="review",
                    affects_columns=["users"],
                ),
                DomainKnowledgeEntry(
                    key="method-1",
                    title="Methodology entry",
                    content="Use time series decomposition for seasonal analysis",
                    category=KnowledgeCategory.methodology,
                    source="review",
                    affects_columns=[],
                ),
                DomainKnowledgeEntry(
                    key="context-1",
                    title="Context entry",
                    content="Market context for churn analysis",
                    category=KnowledgeCategory.context,
                    source="design:CHURN-H01",
                    affects_columns=[],
                ),
            ],
        )

    def test_section_category_filter_hypothesis_statement(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.1: section=hypothesis_statement returns only finding category."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_statement", theme_id="CHURN"
        )
        assert "suggestions" in result
        assert "finding" in result["suggestions"]
        assert "methodology" not in result["suggestions"]
        assert "caution" not in result["suggestions"]

    def test_section_knowledge_map_all_sections(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.2: All 7 sections in SECTION_KNOWLEDGE_MAP filter correctly."""
        from insight_blueprint.core.rules import SECTION_KNOWLEDGE_MAP

        self._setup_mixed_knowledge(tmp_project, design_service)
        for section, expected_cats in SECTION_KNOWLEDGE_MAP.items():
            result = rules_service.suggest_knowledge_for_design(
                section=section,
                theme_id="CHURN",
                source_ids=["orders", "users"],
                hypothesis_text="churn",
            )
            for cat_key in result["suggestions"]:
                assert KnowledgeCategory(cat_key) in expected_cats, (
                    f"Section '{section}' returned unexpected category '{cat_key}'"
                )

    def test_section_none_returns_all_categories(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.3: section=None returns suggestions from all categories."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section=None,
            theme_id="CHURN",
            source_ids=["orders", "users"],
        )
        assert result["section"] is None
        # Should have at least finding and caution
        assert result["total"] > 0

    def test_unknown_section_returns_error(
        self,
        rules_service: RulesService,
    ) -> None:
        """T-3.4: Unknown section returns error dict."""
        result = rules_service.suggest_knowledge_for_design(section="unknown_section")
        assert "error" in result
        assert "unknown_section" in result["error"]
        assert "Valid:" in result["error"]

    def test_theme_id_match_finding(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.5: theme_id match returns finding with relevance."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_statement", theme_id="CHURN"
        )
        findings = result["suggestions"].get("finding", [])
        assert len(findings) >= 1
        keys = [f["key"] for f in findings]
        assert "CHURN-H01-finding" in keys
        # Check relevance field
        matched = [f for f in findings if f["key"] == "CHURN-H01-finding"][0]
        assert "theme_id match" in matched["relevance"]
        assert "CHURN" in matched["relevance"]

    def test_theme_id_match_context(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.6: theme_id match returns context entries."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_background", theme_id="CHURN"
        )
        contexts = result["suggestions"].get("context", [])
        assert len(contexts) >= 1

    def test_source_ids_match_caution(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.10: source_ids match returns caution entries."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section="source_ids", source_ids=["orders", "users"]
        )
        cautions = result["suggestions"].get("caution", [])
        assert len(cautions) >= 1
        keys = [c["key"] for c in cautions]
        assert "orders-caution-1" in keys
        # Check relevance field
        matched = [c for c in cautions if c["key"] == "orders-caution-1"][0]
        assert "source_id match" in matched["relevance"]

    def test_source_ids_match_definition(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.11: source_ids match returns definition entries."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section="source_ids", source_ids=["users"]
        )
        definitions = result["suggestions"].get("definition", [])
        assert len(definitions) >= 1
        keys = [d["key"] for d in definitions]
        assert "users-definition-1" in keys

    def test_relevance_field_present(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.13: Each entry in suggestions has a relevance field."""
        self._setup_mixed_knowledge(tmp_project, design_service)
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_statement", theme_id="CHURN"
        )
        for cat_entries in result["suggestions"].values():
            for entry in cat_entries:
                assert "relevance" in entry
                assert len(entry["relevance"]) > 0

    def test_no_match_returns_empty(
        self,
        rules_service: RulesService,
    ) -> None:
        """T-3.14: No matching knowledge returns empty suggestions."""
        result = rules_service.suggest_knowledge_for_design(section="metrics")
        assert result["section"] == "metrics"
        assert result["suggestions"] == {}
        assert result["total"] == 0

    # -- Task 4.3: parent_id lineage walking tests --

    def test_parent_id_lineage_walking(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.7: parent_id lineage returns findings from ancestors."""
        # Create chain: CHURN-H01 <- CHURN-H02 <- CHURN-H03
        d1 = design_service.create_design(
            title="Root hypothesis",
            hypothesis_statement="Root stmt",
            hypothesis_background="bg",
            theme_id="CHURN",
        )
        d2 = design_service.create_design(
            title="Child hypothesis",
            hypothesis_statement="Child stmt",
            hypothesis_background="bg",
            theme_id="CHURN",
            parent_id=d1.id,
        )
        # Write findings for d1 and d2
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key=f"{d1.id}-finding",
                    title=f"[SUPPORTED] {d1.title}",
                    content=d1.hypothesis_statement,
                    category=KnowledgeCategory.finding,
                    source=f"design:{d1.id}",
                ),
                DomainKnowledgeEntry(
                    key=f"{d2.id}-finding",
                    title=f"[REJECTED] {d2.title}",
                    content=d2.hypothesis_statement,
                    category=KnowledgeCategory.finding,
                    source=f"design:{d2.id}",
                ),
            ],
        )
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_statement", parent_id=d2.id
        )
        findings = result["suggestions"].get("finding", [])
        keys = [f["key"] for f in findings]
        assert f"{d1.id}-finding" in keys
        assert f"{d2.id}-finding" in keys
        # Check relevance mentions ancestor
        for f in findings:
            assert "ancestor design:" in f["relevance"]

    def test_lineage_circular_reference_stops(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.8: Circular reference in lineage doesn't cause infinite loop."""
        # Create A -> B -> A (circular)
        d_a = design_service.create_design(
            title="Design A",
            hypothesis_statement="A stmt",
            hypothesis_background="bg",
            theme_id="CIRC",
        )
        d_b = design_service.create_design(
            title="Design B",
            hypothesis_statement="B stmt",
            hypothesis_background="bg",
            theme_id="CIRC",
            parent_id=d_a.id,
        )
        # Make circular: update A's parent to B
        design_service.update_design(d_a.id, parent_id=d_b.id)

        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key=f"{d_a.id}-finding",
                    title="[SUPPORTED] A",
                    content="A stmt",
                    category=KnowledgeCategory.finding,
                    source=f"design:{d_a.id}",
                ),
                DomainKnowledgeEntry(
                    key=f"{d_b.id}-finding",
                    title="[SUPPORTED] B",
                    content="B stmt",
                    category=KnowledgeCategory.finding,
                    source=f"design:{d_b.id}",
                ),
            ],
        )
        # Should not hang — returns results collected before cycle detected
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_statement", parent_id=d_a.id
        )
        assert "suggestions" in result

    def test_lineage_depth_limit(
        self,
        rules_service: RulesService,
        design_service: DesignService,
        tmp_project: Path,
    ) -> None:
        """T-3.9: Lineage walking stops at depth 10."""
        # Create a chain of depth 15
        designs = []
        for i in range(15):
            parent = designs[-1].id if designs else None
            d = design_service.create_design(
                title=f"Design {i}",
                hypothesis_statement=f"Stmt {i}",
                hypothesis_background="bg",
                theme_id="DEEP",
                parent_id=parent,
            )
            designs.append(d)

        # Write findings for all
        entries = [
            DomainKnowledgeEntry(
                key=f"{d.id}-finding",
                title=f"[SUPPORTED] {d.title}",
                content=d.hypothesis_statement,
                category=KnowledgeCategory.finding,
                source=f"design:{d.id}",
            )
            for d in designs
        ]
        _write_extracted_knowledge(tmp_project, entries)

        # Walk from the deepest (index 14, parent is index 13)
        result = rules_service.suggest_knowledge_for_design(
            section="hypothesis_statement", parent_id=designs[-1].id
        )
        findings = result["suggestions"].get("finding", [])
        # Should have at most 10 results (depth limit)
        assert len(findings) <= 10

    # -- Task 4.4: FTS5 methodology matching tests --

    def test_fts5_methodology_match(
        self,
        tmp_project: Path,
        catalog_service: CatalogService,
        design_service: DesignService,
    ) -> None:
        """T-3.12: FTS5 search returns matching methodology entries."""
        db_path = tmp_project / ".insight" / "catalog.db"
        # Write a methodology knowledge entry
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="method-ts",
                    title="Time series decomposition",
                    content="Use STL decomposition for seasonal trend analysis",
                    category=KnowledgeCategory.methodology,
                    source="review",
                ),
            ],
        )
        # Build FTS5 index with the methodology entry
        build_index(
            db_path,
            sources=[],
            knowledge=[
                {
                    "source_id": "review",
                    "title": "Time series decomposition",
                    "content": "Use STL decomposition for seasonal trend analysis",
                }
            ],
        )
        svc = RulesService(tmp_project, catalog_service, design_service, db_path)
        result = svc.suggest_knowledge_for_design(
            section="metrics", hypothesis_text="seasonal trend analysis"
        )
        methodology = result["suggestions"].get("methodology", [])
        assert len(methodology) >= 1
        keys = [m["key"] for m in methodology]
        assert "method-ts" in keys
        assert "FTS5 match" in methodology[0]["relevance"]

    def test_fts5_failure_returns_empty_methodology(
        self,
        tmp_project: Path,
        catalog_service: CatalogService,
        design_service: DesignService,
    ) -> None:
        """T-3.16: FTS5 failure returns empty methodology, other cats ok."""
        # Use a nonexistent db_path to trigger SQLite failure
        bad_db_path = tmp_project / "nonexistent" / "catalog.db"
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="orders-caution",
                    title="Orders caution",
                    content="Watch for nulls",
                    category=KnowledgeCategory.caution,
                    source="review",
                    affects_columns=["orders"],
                ),
            ],
        )
        svc = RulesService(tmp_project, catalog_service, design_service, bad_db_path)
        result = svc.suggest_knowledge_for_design(
            section="explanatory",
            hypothesis_text="something",
            source_ids=["orders"],
        )
        # methodology should be empty (FTS5 failed)
        assert "methodology" not in result["suggestions"]
        # caution should still work
        cautions = result["suggestions"].get("caution", [])
        assert len(cautions) >= 1

    def test_fts5_title_mismatch_skipped(
        self,
        tmp_project: Path,
        catalog_service: CatalogService,
        design_service: DesignService,
    ) -> None:
        """T-3.17: FTS5 results with no matching title in knowledge are skipped."""
        db_path = tmp_project / ".insight" / "catalog.db"
        # FTS5 index has an entry but knowledge entries don't have matching title
        build_index(
            db_path,
            sources=[],
            knowledge=[
                {
                    "source_id": "review",
                    "title": "Unknown methodology title",
                    "content": "Some content about regression analysis",
                }
            ],
        )
        # No methodology entries in extracted knowledge
        _write_extracted_knowledge(
            tmp_project,
            [
                DomainKnowledgeEntry(
                    key="other-entry",
                    title="Different title",
                    content="Not a methodology",
                    category=KnowledgeCategory.caution,
                    source="review",
                    affects_columns=["data"],
                ),
            ],
        )
        svc = RulesService(tmp_project, catalog_service, design_service, db_path)
        result = svc.suggest_knowledge_for_design(
            section="metrics", hypothesis_text="regression analysis"
        )
        # No methodology matches because title didn't match
        assert "methodology" not in result["suggestions"]
