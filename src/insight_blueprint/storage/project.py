"""Project initialization -- idempotent .insight/ directory setup."""

import importlib.resources
import json
import os
import shutil
import tempfile
from pathlib import Path

from insight_blueprint.storage.yaml_store import write_yaml


def init_project(project_path: Path) -> None:
    """Initialize .insight/ directory and project infrastructure.

    Idempotent: safe to call multiple times without data corruption.
    Does NOT wire server._service -- that is done in cli.py.
    """
    _create_insight_dirs(project_path)
    _copy_skills_template(project_path)
    _register_mcp_server(project_path)


def _create_insight_dirs(project_path: Path) -> None:
    """Create .insight/ directory tree idempotently."""
    insight = project_path / ".insight"

    # Create directories
    (insight / "designs").mkdir(parents=True, exist_ok=True)
    (insight / "catalog" / "knowledge").mkdir(parents=True, exist_ok=True)
    (insight / "rules").mkdir(parents=True, exist_ok=True)

    # Create config.yaml (only if absent)
    config_path = insight / "config.yaml"
    if not config_path.exists():
        write_yaml(config_path, {"schema_version": 1})

    # Create catalog/sources/ directory (per-source YAML files live here)
    (insight / "catalog" / "sources").mkdir(parents=True, exist_ok=True)

    # Create .sqlite/ directory for FTS5 databases
    (insight / ".sqlite").mkdir(parents=True, exist_ok=True)

    review_rules = insight / "rules" / "review_rules.yaml"
    if not review_rules.exists():
        write_yaml(review_rules, {"rules": []})

    analysis_rules = insight / "rules" / "analysis_rules.yaml"
    if not analysis_rules.exists():
        write_yaml(analysis_rules, {"rules": []})

    extracted_knowledge = insight / "rules" / "extracted_knowledge.yaml"
    if not extracted_knowledge.exists():
        write_yaml(extracted_knowledge, {"source_id": "review", "entries": []})


def _copy_skills_template(project_path: Path) -> None:
    """Copy bundled _skills/ to .claude/skills/ (first run only per skill)."""
    pkg_files = importlib.resources.files("insight_blueprint")
    skills_to_copy = ["analysis-design", "catalog-register"]

    for skill_name in skills_to_copy:
        dest = project_path / ".claude" / "skills" / skill_name
        if dest.exists():
            continue  # Never overwrite user customizations
        src = pkg_files / "_skills" / skill_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(src), str(dest))


def _register_mcp_server(project_path: Path) -> None:
    """Upsert insight-blueprint into project .mcp.json (preserve other servers)."""
    mcp_json_path = project_path / ".mcp.json"

    # Load existing .mcp.json or start fresh
    if mcp_json_path.exists():
        with mcp_json_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Upsert insight-blueprint entry
    config["mcpServers"]["insight-blueprint"] = {
        "command": "uvx",
        "args": ["insight-blueprint", "--project", str(project_path.resolve())],
        "env": {
            "PYTHONUNBUFFERED": "1",
            "MCP_TIMEOUT": "10000",
        },
    }

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(dir=project_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, mcp_json_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
