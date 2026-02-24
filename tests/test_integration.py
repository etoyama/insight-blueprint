"""Integration test: full round-trip from init to CRUD."""

from pathlib import Path

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.core.designs import DesignService
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
    drafts = service.list_designs(status=DesignStatus.draft)
    assert len(drafts) == 1

    active = service.list_designs(status=DesignStatus.active)
    assert len(active) == 0

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
