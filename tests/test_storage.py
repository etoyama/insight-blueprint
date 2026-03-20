"""Tests for storage layer: yaml_store and project initialization."""

import json
from concurrent.futures import ThreadPoolExecutor
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


def test_init_project_does_not_copy_skills(tmp_path: Path) -> None:
    """init_project() no longer copies skills to .claude/skills/."""
    _init_project(tmp_path)

    skills_dir = tmp_path / ".claude" / "skills"
    assert not skills_dir.exists()


def test_init_project_does_not_copy_rules(tmp_path: Path) -> None:
    """init_project() no longer copies rules to .claude/rules/."""
    _init_project(tmp_path)

    # .claude/rules/ should not exist (distinct from .insight/rules/ which does)
    rules_dir = tmp_path / ".claude" / "rules"
    assert not rules_dir.exists()


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
    # Issue #2: relative path for portability
    assert server_config["args"] == ["insight-blueprint", "--project", "."]


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


# === corrupt .mcp.json tests (Issue #4) ===


def test_init_project_repairs_corrupt_mcp_json(tmp_path: Path) -> None:
    """Corrupt .mcp.json is backed up and replaced with a fresh one."""
    # Create corrupt .mcp.json
    mcp_json = tmp_path / ".mcp.json"
    mcp_json.write_text("{invalid json content!!!")

    _init_project(tmp_path)

    # Fresh .mcp.json should be valid
    with mcp_json.open() as f:
        config = json.load(f)
    assert "insight-blueprint" in config["mcpServers"]

    # Backup should exist
    backups = list(tmp_path.glob(".mcp.json.bak.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "{invalid json content!!!"


# === concurrent init safety tests (Issue #1) ===


def test_init_project_concurrent_safety(tmp_path: Path) -> None:
    """Concurrent init_project() calls do not corrupt state."""
    from insight_blueprint.storage.project import init_project

    errors: list[Exception] = []

    def run_init() -> None:
        try:
            init_project(tmp_path)
        except Exception as e:
            errors.append(e)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run_init) for _ in range(4)]
        for f in futures:
            f.result()

    assert errors == []

    # All artifacts should be valid
    assert (tmp_path / ".insight" / "config.yaml").exists()
    mcp_json = tmp_path / ".mcp.json"
    with mcp_json.open() as f:
        config = json.load(f)
    assert "insight-blueprint" in config["mcpServers"]
    assert (tmp_path / "CLAUDE.md").exists()


# === write_lock tests (Unit-03: team-server-separation Task 1.2) ===


class TestWriteLock:
    """Verify threading.Lock serializes concurrent write_yaml() calls."""

    def test_concurrent_writes_no_corruption(self, tmp_path: Path) -> None:
        """2 threads x 100 writes each -- final file is valid YAML."""
        import threading as _threading

        target = tmp_path / "concurrent.yaml"
        errors: list[Exception] = []

        def writer(thread_id: int) -> None:
            for i in range(100):
                try:
                    write_yaml(target, {"thread": thread_id, "iteration": i})
                except Exception as e:
                    errors.append(e)

        t1 = _threading.Thread(target=writer, args=(1,))
        t2 = _threading.Thread(target=writer, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert errors == [], f"Unexpected errors: {errors}"

        # Final file must be valid YAML with expected structure
        result = read_yaml(target)
        assert "thread" in result
        assert "iteration" in result
        assert result["thread"] in (1, 2)

    def test_concurrent_writes_no_intermediate_state(self, tmp_path: Path) -> None:
        """Reader thread never sees incomplete/invalid YAML during writes."""
        import threading as _threading

        target = tmp_path / "intermediate.yaml"
        # Seed file so reader always has something
        write_yaml(target, {"seed": True})

        invalid_reads: list[str] = []
        stop_event = _threading.Event()

        def writer() -> None:
            for i in range(200):
                write_yaml(target, {"counter": i})
            stop_event.set()

        def reader() -> None:
            while not stop_event.is_set():
                try:
                    data = read_yaml(target)
                    if not isinstance(data, dict):
                        invalid_reads.append(f"Not a dict: {data!r}")
                except Exception as e:
                    invalid_reads.append(str(e))

        rt = _threading.Thread(target=reader)
        wt = _threading.Thread(target=writer)
        rt.start()
        wt.start()
        wt.join()
        stop_event.set()
        rt.join()

        assert invalid_reads == [], f"Invalid reads detected: {invalid_reads}"

    def test_write_lock_is_module_level(self) -> None:
        """_write_lock is a module-level threading.Lock instance."""
        import threading as _threading

        from insight_blueprint.storage import yaml_store as _ys

        assert hasattr(_ys, "_write_lock")
        assert isinstance(_ys._write_lock, type(_threading.Lock()))


# === .mcp.json stdio registration test (Unit-05: team-server-separation Task 5.2) ===


class TestInitProjectMcpRegistration:
    """Verify init_project registers stdio transport in .mcp.json."""

    def test_mcp_json_registers_stdio_transport(self, tmp_path: Path) -> None:
        """insight-blueprint entry uses stdio (command+args), not SSE."""
        from insight_blueprint.storage.project import init_project

        init_project(tmp_path)

        mcp_json = tmp_path / ".mcp.json"
        assert mcp_json.exists()

        with mcp_json.open() as f:
            config = json.load(f)

        server = config["mcpServers"]["insight-blueprint"]

        # stdio transport must have command and args
        assert "command" in server, "Missing 'command' key (stdio transport)"
        assert "args" in server, "Missing 'args' key (stdio transport)"

        # Must NOT have SSE-style keys
        assert "type" not in server or server.get("type") != "sse", (
            "Should not use SSE transport"
        )
        assert "url" not in server, "Should not have 'url' key (SSE indicator)"


# === Plugin distribution: init_project simplified tests ===


class TestInitProjectPluginDistribution:
    """Verify init_project() with plugin-distribution simplifications."""

    def test_init_project_claude_md_has_extension_policy(self, tmp_path: Path) -> None:
        """CLAUDE.md managed section contains Extension Policy."""
        _init_project(tmp_path)

        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "Extension Policy" in content

    def test_init_project_claude_md_has_optional_package_note(
        self, tmp_path: Path
    ) -> None:
        """CLAUDE.md managed section mentions optional Python package."""
        _init_project(tmp_path)

        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "Optional" in content
        assert "Python Package" in content or "uv add insight-blueprint" in content

    def test_init_project_idempotent(self, tmp_path: Path) -> None:
        """Running init_project() twice produces no duplicates."""
        _init_project(tmp_path)
        _init_project(tmp_path)

        # .mcp.json should have exactly one insight-blueprint entry
        mcp_json = tmp_path / ".mcp.json"
        with mcp_json.open() as f:
            config = json.load(f)
        assert len(config["mcpServers"]) == 1

        # CLAUDE.md should have exactly one managed section
        claude_md = tmp_path / "CLAUDE.md"
        content = claude_md.read_text()
        begin_marker = "<!-- BEGIN insight-blueprint managed section"
        assert content.count(begin_marker) == 1

    def test_upgrade_templates_command_not_exists(self) -> None:
        """Click main.commands has no 'upgrade-templates'."""
        from insight_blueprint.cli import main

        assert "upgrade-templates" not in (main.commands or {})
