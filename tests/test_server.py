"""Tests for server.py MCP tool layer."""

import asyncio
from pathlib import Path

import pytest

import insight_blueprint.server as server_module
from insight_blueprint.core.designs import DesignService


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    """Reset server._service before each test."""
    original = server_module._service
    yield  # type: ignore[misc]
    server_module._service = original


@pytest.fixture
def initialized_server(tmp_path: Path) -> Path:
    """Set up server with a real DesignService backed by tmp_path."""
    (tmp_path / ".insight" / "designs").mkdir(parents=True)
    server_module._service = DesignService(tmp_path)
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
    assert result["status"] == "draft"
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
    server_module._service = None
    with pytest.raises(RuntimeError, match="Service not initialized"):
        server_module.get_service()


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
    assert result["status"] == "draft"


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
            design_id=create_result["id"], status="active"
        )
    )
    assert result["status"] == "active"
