"""Tests for server.py MCP tool layer."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

import insight_blueprint._registry as registry
import insight_blueprint.server as server_module
from insight_blueprint.core.catalog import CatalogService
from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.reviews import ReviewService
from insight_blueprint.core.rules import RulesService


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    """Reset registry.design_service before each test."""
    original = registry.design_service
    yield  # type: ignore[misc]
    registry.design_service = original


@pytest.fixture
def initialized_server(tmp_path: Path) -> Path:
    """Set up server with a real DesignService backed by tmp_path."""
    (tmp_path / ".insight" / "designs").mkdir(parents=True)
    registry.design_service = DesignService(tmp_path)
    return tmp_path


def test_create_analysis_design_returns_dict_with_id_and_status(
    initialized_server: Path,
) -> None:
    result = asyncio.run(
        server_module.create_analysis_design(
            title="Test",
            hypothesis_statement="No correlation",
            hypothesis_background="Background",
            theme_id="FP",
        )
    )
    assert result["id"] == "FP-H01"
    assert result["status"] == "in_review"
    assert "message" in result


def test_get_analysis_design_returns_error_dict_for_missing_id(
    initialized_server: Path,
) -> None:
    result = asyncio.run(server_module.get_analysis_design("FP-H99"))
    assert "error" in result
    assert "FP-H99" in result["error"]


def test_list_analysis_designs_returns_count_field(
    initialized_server: Path,
) -> None:
    asyncio.run(
        server_module.create_analysis_design(
            title="T",
            hypothesis_statement="s",
            hypothesis_background="b",
        )
    )
    result = asyncio.run(server_module.list_analysis_designs())
    assert "count" in result
    assert result["count"] == 1
    assert len(result["designs"]) == 1


def test_get_service_raises_when_not_initialized() -> None:
    registry.design_service = None
    with pytest.raises(RuntimeError, match="design_service"):
        registry.get_design_service()


def test_create_analysis_design_returns_error_dict_for_invalid_theme_id(
    initialized_server: Path,
) -> None:
    result = asyncio.run(
        server_module.create_analysis_design(
            title="T",
            hypothesis_statement="s",
            hypothesis_background="b",
            theme_id="fp",
        )
    )
    assert "error" in result
    assert "fp" in result["error"]


def test_create_analysis_design_accepts_enrichment_fields(
    initialized_server: Path,
) -> None:
    chart = [{"type": "scatter", "description": "FP vs crime"}]
    next_action = {"if_supported": "proceed to panel FE"}
    explanatory = [{"name": "foreign_ratio", "data_source": "0000010101"}]
    result = asyncio.run(
        server_module.create_analysis_design(
            title="Enriched Design",
            hypothesis_statement="stmt",
            hypothesis_background="bg",
            chart=chart,
            next_action=next_action,
            explanatory=explanatory,
        )
    )
    assert "id" in result
    assert result["status"] == "in_review"


def test_update_analysis_design_mcp_patches_fields(initialized_server: Path) -> None:
    create_result = asyncio.run(
        server_module.create_analysis_design(
            title="Original",
            hypothesis_statement="stmt",
            hypothesis_background="bg",
        )
    )
    design_id = create_result["id"]

    result = asyncio.run(
        server_module.update_analysis_design(
            design_id=design_id,
            title="Updated",
            next_action={"if_supported": "go"},
        )
    )
    assert result["title"] == "Updated"
    assert result["next_action"] == {"if_supported": "go"}
    assert result["hypothesis_statement"] == "stmt"  # unchanged


def test_update_analysis_design_mcp_returns_error_for_missing_id(
    initialized_server: Path,
) -> None:
    result = asyncio.run(
        server_module.update_analysis_design(design_id="FP-H99", title="Ghost")
    )
    assert "error" in result
    assert "FP-H99" in result["error"]


def test_update_analysis_design_mcp_does_not_accept_status(
    initialized_server: Path,
) -> None:
    """update_analysis_design no longer accepts status parameter."""
    create_result = asyncio.run(
        server_module.create_analysis_design(
            title="T", hypothesis_statement="s", hypothesis_background="b"
        )
    )
    result = asyncio.run(
        server_module.update_analysis_design(
            design_id=create_result["id"], title="Updated"
        )
    )
    assert result["title"] == "Updated"
    assert result["status"] == "in_review"  # status unchanged


# ---------------------------------------------------------------------------
# Catalog MCP tools tests (SPEC-2 Tasks 3.1 + 3.2)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_catalog_service() -> None:
    """Reset registry.catalog_service before each test."""
    original = registry.catalog_service
    yield  # type: ignore[misc]
    registry.catalog_service = original


@pytest.fixture
def initialized_catalog_server(tmp_project: Path) -> Path:
    """Set up server with both DesignService and CatalogService."""
    registry.design_service = DesignService(tmp_project)
    registry.catalog_service = CatalogService(tmp_project)
    # Build empty FTS5 index so search works
    registry.catalog_service.rebuild_index()
    return tmp_project


# -- get_catalog_service guard --


def test_get_catalog_service_raises_when_not_initialized() -> None:
    registry.catalog_service = None
    with pytest.raises(RuntimeError, match="catalog_service"):
        registry.get_catalog_service()


# -- add_catalog_entry (Task 3.1) --


def test_add_catalog_entry_returns_success_dict(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(
        server_module.add_catalog_entry(
            source_id="test-src",
            name="Test Source",
            type="csv",
            description="A test CSV source",
            connection={"file_path": "data.csv"},
            columns=[{"name": "year", "type": "integer", "description": "Year"}],
        )
    )
    assert result["id"] == "test-src"
    assert result["type"] == "csv"
    assert "message" in result


def test_add_catalog_entry_duplicate_returns_error_dict(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="dup-src",
            name="First",
            type="csv",
            description="First source",
            connection={},
        )
    )
    result = asyncio.run(
        server_module.add_catalog_entry(
            source_id="dup-src",
            name="Second",
            type="csv",
            description="Duplicate",
            connection={},
        )
    )
    assert "error" in result
    assert "already exists" in result["error"]


def test_add_catalog_entry_invalid_type_returns_error_dict(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(
        server_module.add_catalog_entry(
            source_id="bad-type",
            name="Bad",
            type="parquet",
            description="Bad type",
            connection={},
        )
    )
    assert "error" in result
    assert "parquet" in result["error"]


# -- update_catalog_entry (Task 3.1) --


def test_update_catalog_entry_patches_fields(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="upd-src",
            name="Original",
            type="csv",
            description="Original desc",
            connection={},
        )
    )
    result = asyncio.run(
        server_module.update_catalog_entry(
            source_id="upd-src",
            name="Updated Name",
        )
    )
    assert result["name"] == "Updated Name"
    assert result["description"] == "Original desc"  # unchanged


def test_update_catalog_entry_missing_returns_error_dict(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(
        server_module.update_catalog_entry(source_id="missing", name="X")
    )
    assert "error" in result
    assert "missing" in result["error"]


# -- get_table_schema (Task 3.1) --


def test_get_table_schema_returns_columns(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="schema-src",
            name="Schema Test",
            type="api",
            description="Schema test source",
            connection={"base_url": "https://api.example.com"},
            columns=[
                {"name": "year", "type": "integer", "description": "Year"},
                {"name": "pop", "type": "integer", "description": "Population"},
            ],
            primary_key=["year"],
            row_count_estimate=1000,
        )
    )
    result = asyncio.run(server_module.get_table_schema("schema-src"))
    assert result["source_id"] == "schema-src"
    assert len(result["columns"]) == 2
    assert result["primary_key"] == ["year"]
    assert result["row_count_estimate"] == 1000


def test_get_table_schema_missing_returns_error_dict(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(server_module.get_table_schema("nonexistent"))
    assert "error" in result


# -- search_catalog (Task 3.2) --


def test_search_catalog_returns_results_dict(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="search-src",
            name="Population Data",
            type="csv",
            description="Japanese population statistics for analysis",
            connection={},
        )
    )
    # Rebuild so FTS5 has the data
    registry.catalog_service.rebuild_index()
    result = asyncio.run(server_module.search_catalog(query="population"))
    assert "results" in result
    assert "count" in result
    assert result["count"] >= 1


def test_search_catalog_empty_returns_zero_count(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(server_module.search_catalog(query="zzzznonexistent"))
    assert result["count"] == 0
    assert result["results"] == []


def test_search_catalog_with_source_type_filter(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="csv-s",
            name="CSV Data",
            type="csv",
            description="CSV data source with population info",
            connection={},
        )
    )
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="api-s",
            name="API Data",
            type="api",
            description="API data source with population info",
            connection={},
        )
    )
    registry.catalog_service.rebuild_index()
    result = asyncio.run(
        server_module.search_catalog(query="population", source_type="csv")
    )
    for r in result["results"]:
        assert r["source_id"] == "csv-s"


# -- get_domain_knowledge (Task 3.2) --


def test_get_domain_knowledge_returns_entries(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="dk-src",
            name="DK Source",
            type="csv",
            description="Source with knowledge",
            connection={},
        )
    )
    result = asyncio.run(server_module.get_domain_knowledge("dk-src"))
    assert result["source_id"] == "dk-src"
    assert "entries" in result
    assert "count" in result


def test_get_domain_knowledge_missing_returns_error_dict(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(server_module.get_domain_knowledge("nonexistent"))
    assert "error" in result


def test_get_domain_knowledge_with_category_filter(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="cat-src",
            name="Cat Source",
            type="csv",
            description="Category test",
            connection={},
        )
    )
    result = asyncio.run(
        server_module.get_domain_knowledge("cat-src", category="caution")
    )
    assert result["source_id"] == "cat-src"
    assert result["count"] == 0  # No knowledge entries yet


def test_get_domain_knowledge_invalid_category_returns_error(
    initialized_catalog_server: Path,
) -> None:
    asyncio.run(
        server_module.add_catalog_entry(
            source_id="inv-src",
            name="Invalid Cat",
            type="csv",
            description="Invalid cat test",
            connection={},
        )
    )
    result = asyncio.run(
        server_module.get_domain_knowledge("inv-src", category="invalid_cat")
    )
    assert "error" in result
    assert "invalid_cat" in result["error"]


# ---------------------------------------------------------------------------
# Review workflow MCP tools tests (SPEC-3 Tasks 4.1)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_review_service() -> None:
    """Reset registry.review_service before each test."""
    original = registry.review_service
    yield  # type: ignore[misc]
    registry.review_service = original


@pytest.fixture(autouse=True)
def _reset_rules_service() -> None:
    """Reset registry.rules_service before each test."""
    original = registry.rules_service
    yield  # type: ignore[misc]
    registry.rules_service = original


@pytest.fixture
def initialized_review_server(tmp_project: Path) -> Path:
    """Set up server with all services for review workflow testing."""
    design_service = DesignService(tmp_project)
    catalog_service = CatalogService(tmp_project)
    catalog_service.rebuild_index()
    registry.design_service = design_service
    registry.catalog_service = catalog_service
    registry.review_service = ReviewService(tmp_project, design_service)
    db_path = tmp_project / ".insight" / "catalog.db"
    registry.rules_service = RulesService(
        tmp_project, catalog_service, design_service, db_path
    )
    return tmp_project


def _create_in_review_design(theme_id: str = "FP") -> str:
    """Helper to create a design (defaults to in_review status)."""
    result = asyncio.run(
        server_module.create_analysis_design(
            title="Test Design",
            hypothesis_statement="Test hypothesis",
            hypothesis_background="Test background",
            theme_id=theme_id,
        )
    )
    return result["id"]


# -- get_review_service / get_rules_service guards --


def test_get_review_service_raises_when_not_initialized() -> None:
    registry.review_service = None
    with pytest.raises(RuntimeError, match="review_service"):
        registry.get_review_service()


def test_get_rules_service_raises_when_not_initialized() -> None:
    registry.rules_service = None
    with pytest.raises(RuntimeError, match="rules_service"):
        registry.get_rules_service()


# -- design_id validation --


def test_invalid_design_id_rejected(initialized_server: Path) -> None:
    result = asyncio.run(server_module.get_analysis_design("../etc/passwd"))
    assert "error" in result
    assert "Invalid design_id" in result["error"]


# -- source_id validation --


@pytest.mark.parametrize(
    "bad_id",
    ["../etc/passwd", "foo/bar", "id with spaces", "", "valid-id\n", "back\\slash"],
)
def test_add_catalog_entry_invalid_source_id(
    initialized_catalog_server: Path,
    bad_id: str,
) -> None:
    result = asyncio.run(
        server_module.add_catalog_entry(
            source_id=bad_id,
            name="x",
            type="csv",
            description="x",
            connection={},
        )
    )
    assert "error" in result
    assert "Invalid source_id" in result["error"]


def test_update_catalog_entry_invalid_source_id(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(
        server_module.update_catalog_entry(
            source_id="foo/bar",
            name="x",
        )
    )
    assert "error" in result
    assert "Invalid source_id" in result["error"]


def test_get_table_schema_invalid_source_id(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(server_module.get_table_schema("id with spaces"))
    assert "error" in result
    assert "Invalid source_id" in result["error"]


def test_get_domain_knowledge_invalid_source_id(
    initialized_catalog_server: Path,
) -> None:
    result = asyncio.run(server_module.get_domain_knowledge("../etc/passwd"))
    assert "error" in result
    assert "Invalid source_id" in result["error"]


# -- transition_design_status tool --


def test_transition_design_status_success(initialized_review_server: Path) -> None:
    design_id = _create_in_review_design()
    result = asyncio.run(
        server_module.transition_design_status(design_id, "revision_requested")
    )
    assert result["design_id"] == design_id
    assert result["status"] == "revision_requested"


def test_transition_design_status_invalid(
    initialized_review_server: Path,
) -> None:
    design_id = _create_in_review_design()
    # Move to terminal state via valid transition
    asyncio.run(server_module.transition_design_status(design_id, "supported"))
    result = asyncio.run(server_module.transition_design_status(design_id, "in_review"))
    assert "error" in result
    assert "Cannot transition" in result["error"]


def test_submit_for_review_removed(
    initialized_review_server: Path,
) -> None:
    """submit_for_review MCP tool no longer exists."""
    assert not hasattr(server_module, "submit_for_review")


# -- save_review_comment tool --


def test_save_review_comment_tool_success(
    initialized_review_server: Path,
) -> None:
    design_id = _create_in_review_design()
    result = asyncio.run(
        server_module.save_review_comment(
            design_id=design_id,
            comment="Good analysis",
            status="supported",
        )
    )
    assert result["design_id"] == design_id
    assert result["status_after"] == "supported"
    assert "comment_id" in result
    assert "message" in result


def test_save_review_comment_tool_invalid_status(
    initialized_review_server: Path,
) -> None:
    design_id = _create_in_review_design()
    result = asyncio.run(
        server_module.save_review_comment(
            design_id=design_id,
            comment="Bad",
            status="nonexistent_status",
        )
    )
    assert "error" in result


def test_save_review_comment_tool_not_found(
    initialized_review_server: Path,
) -> None:
    result = asyncio.run(
        server_module.save_review_comment(
            design_id="NONEXIST-H99",
            comment="Ghost",
            status="supported",
        )
    )
    assert "error" in result
    assert "not found" in result["error"]


# -- extract_domain_knowledge tool --


def test_extract_domain_knowledge_tool_preview(
    initialized_review_server: Path,
) -> None:
    design_id = _create_in_review_design()
    asyncio.run(
        server_module.save_review_comment(
            design_id=design_id,
            comment="caution: watch for nulls",
            status="supported",
        )
    )
    result = asyncio.run(server_module.extract_domain_knowledge(design_id))
    assert result["design_id"] == design_id
    assert "entries" in result
    assert result["count"] >= 1
    assert "message" in result


# -- save_extracted_knowledge tool --


def test_save_extracted_knowledge_tool_success(
    initialized_review_server: Path,
) -> None:
    design_id = _create_in_review_design()
    asyncio.run(
        server_module.save_review_comment(
            design_id=design_id,
            comment="caution: watch for nulls",
            status="supported",
        )
    )
    preview = asyncio.run(server_module.extract_domain_knowledge(design_id))
    entries = preview["entries"]

    result = asyncio.run(
        server_module.save_extracted_knowledge(
            design_id=design_id,
            entries=entries,
        )
    )
    assert result["design_id"] == design_id
    assert result["count"] >= 1
    assert "message" in result


def test_save_extracted_knowledge_tool_invalid_entries(
    initialized_review_server: Path,
) -> None:
    result = asyncio.run(
        server_module.save_extracted_knowledge(
            design_id="FP-H01",
            entries=[{"invalid": "data"}],
        )
    )
    assert "error" in result


# -- get_project_context tool --


def test_get_project_context_tool(initialized_review_server: Path) -> None:
    result = asyncio.run(server_module.get_project_context())
    assert "sources" in result
    assert "knowledge_entries" in result
    assert "rules" in result
    assert "total_sources" in result
    assert "total_knowledge" in result
    assert "total_rules" in result


# -- suggest_cautions tool --


def test_suggest_cautions_tool_with_matches(
    initialized_review_server: Path,
) -> None:
    design_id = _create_in_review_design()
    asyncio.run(
        server_module.save_review_comment(
            design_id=design_id,
            comment="table: test_data\ncaution: watch for nulls",
            status="supported",
        )
    )
    preview = asyncio.run(server_module.extract_domain_knowledge(design_id))
    asyncio.run(
        server_module.save_extracted_knowledge(
            design_id=design_id,
            entries=preview["entries"],
        )
    )
    result = asyncio.run(server_module.suggest_cautions(table_names="test_data"))
    assert result["count"] >= 1
    assert len(result["cautions"]) >= 1


def test_suggest_cautions_tool_no_matches(
    initialized_review_server: Path,
) -> None:
    result = asyncio.run(server_module.suggest_cautions(table_names="nonexistent"))
    assert result["count"] == 0
    assert result["cautions"] == []


# ---------------------------------------------------------------------------
# save_review_batch MCP tool tests (Inline Review Comments)
# ---------------------------------------------------------------------------


class TestSaveReviewBatchTool:
    """Tests for save_review_batch MCP tool (FR-18)."""

    def test_save_review_batch_tool_success(
        self, initialized_review_server: Path
    ) -> None:
        """FR-18: Valid batch creation via MCP tool."""
        design_id = _create_in_review_design()
        result = asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="supported",
                comments=[{"comment": "Good analysis"}],
            )
        )
        assert "batch_id" in result
        assert result["status_after"] == "supported"

    def test_save_review_batch_tool_with_sections(
        self, initialized_review_server: Path
    ) -> None:
        """FR-18: Batch with target_section + target_content."""
        design_id = _create_in_review_design()
        result = asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="supported",
                comments=[
                    {
                        "comment": "Check metrics",
                        "target_section": "metrics",
                        "target_content": {"kpi": "CVR"},
                    }
                ],
            )
        )
        assert "batch_id" in result
        assert result["status_after"] == "supported"

    def test_save_review_batch_tool_non_in_review(
        self, initialized_review_server: Path
    ) -> None:
        """FR-18: Non-in_review design returns error."""
        design_id = _create_in_review_design()
        # Move to terminal state via valid transition
        asyncio.run(server_module.transition_design_status(design_id, "supported"))
        result = asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="supported",
                comments=[{"comment": "Should fail"}],
            )
        )
        assert "error" in result

    def test_save_review_batch_tool_not_found(
        self, initialized_review_server: Path
    ) -> None:
        """MCP tool returns error for non-existent design_id."""
        result = asyncio.run(
            server_module.save_review_batch(
                design_id="nonexistent-id",
                status_after="supported",
                comments=[{"comment": "Should fail"}],
            )
        )
        assert "error" in result
        assert "not found" in result["error"]

    def test_save_review_batch_tool_validation_error(
        self, initialized_review_server: Path
    ) -> None:
        """MCP tool returns error for invalid comment (exceeds max_length)."""
        design_id = _create_in_review_design()
        result = asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="supported",
                comments=[{"comment": "x" * 2001}],
            )
        )
        assert "error" in result


# ---------------------------------------------------------------------------
# get_review_comments MCP tool tests (analysis-revision Task 1.1)
# ---------------------------------------------------------------------------


class TestGetReviewCommentsTool:
    """Tests for get_review_comments MCP tool (REQ-1)."""

    def test_get_review_comments_returns_batches(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-01: Returns review batches with correct structure."""
        design_id = _create_in_review_design()
        asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="revision_requested",
                comments=[{"comment": "Fix hypothesis"}],
            )
        )
        result = asyncio.run(server_module.get_review_comments(design_id))
        assert result["design_id"] == design_id
        assert result["count"] == 1
        assert result["batches"][0]["status_after"] == "revision_requested"
        assert result["batches"][0]["comments"][0]["comment"] == "Fix hypothesis"

    def test_get_review_comments_empty_when_no_reviews(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-02: Returns empty list when no reviews exist."""
        design_id = _create_in_review_design()
        result = asyncio.run(server_module.get_review_comments(design_id))
        assert result["design_id"] == design_id
        assert result["batches"] == []
        assert result["count"] == 0

    def test_get_review_comments_invalid_design_id(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-03: Returns error for invalid design_id."""
        result_empty = asyncio.run(server_module.get_review_comments(""))
        assert "error" in result_empty

        result_path = asyncio.run(server_module.get_review_comments("../etc/passwd"))
        assert "error" in result_path

    def test_get_review_comments_corrupted_yaml_returns_empty(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-04: Returns empty list for corrupted YAML (graceful degradation)."""
        design_id = _create_in_review_design()
        asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="revision_requested",
                comments=[{"comment": "Will corrupt"}],
            )
        )
        # Overwrite reviews YAML with garbage
        reviews_path = (
            initialized_review_server
            / ".insight"
            / "designs"
            / f"{design_id}_reviews.yaml"
        )
        reviews_path.write_text("{{{{invalid yaml: [[[")
        result = asyncio.run(server_module.get_review_comments(design_id))
        assert result["batches"] == []
        assert result["count"] == 0
        assert "error" not in result

    def test_get_review_comments_sorted_descending(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-05: Multiple batches are sorted by created_at descending."""
        design_id = _create_in_review_design()
        # Save batch 1
        asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="revision_requested",
                comments=[{"comment": "First batch"}],
            )
        )
        # Transition back to in_review
        asyncio.run(server_module.transition_design_status(design_id, "in_review"))
        # Save batch 2
        asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="revision_requested",
                comments=[{"comment": "Second batch"}],
            )
        )
        result = asyncio.run(server_module.get_review_comments(design_id))
        assert result["count"] == 2
        assert result["batches"][0]["created_at"] >= result["batches"][1]["created_at"]

    def test_get_review_comments_includes_target_fields(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-06: Response includes target_section and target_content."""
        design_id = _create_in_review_design()
        asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="revision_requested",
                comments=[
                    {
                        "comment": "Check metrics",
                        "target_section": "metrics",
                        "target_content": [{"target": "rev"}],
                    }
                ],
            )
        )
        result = asyncio.run(server_module.get_review_comments(design_id))
        batch = result["batches"][0]
        assert batch["comments"][0]["target_section"] == "metrics"
        assert batch["comments"][0]["target_content"] == [{"target": "rev"}]

    def test_get_review_comments_nonexistent_design_id(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-07: Valid format but nonexistent ID returns empty (not error)."""
        result = asyncio.run(server_module.get_review_comments("NONEXISTENT-H99"))
        assert result["design_id"] == "NONEXISTENT-H99"
        assert result["batches"] == []
        assert result["count"] == 0
        assert "error" not in result

    def test_get_review_comments_service_exception_returns_error(
        self, initialized_review_server: Path
    ) -> None:
        """Unit-08: Service exception returns error dict."""
        with patch.object(
            type(registry.review_service),
            "list_review_batches",
            side_effect=RuntimeError("boom"),
        ):
            result = asyncio.run(server_module.get_review_comments("ANY-H01"))
        assert "error" in result

    def test_review_write_then_read_roundtrip(
        self, initialized_review_server: Path
    ) -> None:
        """Integ-01: save_review_batch -> get_review_comments roundtrip."""
        design_id = _create_in_review_design()
        comments_data = [
            {"comment": "Fix hypothesis statement"},
            {
                "comment": "Check metrics definition",
                "target_section": "metrics",
                "target_content": {"kpi": "CVR"},
            },
            {
                "comment": "Update chart",
                "target_section": "chart",
                "target_content": [{"type": "bar"}],
            },
        ]
        write_result = asyncio.run(
            server_module.save_review_batch(
                design_id=design_id,
                status_after="revision_requested",
                comments=comments_data,
            )
        )
        assert "batch_id" in write_result

        read_result = asyncio.run(server_module.get_review_comments(design_id))
        assert read_result["count"] == 1
        read_comments = read_result["batches"][0]["comments"]
        assert len(read_comments) == 3
        assert read_comments[0]["comment"] == "Fix hypothesis statement"
        assert read_comments[1]["comment"] == "Check metrics definition"
        assert read_comments[2]["comment"] == "Update chart"


# ---------------------------------------------------------------------------
# Knowledge Suggestion MCP tools tests (Task 5.1)
# ---------------------------------------------------------------------------


class TestKnowledgeSuggestionMCPTools:
    """Tests for suggest_knowledge_for_design and referenced_knowledge params."""

    def test_get_domain_knowledge_error_includes_finding(
        self, initialized_catalog_server: Path
    ) -> None:
        """T-MCP.0: get_domain_knowledge error message includes 'finding'."""
        asyncio.run(
            server_module.add_catalog_entry(
                source_id="test-src",
                name="Test",
                type="csv",
                description="Test",
                connection={},
            )
        )
        result = asyncio.run(
            server_module.get_domain_knowledge("test-src", category="invalid_cat")
        )
        assert "error" in result
        assert "finding" in result["error"]

    def test_suggest_knowledge_for_design_tool(
        self, initialized_review_server: Path
    ) -> None:
        """T-MCP.1: suggest_knowledge_for_design MCP tool returns suggestions."""
        result = asyncio.run(
            server_module.suggest_knowledge_for_design(section="metrics")
        )
        assert "suggestions" in result
        assert "total" in result

    def test_suggest_knowledge_hypothesis_text_truncated_at_1001(
        self, initialized_review_server: Path
    ) -> None:
        """S-03: hypothesis_text of 1001 chars is truncated to 1000."""
        text_1001 = "a" * 1001
        with patch.object(
            type(registry.rules_service), "suggest_knowledge_for_design"
        ) as mock_suggest:
            mock_suggest.return_value = {
                "section": "metrics",
                "suggestions": {},
                "total": 0,
            }
            asyncio.run(
                server_module.suggest_knowledge_for_design(
                    section="metrics", hypothesis_text=text_1001
                )
            )
            _, kwargs = mock_suggest.call_args
            assert len(kwargs["hypothesis_text"]) == 1000

    def test_suggest_knowledge_hypothesis_text_at_1000_unchanged(
        self, initialized_review_server: Path
    ) -> None:
        """S-03: hypothesis_text of exactly 1000 chars passes through unchanged."""
        text_1000 = "b" * 1000
        with patch.object(
            type(registry.rules_service), "suggest_knowledge_for_design"
        ) as mock_suggest:
            mock_suggest.return_value = {
                "section": "metrics",
                "suggestions": {},
                "total": 0,
            }
            asyncio.run(
                server_module.suggest_knowledge_for_design(
                    section="metrics", hypothesis_text=text_1000
                )
            )
            _, kwargs = mock_suggest.call_args
            assert kwargs["hypothesis_text"] == text_1000

    def test_suggest_knowledge_hypothesis_text_none_unchanged(
        self, initialized_review_server: Path
    ) -> None:
        """S-03: hypothesis_text=None remains None."""
        result = asyncio.run(
            server_module.suggest_knowledge_for_design(
                section="metrics", hypothesis_text=None
            )
        )
        assert "suggestions" in result

    def test_create_analysis_design_with_referenced_knowledge(
        self, initialized_review_server: Path
    ) -> None:
        """T-MCP.2: create_analysis_design accepts referenced_knowledge."""
        ref = {"hypothesis_statement": ["K-001"]}
        result = asyncio.run(
            server_module.create_analysis_design(
                title="Test",
                hypothesis_statement="stmt",
                hypothesis_background="bg",
                referenced_knowledge=ref,
            )
        )
        assert "id" in result
        # Verify it was stored
        design = asyncio.run(server_module.get_analysis_design(result["id"]))
        assert design["referenced_knowledge"] == ref

    def test_update_analysis_design_with_referenced_knowledge(
        self, initialized_review_server: Path
    ) -> None:
        """T-MCP.3: update_analysis_design merges referenced_knowledge."""
        create_result = asyncio.run(
            server_module.create_analysis_design(
                title="Test",
                hypothesis_statement="stmt",
                hypothesis_background="bg",
                referenced_knowledge={"hypothesis_statement": ["K-001"]},
            )
        )
        design_id = create_result["id"]
        result = asyncio.run(
            server_module.update_analysis_design(
                design_id=design_id,
                referenced_knowledge={"hypothesis_statement": ["K-002"]},
            )
        )
        assert result["referenced_knowledge"] == {
            "hypothesis_statement": ["K-001", "K-002"]
        }


# ---------------------------------------------------------------------------
# Typed field MCP tool tests (verification-design)
# ---------------------------------------------------------------------------


def test_create_analysis_design_with_typed_explanatory(
    initialized_server: Path,
) -> None:
    """Integ-03: create with explanatory with role field, assert no error."""
    result = asyncio.run(
        server_module.create_analysis_design(
            title="t",
            hypothesis_statement="s",
            hypothesis_background="b",
            explanatory=[{"name": "x1", "role": "treatment"}],
        )
    )
    assert "error" not in result
    assert "id" in result


def test_update_analysis_design_with_typed_explanatory(
    initialized_server: Path,
) -> None:
    """Integ-04: update with explanatory with role field, assert no error."""
    create_result = asyncio.run(
        server_module.create_analysis_design(
            title="t",
            hypothesis_statement="s",
            hypothesis_background="b",
        )
    )
    design_id = create_result["id"]
    result = asyncio.run(
        server_module.update_analysis_design(
            design_id=design_id,
            explanatory=[
                {"name": "x1", "role": "treatment"},
                {"name": "x2", "role": "confounder"},
            ],
        )
    )
    assert "error" not in result


def test_create_analysis_design_with_metrics_list(
    initialized_server: Path,
) -> None:
    """Integ-06: create with metrics list, assert no error."""
    result = asyncio.run(
        server_module.create_analysis_design(
            title="t",
            hypothesis_statement="s",
            hypothesis_background="b",
            metrics=[{"target": "y", "tier": "primary"}],
        )
    )
    assert "error" not in result
    assert "id" in result


def test_update_analysis_design_with_methodology(
    initialized_server: Path,
) -> None:
    """Integ-11: update with methodology, assert no error."""
    create_result = asyncio.run(
        server_module.create_analysis_design(
            title="t",
            hypothesis_statement="s",
            hypothesis_background="b",
        )
    )
    design_id = create_result["id"]
    result = asyncio.run(
        server_module.update_analysis_design(
            design_id=design_id,
            methodology={"method": "CausalImpact", "package": "tfcausalimpact"},
        )
    )
    assert "error" not in result


# ---------------------------------------------------------------------------
# Headless mode, SSE transport, multi-client tests (Integ-02, Integ-03, Integ-04)
# ---------------------------------------------------------------------------


class TestHeadlessMode:
    """Integration tests for headless mode: SSE only, no WebUI (Integ-02)."""

    def test_headless_mcp_sse_available(self, tmp_project: Path) -> None:
        """Integ-02: get_mcp_sse_app() returns a valid ASGI app."""
        from starlette.testclient import TestClient

        from insight_blueprint.server import get_mcp_sse_app

        registry.design_service = DesignService(tmp_project)
        catalog_service = CatalogService(tmp_project)
        catalog_service.rebuild_index()
        registry.catalog_service = catalog_service
        registry.review_service = ReviewService(tmp_project, registry.design_service)
        db_path = tmp_project / ".insight" / "catalog.db"
        registry.rules_service = RulesService(
            tmp_project, catalog_service, registry.design_service, db_path
        )

        sse_app = get_mcp_sse_app()
        assert callable(sse_app)

        # The SSE app should respond to requests (not 404)
        with TestClient(sse_app, raise_server_exceptions=False) as client:
            # POST /messages without valid session should return error, not 404
            resp = client.post("/messages", json={})
            assert resp.status_code != 404

    def test_headless_no_webui(self, tmp_project: Path) -> None:
        """Integ-02: The SSE app does NOT have WebUI routes."""
        from starlette.testclient import TestClient

        from insight_blueprint.server import get_mcp_sse_app

        registry.design_service = DesignService(tmp_project)
        catalog_service = CatalogService(tmp_project)
        catalog_service.rebuild_index()
        registry.catalog_service = catalog_service
        registry.review_service = ReviewService(tmp_project, registry.design_service)
        db_path = tmp_project / ".insight" / "catalog.db"
        registry.rules_service = RulesService(
            tmp_project, catalog_service, registry.design_service, db_path
        )

        sse_app = get_mcp_sse_app()
        with TestClient(sse_app, raise_server_exceptions=False) as client:
            # SSE app should NOT serve WebUI routes
            resp_designs = client.get("/api/designs")
            assert resp_designs.status_code in (404, 405)

            # SSE app should NOT serve static files at /
            resp_root = client.get("/")
            # Either 404 or the SSE app's own response, but NOT HTML
            content_type = resp_root.headers.get("content-type", "")
            if resp_root.status_code == 200:
                assert "text/html" not in content_type


class TestSseTransport:
    """Tests verifying SSE transport configuration (Integ-03)."""

    def test_sse_app_is_valid_asgi(self) -> None:
        """Integ-03: get_mcp_sse_app() returns a callable ASGI app."""
        from insight_blueprint.server import get_mcp_sse_app

        sse_app = get_mcp_sse_app()
        assert callable(sse_app)

    def test_tools_list_via_direct_call(self, tmp_project: Path) -> None:
        """Integ-03: All tools are registered on the mcp instance."""
        from insight_blueprint.server import mcp

        registry.design_service = DesignService(tmp_project)
        catalog_service = CatalogService(tmp_project)
        catalog_service.rebuild_index()
        registry.catalog_service = catalog_service
        registry.review_service = ReviewService(tmp_project, registry.design_service)
        db_path = tmp_project / ".insight" / "catalog.db"
        registry.rules_service = RulesService(
            tmp_project, catalog_service, registry.design_service, db_path
        )

        tools = asyncio.run(mcp.list_tools())
        tool_names = sorted(t.name for t in tools)
        assert len(tool_names) >= 18
        # Verify key tools are present
        expected_tools = {
            "create_analysis_design",
            "list_analysis_designs",
            "get_analysis_design",
            "update_analysis_design",
            "add_catalog_entry",
            "search_catalog",
            "transition_design_status",
            "save_review_comment",
            "save_review_batch",
            "get_review_comments",
            "get_project_context",
            "suggest_cautions",
            "suggest_knowledge_for_design",
        }
        assert expected_tools.issubset(set(tool_names))


class TestSseMultiClient:
    """Tests for multiple client independence (Integ-04)."""

    def test_two_clients_can_get_independent_apps(self) -> None:
        """Integ-04: Two calls to get_mcp_sse_app() return valid apps."""
        from insight_blueprint.server import get_mcp_sse_app

        app1 = get_mcp_sse_app()
        app2 = get_mcp_sse_app()
        assert callable(app1)
        assert callable(app2)
