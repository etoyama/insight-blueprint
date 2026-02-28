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
from importlib.resources.abc import Traversable
from pathlib import Path

from packaging.version import InvalidVersion, Version

from insight_blueprint.storage.yaml_store import write_yaml

logger = logging.getLogger(__name__)


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


def _discover_bundled_skills() -> list[str]:
    """Auto-detect skill directories under _skills/ that contain SKILL.md.

    Returns a sorted list of directory names.
    """
    pkg_files = importlib.resources.files("insight_blueprint")
    skills_root = pkg_files / "_skills"
    result: list[str] = []
    try:
        for entry in skills_root.iterdir():
            if not entry.is_dir():
                continue
            # S-2: Reject suspicious entry names (path traversal defense)
            if ".." in entry.name or "/" in entry.name or "\\" in entry.name:
                logger.warning("Skipping invalid skill name: %s", entry.name)
                continue
            # Check if directory contains SKILL.md
            skill_md = entry / "SKILL.md"
            try:
                if skill_md.is_file():
                    result.append(entry.name)
            except (AttributeError, TypeError):
                # Traversable may not support / operator for all entries
                continue
    except (FileNotFoundError, TypeError):
        return []
    return sorted(result)


def _parse_version_from_content(
    content: str, *, source_label: str | None = None
) -> str | None:
    """Parse version from SKILL.md content string (shared logic).

    Returns validated semver string or None. Logs warnings if source_label given.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        if source_label:
            logger.warning("Invalid frontmatter in %s", source_label)
        return None

    frontmatter = match.group(1)
    version_match = re.search(r"^version:\s*(.+)$", frontmatter, re.MULTILINE)
    if not version_match:
        return None

    raw_value = version_match.group(1).strip()
    if (raw_value.startswith('"') and raw_value.endswith('"')) or (
        raw_value.startswith("'") and raw_value.endswith("'")
    ):
        raw_value = raw_value[1:-1]

    try:
        Version(raw_value)
    except InvalidVersion:
        if source_label:
            logger.warning("Invalid version '%s' in %s", raw_value, source_label)
        return None

    return raw_value


def _get_skill_version(skill_md_path: Path) -> str | None:
    """Parse the version field from SKILL.md YAML frontmatter.

    Returns the version string (validated as semver) or None on any error.
    Logs a warning on parse errors or invalid versions.
    """
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Cannot read SKILL.md: %s", skill_md_path)
        return None

    return _parse_version_from_content(content, source_label=str(skill_md_path))


_STATE_FILENAME = ".insight-blueprint-state.json"

# Managed files/dirs excluded from hash when exclude_managed=True
_MANAGED_FILES = {_STATE_FILENAME, ".bundled-update.json"}
_MANAGED_DIRS = {".bundled-update"}


def _hash_entries(entries: list[tuple[str, bytes]]) -> str:
    """Compute SHA-256 over sorted (relative_path, content) pairs.

    Line endings are normalized to LF before hashing.
    """
    h = hashlib.sha256()
    for rel_str, content in sorted(entries, key=lambda x: x[0]):
        h.update(rel_str.encode("utf-8"))
        h.update(content.replace(b"\r\n", b"\n"))
    return h.hexdigest()


def _hash_skill_directory(skill_dir: Path, *, exclude_managed: bool = False) -> str:
    """Compute SHA-256 hash over all files in a skill directory.

    Files are sorted by relative path for determinism.
    Line endings are normalized to LF before hashing.
    With exclude_managed=True, skip state/update files.
    """
    entries: list[tuple[str, bytes]] = []

    for file_path in sorted(skill_dir.rglob("*")):
        if not file_path.is_file():
            continue

        rel = file_path.relative_to(skill_dir)
        rel_parts = rel.parts

        if exclude_managed:
            # Skip managed files at top level
            if len(rel_parts) == 1 and rel_parts[0] in _MANAGED_FILES:
                continue
            # Skip anything under managed directories
            if rel_parts[0] in _MANAGED_DIRS:
                continue

        entries.append((str(rel), file_path.read_bytes()))

    return _hash_entries(entries)


def _load_skill_state(skill_dir: Path) -> dict[str, str | None]:
    """Load skill state from .insight-blueprint-state.json.

    Returns empty dict if file is missing or contains invalid JSON.
    """
    state_file = skill_dir / _STATE_FILENAME
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read skill state %s: %s", state_file, exc)
        return {}


def _save_skill_state(skill_dir: Path, version: str | None, bundled_hash: str) -> None:
    """Save skill state to .insight-blueprint-state.json."""
    state = {
        "installed_version": version,
        "installed_bundled_hash": bundled_hash,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    state_file = skill_dir / _STATE_FILENAME
    state_file.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _copy_skill_tree(src: Traversable, dest: Path) -> None:
    """Recursively copy files from a Traversable source to dest Path.

    On update (dest exists): rename to .backup -> copy new -> delete .backup
    on success, restore .backup on failure.
    Does NOT use shutil.copytree(str(src)) to avoid importer dependency.
    """
    backup = dest.parent / (dest.name + ".backup") if dest.exists() else None

    if backup is not None:
        dest.rename(backup)

    try:
        _copy_traversable_recursive(src, dest)
    except Exception:
        # Restore from backup on failure
        if backup is not None and backup.exists():
            if dest.exists():
                shutil.rmtree(dest)
            backup.rename(dest)
        raise

    # Success: clean up backup
    if backup is not None and backup.exists():
        shutil.rmtree(backup)


def _copy_traversable_recursive(src: Traversable, dest: Path) -> None:
    """Recursively copy Traversable entries to dest."""
    dest.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        # S-1: Path traversal defense
        if ".." in entry.name or "/" in entry.name or "\\" in entry.name:
            logger.warning("Skipping suspicious entry name: %s", entry.name)
            continue
        target = dest / entry.name
        if not target.resolve().is_relative_to(dest.resolve()):
            logger.warning("Path traversal blocked: %s", entry.name)
            continue
        if entry.is_file():
            target.write_bytes(entry.read_bytes())
        elif entry.is_dir():
            _copy_traversable_recursive(entry, target)


def _write_bundled_update(
    bundled_src: Traversable,
    dest_dir: Path,
    new_version: str | None,
    old_version: str | None,
) -> None:
    """Write .bundled-update.json and copy new skill files to .bundled-update/.

    Catches all write errors gracefully — logs warning, never crashes.
    """
    try:
        skill_name = dest_dir.name
        update_json = dest_dir / ".bundled-update.json"
        update_dir = dest_dir / ".bundled-update"

        data = {
            "from_version": old_version,
            "to_version": new_version,
            "created_at": datetime.now(UTC).isoformat(),
            "message": (
                f"Run: diff .claude/skills/{skill_name}/SKILL.md "
                f".claude/skills/{skill_name}/.bundled-update/SKILL.md"
            ),
        }
        update_json.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Copy new version files to .bundled-update/
        if update_dir.exists():
            shutil.rmtree(update_dir)
        _copy_traversable_recursive(bundled_src, update_dir)

    except OSError as exc:
        logger.warning(
            "Failed to write bundled update for '%s': %s", dest_dir.name, exc
        )


def _copy_skills_template(project_path: Path) -> None:
    """Copy bundled _skills/ to .claude/skills/ with version-aware updates.

    Decision cases:
      1. Fresh copy (dest absent) -> copy + save state
      2. Same version or downgrade -> skip
      3. Upgrade, unmodified -> auto-update
      4. Upgrade, customized -> skip + warning + .bundled-update
      5. No version, dest exists -> skip (legacy)
      6. No version, dest absent -> fresh copy (legacy)
    """
    pkg_files = importlib.resources.files("insight_blueprint")

    for skill_name in _discover_bundled_skills():
        bundled_src = pkg_files / "_skills" / skill_name
        dest = project_path / ".claude" / "skills" / skill_name

        # Read bundled version from Traversable
        bundled_version = _get_skill_version_from_traversable(bundled_src / "SKILL.md")
        bundled_hash = _hash_skill_directory_from_traversable(bundled_src)

        if not dest.exists():
            # Case 1 / Case 6: Fresh copy
            dest.parent.mkdir(parents=True, exist_ok=True)
            _copy_skill_tree(bundled_src, dest)
            _save_skill_state(dest, bundled_version, bundled_hash)
            logger.info("Skill '%s' installed (v%s)", skill_name, bundled_version)
            continue

        state = _load_skill_state(dest)
        installed_version = state.get("installed_version")

        # Version comparison (only when both versions are present)
        if bundled_version and installed_version:
            try:
                if Version(bundled_version) <= Version(installed_version):
                    # Case 2: Same version or downgrade -> skip
                    continue
            except InvalidVersion:
                pass

        # No version on bundled side, dest already exists -> legacy skip
        if not bundled_version:
            continue

        # Bundled is newer -> check for user customization
        installed_hash = _hash_skill_directory(dest, exclude_managed=True)
        prev_bundled_hash = state.get("installed_bundled_hash")

        if prev_bundled_hash and installed_hash == prev_bundled_hash:
            # Case 3: Unmodified -> auto-update
            _copy_skill_tree(bundled_src, dest)
            _save_skill_state(dest, bundled_version, bundled_hash)
            logger.info("Skill '%s' updated to v%s", skill_name, bundled_version)
        else:
            # Case 4: Customized -> skip + notification
            logger.warning(
                "Skill '%s' v%s available but customized, skipped. "
                "See .bundled-update/ for new version.",
                skill_name,
                bundled_version,
            )
            _write_bundled_update(bundled_src, dest, bundled_version, installed_version)


def _get_skill_version_from_traversable(skill_md: Traversable) -> str | None:
    """Parse version from a Traversable SKILL.md (bundled, not on disk)."""
    try:
        content = skill_md.read_text(encoding="utf-8")
    except (OSError, AttributeError):
        return None

    return _parse_version_from_content(content)


def _hash_skill_directory_from_traversable(src: Traversable) -> str:
    """Compute SHA-256 hash over a Traversable directory (bundled skills)."""
    entries: list[tuple[str, bytes]] = []
    _collect_traversable_entries(src, "", entries)
    return _hash_entries(entries)


def _collect_traversable_entries(
    src: Traversable, prefix: str, entries: list[tuple[str, bytes]]
) -> None:
    """Recursively collect (relative_path, content) from Traversable."""
    for entry in src.iterdir():
        rel = f"{prefix}/{entry.name}" if prefix else entry.name
        if entry.is_file():
            entries.append((rel, entry.read_bytes()))
        elif entry.is_dir():
            _collect_traversable_entries(entry, rel, entries)


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
