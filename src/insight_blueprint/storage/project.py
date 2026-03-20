"""Project initialization -- idempotent .insight/ directory setup."""

import hashlib
import importlib.resources
import json
import logging
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from insight_blueprint.storage.yaml_store import write_yaml

logger = logging.getLogger(__name__)


def init_project(project_path: Path) -> None:
    """Initialize .insight/ directory and project infrastructure.

    Idempotent: safe to call multiple times without data corruption.
    Does NOT wire server._service -- that is done in cli.py.
    Concurrent calls on the same path are serialized via file lock.
    """
    lock_path = project_path / ".insight" / ".init.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(lock_path, timeout=30)

    with lock:
        _create_insight_dirs(project_path)
        _register_mcp_server(project_path)
        _generate_claude_md(project_path)


def _create_insight_dirs(project_path: Path) -> None:
    """Create .insight/ directory tree idempotently."""
    insight = project_path / ".insight"

    # Create directories
    (insight / "designs").mkdir(parents=True, exist_ok=True)
    (insight / "catalog" / "knowledge").mkdir(parents=True, exist_ok=True)
    (insight / "rules").mkdir(parents=True, exist_ok=True)
    (insight / "lineage").mkdir(parents=True, exist_ok=True)

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


def _register_mcp_server(project_path: Path) -> None:
    """Upsert insight-blueprint into project .mcp.json (preserve other servers)."""
    mcp_json_path = project_path / ".mcp.json"

    # Load existing .mcp.json or start fresh
    if mcp_json_path.exists():
        try:
            with mcp_json_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            # Backup corrupt file and start fresh
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            backup_path = mcp_json_path.parent / f".mcp.json.bak.{ts}"
            shutil.copy2(mcp_json_path, backup_path)
            logger.warning(
                "Corrupt .mcp.json backed up to %s. "
                "Other server registrations may need to be re-added manually.",
                backup_path.name,
            )
            config = {}
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Upsert insight-blueprint entry
    config["mcpServers"]["insight-blueprint"] = {
        "command": "uvx",
        "args": ["insight-blueprint", "--project", "."],
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


# ---------------------------------------------------------------------------
# CLAUDE.md generation (marker-delimited managed section)
# ---------------------------------------------------------------------------

_CLAUDE_MD_BEGIN = (
    "<!-- BEGIN insight-blueprint managed section — do not edit manually -->"
)
_CLAUDE_MD_END = "<!-- END insight-blueprint managed section -->"
_CLAUDE_MD_STATE_KEY = "claude_md"
_STATE_FILENAME = ".insight-blueprint-state.json"


def _load_template(name: str) -> str:
    """Load a bundled template file from _templates/."""
    pkg_files = importlib.resources.files("insight_blueprint")
    template = pkg_files / "_templates" / name
    return template.read_text(encoding="utf-8")


def _hash_content(content: str) -> str:
    """SHA-256 of content (LF-normalized)."""
    return hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _load_claude_md_state(project_path: Path) -> dict[str, Any]:
    """Load state for CLAUDE.md from .claude/.insight-blueprint-state.json."""
    state_file = project_path / ".claude" / _STATE_FILENAME
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read state %s: %s", state_file, exc)
        return {}


def _save_claude_md_state(project_path: Path, state: dict[str, Any]) -> None:
    """Save state for CLAUDE.md to .claude/.insight-blueprint-state.json."""
    state_file = project_path / ".claude" / _STATE_FILENAME
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _generate_claude_md(project_path: Path) -> None:
    """Generate or update the insight-blueprint managed section in CLAUDE.md.

    Behavior:
      - CLAUDE.md absent -> create with managed section
      - CLAUDE.md exists, no markers -> append managed section
      - CLAUDE.md exists, markers present -> replace content between markers
      - Content unchanged (hash match) -> skip rewrite
    """
    claude_md_path = project_path / "CLAUDE.md"
    template_content = _load_template("CLAUDE.md.template")
    managed_block = f"{_CLAUDE_MD_BEGIN}\n{template_content}\n{_CLAUDE_MD_END}\n"

    # Check hash to avoid unnecessary rewrites
    new_hash = _hash_content(managed_block)
    state = _load_claude_md_state(project_path)
    if state.get(_CLAUDE_MD_STATE_KEY) == new_hash and claude_md_path.exists():
        # Content hasn't changed and file exists -> skip
        return

    if not claude_md_path.exists():
        # Fresh creation
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        claude_md_path.write_text(managed_block, encoding="utf-8")
        logger.info("CLAUDE.md created with insight-blueprint section")
    else:
        existing = claude_md_path.read_text(encoding="utf-8")
        if _CLAUDE_MD_BEGIN in existing and _CLAUDE_MD_END in existing:
            # Replace between markers
            pattern = re.compile(
                re.escape(_CLAUDE_MD_BEGIN)
                + r".*?"
                + re.escape(_CLAUDE_MD_END)
                + r"\n?",
                re.DOTALL,
            )
            updated = pattern.sub(managed_block, existing)
            claude_md_path.write_text(updated, encoding="utf-8")
            logger.info("CLAUDE.md managed section updated")
        else:
            # Append managed section
            separator = "\n" if existing.endswith("\n") else "\n\n"
            claude_md_path.write_text(
                existing + separator + managed_block, encoding="utf-8"
            )
            logger.info("CLAUDE.md managed section appended")

    state[_CLAUDE_MD_STATE_KEY] = new_hash
    _save_claude_md_state(project_path, state)
