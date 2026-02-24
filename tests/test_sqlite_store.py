"""Tests for SQLite FTS5 storage layer (SPEC-2 Task 1.2)."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from insight_blueprint.storage.sqlite_store import (
    build_index,
    delete_source_documents,
    insert_document,
    replace_source_documents,
    search_index,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_fts.db"


class TestBuildIndex:
    def test_build_index_creates_db_file(self, db_path: Path) -> None:
        build_index(db_path, [], [])
        assert db_path.exists()

    def test_build_index_with_empty_data_creates_empty_table(
        self, db_path: Path
    ) -> None:
        build_index(db_path, [], [])
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT count(*) FROM catalog_fts")
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_build_index_indexes_source_metadata(self, db_path: Path) -> None:
        sources = [
            {
                "id": "test-src",
                "name": "Test Source",
                "description": "A test data source for population data",
                "columns": [
                    {"name": "year", "description": "Census year"},
                    {"name": "population", "description": "Total population"},
                ],
            }
        ]
        build_index(db_path, sources, [])
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT count(*) FROM catalog_fts WHERE doc_type = 'source'"
        )
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_build_index_indexes_knowledge_entries(self, db_path: Path) -> None:
        knowledge = [
            {
                "source_id": "test-src",
                "title": "Important Note",
                "content": "This data requires special handling for accurate analysis",
            }
        ]
        build_index(db_path, [], knowledge)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT count(*) FROM catalog_fts WHERE doc_type = 'knowledge'"
        )
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_build_index_replaces_old_index_on_rebuild(self, db_path: Path) -> None:
        sources = [
            {
                "id": "s1",
                "name": "Old",
                "description": "Old data",
                "columns": [],
            }
        ]
        build_index(db_path, sources, [])
        # Rebuild with different data
        new_sources = [
            {
                "id": "s2",
                "name": "New",
                "description": "New data",
                "columns": [],
            }
        ]
        build_index(db_path, new_sources, [])
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT count(*) FROM catalog_fts")
        assert cursor.fetchone()[0] == 1  # Only new data
        cursor = conn.execute("SELECT source_id FROM catalog_fts")
        assert cursor.fetchone()[0] == "s2"
        conn.close()

    def test_build_index_handles_fts5_unavailable(self, db_path: Path) -> None:
        """When FTS5 is unavailable, build_index should warn and not crash."""
        with patch("insight_blueprint.storage.sqlite_store.sqlite3") as mock_sqlite3:
            mock_conn = mock_sqlite3.connect.return_value
            mock_conn.execute.side_effect = sqlite3.OperationalError(
                "no such module: fts5"
            )
            # Should not raise
            build_index(db_path, [], [])


class TestSearchIndex:
    def test_search_index_returns_matching_results(self, db_path: Path) -> None:
        sources = [
            {
                "id": "pop-data",
                "name": "Population Data",
                "description": "Japanese population statistics",
                "columns": [],
            },
        ]
        build_index(db_path, sources, [])
        results = search_index(db_path, "population")
        assert len(results) >= 1
        assert results[0]["source_id"] == "pop-data"

    def test_search_index_returns_empty_for_no_match(self, db_path: Path) -> None:
        sources = [
            {
                "id": "pop-data",
                "name": "Population",
                "description": "population stats",
                "columns": [],
            },
        ]
        build_index(db_path, sources, [])
        results = search_index(db_path, "zzzznonexistent")
        assert results == []

    def test_search_index_returns_ranked_results(self, db_path: Path) -> None:
        sources = [
            {
                "id": "s1",
                "name": "Population Data",
                "description": "Population statistics for Japan",
                "columns": [
                    {
                        "name": "population",
                        "description": "total population count",
                    }
                ],
            },
            {
                "id": "s2",
                "name": "Weather Data",
                "description": "Temperature and rainfall data",
                "columns": [],
            },
        ]
        build_index(db_path, sources, [])
        results = search_index(db_path, "population")
        assert len(results) >= 1
        # s1 should rank higher (more "population" mentions)
        assert results[0]["source_id"] == "s1"

    def test_search_index_includes_snippet(self, db_path: Path) -> None:
        sources = [
            {
                "id": "s1",
                "name": "Test",
                "description": "Contains population census data for analysis",
                "columns": [],
            },
        ]
        build_index(db_path, sources, [])
        results = search_index(db_path, "population")
        assert len(results) >= 1
        assert "snippet" in results[0]

    def test_search_index_handles_missing_db_gracefully(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.db"
        results = search_index(missing, "anything")
        assert results == []


class TestIncrementalOps:
    def test_insert_document_is_immediately_searchable(self, db_path: Path) -> None:
        build_index(db_path, [], [])
        insert_document(
            db_path,
            "source",
            "new-src",
            "New Source",
            "Brand new data source for testing",
        )
        results = search_index(db_path, "Brand new data")
        assert len(results) >= 1
        assert results[0]["source_id"] == "new-src"

    def test_delete_source_documents_removes_all_rows(self, db_path: Path) -> None:
        sources = [
            {
                "id": "to-delete",
                "name": "Delete Me",
                "description": "This will be deleted",
                "columns": [],
            },
            {
                "id": "to-keep",
                "name": "Keep Me",
                "description": "This should remain after deletion",
                "columns": [],
            },
        ]
        build_index(db_path, sources, [])
        delete_source_documents(db_path, "to-delete")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT count(*) FROM catalog_fts WHERE source_id = 'to-delete'"
        )
        assert cursor.fetchone()[0] == 0
        cursor = conn.execute(
            "SELECT count(*) FROM catalog_fts WHERE source_id = 'to-keep'"
        )
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_replace_source_documents_is_atomic(self, db_path: Path) -> None:
        sources = [
            {
                "id": "replace-me",
                "name": "Old Name",
                "description": "Old description",
                "columns": [],
            },
        ]
        build_index(db_path, sources, [])
        new_rows = [
            {
                "doc_type": "source",
                "source_id": "replace-me",
                "title": "New Name",
                "content": "New description updated content",
            },
            {
                "doc_type": "knowledge",
                "source_id": "replace-me",
                "title": "Note",
                "content": "A knowledge entry for this source",
            },
        ]
        replace_source_documents(db_path, "replace-me", new_rows)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT count(*) FROM catalog_fts WHERE source_id = 'replace-me'"
        )
        assert cursor.fetchone()[0] == 2  # replaced with 2 rows
        conn.close()

    def test_incremental_ops_handle_missing_table_gracefully(
        self, tmp_path: Path
    ) -> None:
        """Incremental ops on a DB without FTS5 table should warn, not crash."""
        db_path = tmp_path / "no_table.db"
        # Create an empty DB file (no FTS5 table)
        conn = sqlite3.connect(str(db_path))
        conn.close()
        # These should not raise
        insert_document(db_path, "source", "s1", "T", "C")
        delete_source_documents(db_path, "s1")
        replace_source_documents(db_path, "s1", [])
