"""Tests for catalog Pydantic models (SPEC-2 Task 1.1)."""

from datetime import datetime

import pytest

from insight_blueprint.models.catalog import (
    ColumnSchema,
    DataSource,
    DomainKnowledge,
    DomainKnowledgeEntry,
    KnowledgeCategory,
    KnowledgeImportance,
    SourceType,
)


class TestSourceType:
    def test_source_type_enum_has_csv_api_sql(self) -> None:
        assert SourceType.csv == "csv"
        assert SourceType.api == "api"
        assert SourceType.sql == "sql"
        assert len(SourceType) == 3

    def test_source_type_rejects_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            SourceType("parquet")


class TestColumnSchema:
    def test_column_schema_instantiation_with_required_fields(self) -> None:
        col = ColumnSchema(name="age", type="integer", description="User age")
        assert col.name == "age"
        assert col.type == "integer"
        assert col.description == "User age"

    def test_column_schema_optional_fields_default_to_none(self) -> None:
        col = ColumnSchema(name="age", type="integer", description="User age")
        assert col.nullable is True
        assert col.examples is None
        assert col.range is None
        assert col.unit is None


class TestDataSource:
    def test_data_source_instantiation_with_all_required_fields(self) -> None:
        source = DataSource(
            id="test-src",
            name="Test Source",
            type=SourceType.csv,
            description="A test CSV source",
            connection={"file_path": "data.csv"},
            schema_info={"columns": []},
        )
        assert source.id == "test-src"
        assert source.name == "Test Source"
        assert source.type == SourceType.csv
        assert source.description == "A test CSV source"
        assert source.connection == {"file_path": "data.csv"}
        assert source.schema_info == {"columns": []}
        assert source.tags == []

    def test_data_source_timestamps_default_to_jst(self) -> None:
        source = DataSource(
            id="ts-test",
            name="TS Test",
            type=SourceType.api,
            description="Timestamp test",
            connection={},
            schema_info={"columns": []},
        )
        assert isinstance(source.created_at, datetime)
        assert isinstance(source.updated_at, datetime)
        assert source.created_at.tzinfo is not None
        assert str(source.created_at.tzinfo) == "Asia/Tokyo"

    def test_data_source_model_dump_json_round_trip(self) -> None:
        source = DataSource(
            id="round-trip",
            name="Round Trip",
            type=SourceType.sql,
            description="Round trip test",
            connection={"provider": "bigquery", "project_id": "my-proj"},
            schema_info={
                "columns": [
                    {"name": "col1", "type": "string", "description": "Column 1"}
                ]
            },
            tags=["test", "demo"],
        )
        data = source.model_dump(mode="json")
        restored = DataSource(**data)
        assert restored.id == source.id
        assert restored.type == source.type
        assert restored.tags == source.tags
        assert restored.connection == source.connection


class TestKnowledgeEnums:
    def test_knowledge_category_enum_values(self) -> None:
        assert KnowledgeCategory.methodology == "methodology"
        assert KnowledgeCategory.caution == "caution"
        assert KnowledgeCategory.definition == "definition"
        assert KnowledgeCategory.context == "context"
        assert len(KnowledgeCategory) == 4

    def test_knowledge_importance_enum_values(self) -> None:
        assert KnowledgeImportance.high == "high"
        assert KnowledgeImportance.medium == "medium"
        assert KnowledgeImportance.low == "low"
        assert len(KnowledgeImportance) == 3


class TestDomainKnowledge:
    def test_domain_knowledge_entry_instantiation(self) -> None:
        entry = DomainKnowledgeEntry(
            key="test-entry",
            title="Test Entry",
            content="Some knowledge content",
            category=KnowledgeCategory.caution,
            importance=KnowledgeImportance.high,
        )
        assert entry.key == "test-entry"
        assert entry.category == KnowledgeCategory.caution
        assert entry.importance == KnowledgeImportance.high
        assert entry.source is None
        assert entry.affects_columns == []

    def test_domain_knowledge_container_with_empty_entries(self) -> None:
        dk = DomainKnowledge(source_id="test-source")
        assert dk.source_id == "test-source"
        assert dk.entries == []
