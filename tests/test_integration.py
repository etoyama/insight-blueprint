"""Integration test: full round-trip from init to CRUD."""

from pathlib import Path

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.reviews import ReviewService
from insight_blueprint.core.rules import RulesService
from insight_blueprint.models.catalog import DataSource, SourceType
from insight_blueprint.models.design import DesignStatus
from insight_blueprint.storage.project import init_project


def test_full_round_trip(tmp_path: Path) -> None:
    """Integration test: init -> create -> get -> list."""
    # 1. Init project
    init_project(tmp_path)
    service = DesignService(tmp_path)

    # 2. Create
    design = service.create_design(
        title="Crime Rate Analysis",
        hypothesis_statement="No positive correlation",
        hypothesis_background="Background context",
        theme_id="FP",
    )
    assert design.id == "FP-H01"

    # 3. Verify YAML file exists
    yaml_path = tmp_path / ".insight" / "designs" / "FP-H01_hypothesis.yaml"
    assert yaml_path.exists()

    # 4. Get
    retrieved = service.get_design("FP-H01")
    assert retrieved is not None
    assert retrieved.title == "Crime Rate Analysis"
    assert retrieved.id == "FP-H01"

    # 5. List
    all_designs = service.list_designs()
    assert len(all_designs) == 1
    assert all_designs[0].id == "FP-H01"

    # 6. List with status filter
    in_review = service.list_designs(status=DesignStatus.in_review)
    assert len(in_review) == 1

    analyzing = service.list_designs(status=DesignStatus.analyzing)
    assert len(analyzing) == 0

    # 7. Missing design returns None
    missing = service.get_design("FP-H99")
    assert missing is None


def test_catalog_full_round_trip(tmp_path: Path) -> None:
    """Integration test: init -> add_source -> get -> schema -> search -> knowledge."""
    # 1. Init project
    init_project(tmp_path)
    service = CatalogService(tmp_path)

    # Verify catalog directories exist
    assert (tmp_path / ".insight" / "catalog" / "sources").is_dir()
    assert (tmp_path / ".insight" / "catalog" / "knowledge").is_dir()
    assert (tmp_path / ".insight" / ".sqlite").is_dir()

    # 2. Add a source
    source = DataSource(
        id="estat-pop",
        name="e-Stat Population Census",
        type=SourceType.api,
        description="Japanese population statistics from e-Stat",
        connection={
            "base_url": "https://api.e-stat.go.jp/rest/3.0",
            "provider": "e-stat",
            "table_id": "0003348423",
        },
        schema_info={
            "columns": [
                {
                    "name": "prefecture_code",
                    "type": "string",
                    "description": "Prefecture code",
                },
                {
                    "name": "year",
                    "type": "integer",
                    "description": "Census year",
                },
                {
                    "name": "population",
                    "type": "integer",
                    "description": "Total population",
                },
            ]
        },
        tags=["government", "population"],
    )
    added = service.add_source(source)
    assert added.id == "estat-pop"

    # 3. Get source
    retrieved = service.get_source("estat-pop")
    assert retrieved is not None
    assert retrieved.name == "e-Stat Population Census"
    assert retrieved.type == SourceType.api

    # 4. Get schema
    schema = service.get_schema("estat-pop")
    assert schema is not None
    assert len(schema) == 3
    assert schema[0].name == "prefecture_code"

    # 5. Rebuild index and search
    service.rebuild_index()
    results = service.search("population")
    assert len(results) >= 1
    assert results[0]["source_id"] == "estat-pop"

    # 6. Search with type filter — should return 0 for csv
    csv_results = service.search("population", source_type=SourceType.csv)
    assert len(csv_results) == 0

    # 7. Get knowledge (should be empty entries)
    knowledge = service.get_knowledge("estat-pop")
    assert knowledge is not None
    assert knowledge.source_id == "estat-pop"
    assert knowledge.entries == []

    # 8. Missing source returns None
    assert service.get_source("nonexistent") is None
    assert service.get_schema("nonexistent") is None
    assert service.get_knowledge("nonexistent") is None


