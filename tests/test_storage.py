"""Tests for storage layer: yaml_store and project initialization."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

# === yaml_store tests ===


def test_write_yaml_creates_file(tmp_path: Path) -> None:
    """Basic write creates file with correct content."""
    target = tmp_path / "test.yaml"
    data = {"key": "value", "number": 42}
    write_yaml(target, data)

    assert target.exists()
    result = read_yaml(target)
    assert result["key"] == "value"
    assert result["number"] == 42


def test_write_yaml_is_atomic(tmp_path: Path) -> None:
    """Simulate crash during write -- original file is preserved."""
    target = tmp_path / "test.yaml"
    original_data = {"original": True}
    write_yaml(target, original_data)

    # Simulate a crash by patching os.replace to raise
    with patch(
        "insight_blueprint.storage.yaml_store.os.replace",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises(OSError, match="disk full"):
            write_yaml(target, {"corrupted": True})

    # Original file should be preserved
    result = read_yaml(target)
    assert result["original"] is True


def test_read_yaml_returns_empty_for_missing_file(tmp_path: Path) -> None:
    """Returns {} for a file that does not exist."""
    missing = tmp_path / "nonexistent.yaml"
    result = read_yaml(missing)
    assert result == {}


# === init_project tests ===


def _init_project(project_path: Path) -> None:
    """Helper to import and call init_project."""
    from insight_blueprint.storage.project import init_project

    init_project(project_path)


def test_init_project_creates_directory_structure(tmp_path: Path) -> None:
    """.insight/ directory tree is created."""
    _init_project(tmp_path)

    insight = tmp_path / ".insight"
    assert insight.is_dir()
    assert (insight / "designs").is_dir()
    assert (insight / "catalog").is_dir()
    assert (insight / "catalog" / "knowledge").is_dir()
    assert (insight / "rules").is_dir()


def test_init_project_creates_sources_directory(tmp_path: Path) -> None:
    """catalog/sources/ directory exists after init."""
    _init_project(tmp_path)

    sources_dir = tmp_path / ".insight" / "catalog" / "sources"
    assert sources_dir.is_dir()


def test_init_project_creates_sqlite_dir(tmp_path: Path) -> None:
    """.sqlite/ directory exists after init."""
    _init_project(tmp_path)

    sqlite_dir = tmp_path / ".insight" / ".sqlite"
    assert sqlite_dir.is_dir()


def test_init_project_creates_catalog_knowledge_dir(tmp_path: Path) -> None:
    """catalog/knowledge/ directory exists after init."""
    _init_project(tmp_path)

    knowledge = tmp_path / ".insight" / "catalog" / "knowledge"
    assert knowledge.is_dir()


def test_init_project_creates_rules_yaml_stubs(tmp_path: Path) -> None:
    """Both rules/ yaml files exist after init."""
    _init_project(tmp_path)

    rules = tmp_path / ".insight" / "rules"
    assert (rules / "review_rules.yaml").exists()
    assert (rules / "analysis_rules.yaml").exists()

    review = read_yaml(rules / "review_rules.yaml")
    assert review["rules"] == []

    analysis = read_yaml(rules / "analysis_rules.yaml")
    assert analysis["rules"] == []


def test_init_project_creates_config_with_schema_version(tmp_path: Path) -> None:
    """config.yaml contains schema_version: 1."""
    _init_project(tmp_path)

    config = read_yaml(tmp_path / ".insight" / "config.yaml")
    assert config["schema_version"] == 1


def test_init_project_copies_skills_template_when_absent(tmp_path: Path) -> None:
    """.claude/skills/analysis-design/ is created on first run."""
    _init_project(tmp_path)

    skill_dir = tmp_path / ".claude" / "skills" / "analysis-design"
    assert skill_dir.is_dir()
    assert (skill_dir / "SKILL.md").exists()


def test_init_project_does_not_overwrite_existing_skills(tmp_path: Path) -> None:
    """Existing .claude/skills/analysis-design/ is not modified on re-run."""
    # Create existing skills dir with custom content
    skill_dir = tmp_path / ".claude" / "skills" / "analysis-design"
    skill_dir.mkdir(parents=True)
    custom_file = skill_dir / "SKILL.md"
    custom_file.write_text("custom content")

    _init_project(tmp_path)

    # Custom content should be preserved
    assert custom_file.read_text() == "custom content"


def test_init_project_registers_mcp_json_when_absent(tmp_path: Path) -> None:
    """.mcp.json is created with insight-blueprint when absent."""
    _init_project(tmp_path)

    mcp_json = tmp_path / ".mcp.json"
    assert mcp_json.exists()

    with mcp_json.open() as f:
        config = json.load(f)

    assert "insight-blueprint" in config["mcpServers"]
    server_config = config["mcpServers"]["insight-blueprint"]
    assert server_config["command"] == "uvx"


def test_init_project_merges_existing_mcp_json(tmp_path: Path) -> None:
    """Existing servers in .mcp.json are preserved."""
    # Create existing .mcp.json with another server
    mcp_json = tmp_path / ".mcp.json"
    existing = {
        "mcpServers": {
            "other-server": {
                "command": "node",
                "args": ["other.js"],
            }
        }
    }
    with mcp_json.open("w") as f:
        json.dump(existing, f)

    _init_project(tmp_path)

    with mcp_json.open() as f:
        config = json.load(f)

    # Both servers should exist
    assert "other-server" in config["mcpServers"]
    assert "insight-blueprint" in config["mcpServers"]
    # Other server config preserved
    assert config["mcpServers"]["other-server"]["command"] == "node"


def test_init_project_does_not_modify_if_already_registered(tmp_path: Path) -> None:
    """Re-running init does not corrupt existing registration."""
    _init_project(tmp_path)

    # Read state after first init
    mcp_json = tmp_path / ".mcp.json"
    with mcp_json.open() as f:
        first_config = json.load(f)

    # Run again
    _init_project(tmp_path)

    with mcp_json.open() as f:
        second_config = json.load(f)

    # Config should be identical
    assert first_config == second_config


def test_init_project_partial_recovery(tmp_path: Path) -> None:
    """Missing artifacts are created on second run after partial failure."""
    _init_project(tmp_path)

    # Simulate partial failure: remove some artifacts
    (tmp_path / ".insight" / "rules" / "review_rules.yaml").unlink()
    (tmp_path / ".insight" / "rules" / "analysis_rules.yaml").unlink()

    # Re-run init
    _init_project(tmp_path)

    # Missing artifacts should be recreated
    assert (tmp_path / ".insight" / "rules" / "review_rules.yaml").exists()
    assert (tmp_path / ".insight" / "rules" / "analysis_rules.yaml").exists()

    # Existing artifacts should still be there
    assert (tmp_path / ".insight" / "config.yaml").exists()
    assert (tmp_path / ".insight" / "catalog" / "sources").is_dir()


def test_init_project_copies_catalog_register_skill(tmp_path: Path) -> None:
    """.claude/skills/catalog-register/ is created on first run."""
    _init_project(tmp_path)

    skill_dir = tmp_path / ".claude" / "skills" / "catalog-register"
    assert skill_dir.is_dir()
    assert (skill_dir / "SKILL.md").exists()


# === extracted_knowledge.yaml tests (SPEC-3 Task 4.2) ===


def test_init_project_creates_extracted_knowledge_yaml(tmp_path: Path) -> None:
    """extracted_knowledge.yaml is created with correct structure."""
    _init_project(tmp_path)

    ek_path = tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml"
    assert ek_path.exists()

    data = read_yaml(ek_path)
    assert data["source_id"] == "review"
    assert data["entries"] == []


def test_init_project_does_not_overwrite_existing_extracted_knowledge(
    tmp_path: Path,
) -> None:
    """Existing extracted_knowledge.yaml is preserved on re-run."""
    _init_project(tmp_path)

    # Add a custom entry
    ek_path = tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml"
    custom_data = {
        "source_id": "review",
        "entries": [{"key": "custom-1", "content": "keep me"}],
    }
    write_yaml(ek_path, custom_data)

    # Re-run init
    _init_project(tmp_path)

    # Custom data should be preserved
    data = read_yaml(ek_path)
    assert len(data["entries"]) == 1
    assert data["entries"][0]["key"] == "custom-1"
