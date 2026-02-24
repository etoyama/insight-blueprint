"""Tests for CatalogService (SPEC-2 Task 2.1 + 2.2)."""

from pathlib import Path

import pytest

from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.models.catalog import (
    DataSource,
    DomainKnowledge,
    DomainKnowledgeEntry,
    KnowledgeCategory,
    KnowledgeImportance,
    SourceType,
)
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml


@pytest.fixture
def catalog_service(tmp_project: Path) -> CatalogService:
    return CatalogService(tmp_project)


@pytest.fixture
def sample_source() -> DataSource:
    return DataSource(
        id="test-src",
        name="Test Source",
        type=SourceType.csv,
        description="A test CSV data source",
        connection={"file_path": "data.csv"},
        schema_info={
            "columns": [
                {"name": "year", "type": "integer", "description": "Census year"},
                {
                    "name": "population",
                    "type": "integer",
                    "description": "Total population",
                },
            ]
        },
        tags=["test", "demo"],
    )


class TestAddSource:
    def test_add_source_creates_source_yaml_file(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        source_file = tmp_project / ".insight" / "catalog" / "sources" / "test-src.yaml"
        assert source_file.exists()

    def test_add_source_returns_data_source_model(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        result = catalog_service.add_source(sample_source)
        assert isinstance(result, DataSource)
        assert result.id == "test-src"

    def test_add_source_creates_empty_knowledge_file(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        knowledge_file = (
            tmp_project / ".insight" / "catalog" / "knowledge" / "test-src.yaml"
        )
        assert knowledge_file.exists()
        data = read_yaml(knowledge_file)
        assert data["source_id"] == "test-src"
        assert data["entries"] == []

    def test_add_source_with_schema_columns_persists(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        source_file = tmp_project / ".insight" / "catalog" / "sources" / "test-src.yaml"
        data = read_yaml(source_file)
        assert len(data["schema_info"]["columns"]) == 2
        assert data["schema_info"]["columns"][0]["name"] == "year"

    def test_add_source_duplicate_id_raises_value_error(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        with pytest.raises(ValueError, match="already exists"):
            catalog_service.add_source(sample_source)


class TestGetSource:
    def test_get_source_returns_correct_source(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        result = catalog_service.get_source("test-src")
        assert result is not None
        assert result.id == "test-src"
        assert result.name == "Test Source"
        assert result.type == SourceType.csv

    def test_get_source_returns_none_for_missing_id(
        self, catalog_service: CatalogService
    ) -> None:
        result = catalog_service.get_source("nonexistent")
        assert result is None


class TestListSources:
    def test_list_sources_returns_all(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        second = DataSource(
            id="second-src",
            name="Second Source",
            type=SourceType.api,
            description="Second source",
            connection={"base_url": "https://api.example.com"},
        )
        catalog_service.add_source(second)
        sources = catalog_service.list_sources()
        assert len(sources) == 2
        ids = [s.id for s in sources]
        assert "test-src" in ids
        assert "second-src" in ids


class TestGetSchema:
    def test_get_schema_returns_column_list(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        schema = catalog_service.get_schema("test-src")
        assert schema is not None
        assert len(schema) == 2
        assert schema[0].name == "year"
        assert schema[1].name == "population"

    def test_get_schema_returns_none_for_missing_source(
        self, catalog_service: CatalogService
    ) -> None:
        result = catalog_service.get_schema("nonexistent")
        assert result is None


class TestGetKnowledge:
    def test_get_knowledge_returns_domain_knowledge(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        result = catalog_service.get_knowledge("test-src")
        assert result is not None
        assert isinstance(result, DomainKnowledge)
        assert result.source_id == "test-src"
        assert result.entries == []

    def test_get_knowledge_returns_none_for_missing_source(
        self, catalog_service: CatalogService
    ) -> None:
        result = catalog_service.get_knowledge("nonexistent")
        assert result is None

    def test_get_knowledge_filters_by_category(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        # Write knowledge entries directly for testing
        knowledge_path = (
            tmp_project / ".insight" / "catalog" / "knowledge" / "test-src.yaml"
        )
        dk = DomainKnowledge(
            source_id="test-src",
            entries=[
                DomainKnowledgeEntry(
                    key="caution-1",
                    title="Caution Note",
                    content="Be careful with this data",
                    category=KnowledgeCategory.caution,
                    importance=KnowledgeImportance.high,
                ),
                DomainKnowledgeEntry(
                    key="method-1",
                    title="Methodology",
                    content="Data collection method info",
                    category=KnowledgeCategory.methodology,
                    importance=KnowledgeImportance.medium,
                ),
            ],
        )
        write_yaml(knowledge_path, dk.model_dump(mode="json"))

        result = catalog_service.get_knowledge(
            "test-src", category=KnowledgeCategory.caution
        )
        assert result is not None
        assert len(result.entries) == 1
        assert result.entries[0].key == "caution-1"


class TestUpdateSource:
    def test_update_source_patches_name_field(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        result = catalog_service.update_source("test-src", name="Updated Name")
        assert result is not None
        assert result.name == "Updated Name"
        assert result.id == "test-src"  # Unchanged

    def test_update_source_refreshes_updated_at(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        original_updated = sample_source.updated_at
        result = catalog_service.update_source("test-src", name="New Name")
        assert result is not None
        assert result.updated_at > original_updated

    def test_update_source_leaves_untouched_fields_intact(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        result = catalog_service.update_source("test-src", name="New Name")
        assert result is not None
        assert result.description == sample_source.description
        assert result.type == sample_source.type
        assert result.tags == sample_source.tags

    def test_update_source_returns_none_for_missing_id(
        self, catalog_service: CatalogService
    ) -> None:
        result = catalog_service.update_source("nonexistent", name="X")
        assert result is None

    def test_update_source_persists_to_yaml(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        catalog_service.update_source("test-src", name="Persisted Name")
        # Re-read from YAML
        reloaded = catalog_service.get_source("test-src")
        assert reloaded is not None
        assert reloaded.name == "Persisted Name"


class TestSearch:
    def test_search_returns_matching_results(
        self, catalog_service: CatalogService, sample_source: DataSource
    ) -> None:
        catalog_service.add_source(sample_source)
        catalog_service.rebuild_index()
        results = catalog_service.search("population")
        assert len(results) >= 1

    def test_search_filters_by_source_type(
        self, catalog_service: CatalogService
    ) -> None:
        csv_source = DataSource(
            id="csv-src",
            name="CSV Source",
            type=SourceType.csv,
            description="A CSV data source with population data",
            connection={"file_path": "data.csv"},
        )
        api_source = DataSource(
            id="api-src",
            name="API Source",
            type=SourceType.api,
            description="An API data source with population data",
            connection={"base_url": "https://api.example.com"},
        )
        catalog_service.add_source(csv_source)
        catalog_service.add_source(api_source)
        catalog_service.rebuild_index()
        results = catalog_service.search("population", source_type=SourceType.csv)
        assert all(r["source_id"] == "csv-src" for r in results)

    def test_search_filters_by_tags(self, catalog_service: CatalogService) -> None:
        tagged = DataSource(
            id="tagged-src",
            name="Tagged Source",
            type=SourceType.csv,
            description="A tagged data source for testing search",
            connection={},
            tags=["government", "demographics"],
        )
        untagged = DataSource(
            id="untagged-src",
            name="Untagged Source",
            type=SourceType.csv,
            description="An untagged data source for testing search",
            connection={},
            tags=[],
        )
        catalog_service.add_source(tagged)
        catalog_service.add_source(untagged)
        catalog_service.rebuild_index()
        results = catalog_service.search("testing search", tags=["government"])
        source_ids = [r["source_id"] for r in results]
        assert "tagged-src" in source_ids
        assert "untagged-src" not in source_ids

    def test_search_returns_empty_when_no_fts_db(
        self, catalog_service: CatalogService
    ) -> None:
        # No rebuild_index called, DB might not exist
        results = catalog_service.search("anything")
        assert results == []


class TestRebuildIndex:
    def test_rebuild_index_creates_fts_db(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        catalog_service.add_source(sample_source)
        catalog_service.rebuild_index()
        db_path = tmp_project / ".insight" / ".sqlite" / "catalog_fts.db"
        assert db_path.exists()

    def test_add_source_then_immediate_search(
        self,
        catalog_service: CatalogService,
        sample_source: DataSource,
        tmp_project: Path,
    ) -> None:
        """Verify add_source inserts into FTS5 for immediate searchability."""
        # First build an empty index so the FTS5 table exists
        catalog_service.rebuild_index()
        # Now add a source — should be immediately searchable
        catalog_service.add_source(sample_source)
        results = catalog_service.search("population")
        assert len(results) >= 1
        assert results[0]["source_id"] == "test-src"