def test_design_lifecycle(tmp_path: Path) -> None:
    """Integration test: create(in_review) → revision_requested → in_review → batch(supported) → knowledge."""
    # 1. Init project
    init_project(tmp_path)
    design_service = DesignService(tmp_path)
    review_service = ReviewService(tmp_path, design_service)
    catalog_service = CatalogService(tmp_path)
    db_path = tmp_path / ".insight" / "catalog.db"
    rules_service = RulesService(tmp_path, catalog_service, design_service, db_path)

    # 2. Create design (defaults to in_review)
    design = design_service.create_design(
        title="Population Analysis",
        hypothesis_statement="No correlation between age and income",
        hypothesis_background="Background context",
        theme_id="FP",
    )
    assert design.id == "FP-H01"
    assert design.status == DesignStatus.in_review

    # 3. Transition to revision_requested
    design = review_service.transition_status(design.id, "revision_requested")
    assert design is not None
    assert design.status == DesignStatus.revision_requested

    # 4. Transition back to in_review
    design = review_service.transition_status(design.id, "in_review")
    assert design is not None
    assert design.status == DesignStatus.in_review

    # 5. Save review batch with knowledge content → supported
    batch = review_service.save_review_batch(
        design.id,
        "supported",
        [
            {
                "comment": "table: test_data\ncaution: watch for nulls in age column",
                "target_section": "hypothesis_statement",
                "target_content": "No correlation between age and income",
            },
        ],
    )
    assert batch is not None
    reloaded = design_service.get_design(design.id)
    assert reloaded is not None
    assert reloaded.status == DesignStatus.supported

    # 6. Save review comment for knowledge extraction
    # Reset to in_review first for comment
    design_service.update_design(design.id, status=DesignStatus.in_review)
    comment = review_service.save_review_comment(
        design.id,
        "table: test_data\ncaution: watch for nulls in age column\n"
        "definition: MAU = Monthly Active Users",
        "supported",
    )
    assert comment is not None

    # 7. Extract domain knowledge (preview)
    entries = review_service.extract_domain_knowledge(design.id)
    assert len(entries) >= 2  # at least caution + definition

    # Verify the preview entries are NOT persisted yet.
    # (Note: a finding entry IS auto-persisted via terminal transition.)
    from insight_blueprint.storage.yaml_store import read_yaml

    ek_data = read_yaml(tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml")
    preview_keys = {e.key for e in entries}
    persisted_keys = {e["key"] for e in ek_data.get("entries", [])}
    assert not preview_keys & persisted_keys

    # 8. Save extracted knowledge (persist)
    saved = review_service.save_extracted_knowledge(design.id, entries)
    assert len(saved) >= 2

    # Verify entries ARE persisted now
    ek_data = read_yaml(tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml")
    assert len(ek_data["entries"]) >= 2

    # 9. Get project context
    ctx = rules_service.get_project_context()
    assert ctx["total_knowledge"] >= 2

    # 10. Suggest cautions — should find matches for test_data
    cautions = rules_service.suggest_cautions(["test_data"])
    assert len(cautions) >= 1

    # 11. Suggest cautions — no matches for nonexistent table
    no_cautions = rules_service.suggest_cautions(["nonexistent_table"])
    assert len(no_cautions) == 0


def test_finding_lifecycle_via_transition_status(tmp_path: Path) -> None:
    """T-INT.1: design create → transition_status(supported) → finding extracted → suggest returns it."""
    init_project(tmp_path)
    design_service = DesignService(tmp_path)
    review_service = ReviewService(tmp_path, design_service)
    catalog_service = CatalogService(tmp_path)
    db_path = tmp_path / ".insight" / "catalog.db"
    rules_service = RulesService(tmp_path, catalog_service, design_service, db_path)

    # Create design and set source_ids
    design = design_service.create_design(
        title="Churn rate hypothesis",
        hypothesis_statement="Churn rate varies by season",
        hypothesis_background="Seasonal analysis",
        theme_id="CHURN",
    )
    design_service.update_design(design.id, source_ids=["orders"])

    # Terminal transition → finding auto-extracted
    review_service.transition_status(design.id, "supported")

    # Suggest should return the auto-extracted finding
    result = rules_service.suggest_knowledge_for_design(
        section="hypothesis_statement", theme_id="CHURN"
    )
    findings = result["suggestions"].get("finding", [])
    keys = [f["key"] for f in findings]
    assert "CHURN-H01-finding" in keys
    matched = [f for f in findings if f["key"] == "CHURN-H01-finding"][0]
    assert matched["category"] == "finding"
    assert "SUPPORTED" in matched["title"]


def test_finding_lifecycle_via_save_review_batch(tmp_path: Path) -> None:
    """T-INT.2: design create → save_review_batch(rejected) → finding extracted → suggest returns it."""
    init_project(tmp_path)
    design_service = DesignService(tmp_path)
    review_service = ReviewService(tmp_path, design_service)
    catalog_service = CatalogService(tmp_path)
    db_path = tmp_path / ".insight" / "catalog.db"
    rules_service = RulesService(tmp_path, catalog_service, design_service, db_path)

    design = design_service.create_design(
        title="Revenue hypothesis",
        hypothesis_statement="Revenue correlates with ad spend",
        hypothesis_background="Marketing analysis",
        theme_id="REV",
    )
    design_service.update_design(design.id, source_ids=["ads"])

    # Batch review with terminal status
    review_service.save_review_batch(
        design.id,
        "rejected",
        [
            {
                "comment": "Data insufficient",
                "target_section": "hypothesis_statement",
                "target_content": "Revenue correlates with ad spend",
            }
        ],
    )

    # Suggest should return finding
    result = rules_service.suggest_knowledge_for_design(
        section="hypothesis_statement", theme_id="REV"
    )
    findings = result["suggestions"].get("finding", [])
    keys = [f["key"] for f in findings]
    assert "REV-H01-finding" in keys
    matched = [f for f in findings if f["key"] == "REV-H01-finding"][0]
    assert "REJECTED" in matched["title"]


def test_traceability_e2e(tmp_path: Path) -> None:
    """T-INT.3: suggest → get finding key → create design with referenced_knowledge → get → verify."""
    init_project(tmp_path)
    design_service = DesignService(tmp_path)
    review_service = ReviewService(tmp_path, design_service)
    catalog_service = CatalogService(tmp_path)
    db_path = tmp_path / ".insight" / "catalog.db"
    rules_service = RulesService(tmp_path, catalog_service, design_service, db_path)

    # Step 1: Create first design and transition to terminal
    d1 = design_service.create_design(
        title="Initial hypothesis",
        hypothesis_statement="Initial statement",
        hypothesis_background="Background",
        theme_id="CHURN",
    )
    review_service.transition_status(d1.id, "supported")

    # Step 2: Suggest and get finding key
    result = rules_service.suggest_knowledge_for_design(
        section="hypothesis_statement", theme_id="CHURN"
    )
    findings = result["suggestions"]["finding"]
    finding_key = findings[0]["key"]  # "CHURN-H01-finding"

    # Step 3: Create new design with referenced_knowledge
    d2 = design_service.create_design(
        title="Follow-up hypothesis",
        hypothesis_statement="Follow-up statement",
        hypothesis_background="Based on prior finding",
        theme_id="CHURN",
        referenced_knowledge={"hypothesis_statement": [finding_key]},
    )

    # Step 4: Verify via get
    retrieved = design_service.get_design(d2.id)
    assert retrieved is not None
    assert finding_key in retrieved.referenced_knowledge["hypothesis_statement"]


def test_referenced_knowledge_merge_integration(tmp_path: Path) -> None:
    """T-INT.4: create with referenced_knowledge → update merge → get → verify union."""
    init_project(tmp_path)
    design_service = DesignService(tmp_path)

    # Create with initial refs
    design = design_service.create_design(
        title="Merge test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        referenced_knowledge={"hypothesis_statement": ["K-001"]},
    )

    # Update: add to same section + new section
    updated = design_service.update_design(
        design.id,
        referenced_knowledge={
            "hypothesis_statement": ["K-002"],
            "source_ids": ["K-003"],
        },
    )
    assert updated is not None

    # Get and verify union
    retrieved = design_service.get_design(design.id)
    assert retrieved is not None
    assert retrieved.referenced_knowledge == {
        "hypothesis_statement": ["K-001", "K-002"],
        "source_ids": ["K-003"],
    }
