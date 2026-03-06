"""Tests for server.py MCP tool layer."""

import asyncio
from pathlib import Path

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


def test_update_analysis_design_mcp_returns_error_for_invalid_status(
    initialized_server: Path,
) -> None:
    create_result = asyncio.run(
        server_module.create_analysis_design(
            title="T", hypothesis_statement="s", hypothesis_background="b"
        )
    )
    result = asyncio.run(
        server_module.update_analysis_design(
            design_id=create_result["id"], status="invalid_status"
        )
    )
    assert "error" in result
    assert "invalid_status" in result["error"]


def test_update_analysis_design_mcp_updates_status(initialized_server: Path) -> None:
    create_result = asyncio.run(
        server_module.create_analysis_design(
            title="T", hypothesis_statement="s", hypothesis_background="b"
        )
    )
    result = asyncio.run(
        server_module.update_analysis_design(
            design_id=create_result["id"], status="analyzing"
        )
    )
    assert result["status"] == "analyzing"


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
    registry.rules_service = RulesService(tmp_project, catalog_service)
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
    # Move to terminal state
    asyncio.run(
        server_module.update_analysis_design(design_id=design_id, status="supported")
    )
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
        # Move to terminal state
        asyncio.run(
            server_module.update_analysis_design(
                design_id=design_id, status="supported"
            )
        )
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
