"""Tests for CLAUDE.md generation and .claude/rules/ template copy."""

import json
from pathlib import Path

from insight_blueprint.storage.project import (
    _CLAUDE_MD_BEGIN,
    _CLAUDE_MD_END,
    _copy_rules_template,
    _generate_claude_md,
    _load_claude_md_state,
    init_project,
)

# === _generate_claude_md tests ===


def test_generate_claude_md_fresh_creation(tmp_path: Path) -> None:
    """CLAUDE.md is created when absent."""
    _generate_claude_md(tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists()
    content = claude_md.read_text()
    assert _CLAUDE_MD_BEGIN in content
    assert _CLAUDE_MD_END in content
    assert "insight-blueprint" in content


def test_generate_claude_md_append_to_existing(tmp_path: Path) -> None:
    """Managed section is appended when CLAUDE.md exists without markers."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# My Project\n\nExisting content.\n")

    _generate_claude_md(tmp_path)

    content = claude_md.read_text()
    assert content.startswith("# My Project\n\nExisting content.\n")
    assert _CLAUDE_MD_BEGIN in content
    assert _CLAUDE_MD_END in content


def test_generate_claude_md_replace_between_markers(tmp_path: Path) -> None:
    """Managed section is replaced when markers already exist."""
    claude_md = tmp_path / "CLAUDE.md"
    original = (
        "# My Project\n\n"
        f"{_CLAUDE_MD_BEGIN}\nOLD CONTENT\n{_CLAUDE_MD_END}\n\n"
        "## My Custom Section\n"
    )
    claude_md.write_text(original)

    _generate_claude_md(tmp_path)

    content = claude_md.read_text()
    assert "OLD CONTENT" not in content
    assert "insight-blueprint" in content
    assert "## My Custom Section" in content


def test_generate_claude_md_preserves_user_content(tmp_path: Path) -> None:
    """User content outside markers is not modified."""
    claude_md = tmp_path / "CLAUDE.md"
    original = (
        "# Project Title\n\n"
        "User instructions here.\n\n"
        f"{_CLAUDE_MD_BEGIN}\nold stuff\n{_CLAUDE_MD_END}\n\n"
        "More user notes.\n"
    )
    claude_md.write_text(original)

    _generate_claude_md(tmp_path)

    content = claude_md.read_text()
    assert "# Project Title" in content
    assert "User instructions here." in content
    assert "More user notes." in content


def test_generate_claude_md_skips_when_unchanged(tmp_path: Path) -> None:
    """No rewrite when content hash matches."""
    _generate_claude_md(tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    mtime_before = claude_md.stat().st_mtime_ns

    # Run again — should skip
    _generate_claude_md(tmp_path)

    mtime_after = claude_md.stat().st_mtime_ns
    assert mtime_before == mtime_after


def test_generate_claude_md_saves_state(tmp_path: Path) -> None:
    """State file is created with hash."""
    _generate_claude_md(tmp_path)

    state = _load_claude_md_state(tmp_path)
    assert "claude_md" in state
    assert isinstance(state["claude_md"], str)
    assert len(state["claude_md"]) == 64  # SHA-256 hex


# === _copy_rules_template tests ===


def test_copy_rules_fresh_install(tmp_path: Path) -> None:
    """Rules are copied to .claude/rules/ when absent."""
    (tmp_path / ".claude").mkdir()
    _copy_rules_template(tmp_path)

    rules_dir = tmp_path / ".claude" / "rules"
    assert (rules_dir / "insight-yaml.md").exists()
    assert (rules_dir / "analysis-workflow.md").exists()
    assert (rules_dir / "catalog-workflow.md").exists()


def test_copy_rules_content_has_frontmatter(tmp_path: Path) -> None:
    """Copied rules have paths frontmatter."""
    (tmp_path / ".claude").mkdir()
    _copy_rules_template(tmp_path)

    content = (tmp_path / ".claude" / "rules" / "insight-yaml.md").read_text()
    assert "---" in content
    assert "paths:" in content
    assert ".insight/**/*.yaml" in content


def test_copy_rules_skip_same_version(tmp_path: Path) -> None:
    """Rules are not overwritten when version matches."""
    (tmp_path / ".claude").mkdir()
    _copy_rules_template(tmp_path)

    rules_dir = tmp_path / ".claude" / "rules"
    rule_file = rules_dir / "insight-yaml.md"
    mtime_before = rule_file.stat().st_mtime_ns

    # Run again — same version, should skip
    _copy_rules_template(tmp_path)

    mtime_after = rule_file.stat().st_mtime_ns
    assert mtime_before == mtime_after


def test_copy_rules_preserves_customized(tmp_path: Path) -> None:
    """Customized rule files are not overwritten."""
    (tmp_path / ".claude").mkdir()
    _copy_rules_template(tmp_path)

    # Customize a rule
    rule_file = tmp_path / ".claude" / "rules" / "insight-yaml.md"
    rule_file.write_text('---\nversion: "1.0.0"\npaths:\n  - custom\n---\n# Custom\n')

    # Bump the state to simulate an upgrade scenario
    state = _load_claude_md_state(tmp_path)
    if "rules" in state and "insight-yaml.md" in state["rules"]:
        state["rules"]["insight-yaml.md"]["installed_version"] = "0.9.0"
        state_file = tmp_path / ".claude" / ".insight-blueprint-state.json"
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    _copy_rules_template(tmp_path)

    # Custom content should be preserved
    content = rule_file.read_text()
    assert "# Custom" in content

    # Bundled update file should exist
    update_file = tmp_path / ".claude" / "rules" / ".bundled-update.insight-yaml.md"
    assert update_file.exists()


def test_copy_rules_saves_state(tmp_path: Path) -> None:
    """State tracks installed rule versions."""
    (tmp_path / ".claude").mkdir()
    _copy_rules_template(tmp_path)

    state = _load_claude_md_state(tmp_path)
    assert "rules" in state
    rules_state = state["rules"]
    assert "insight-yaml.md" in rules_state
    assert rules_state["insight-yaml.md"]["installed_version"] == "1.0.0"


# === Integration test: init_project generates CLAUDE.md and rules ===


def test_init_project_generates_claude_md(tmp_path: Path) -> None:
    """init_project() creates CLAUDE.md."""
    init_project(tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists()
    content = claude_md.read_text()
    assert _CLAUDE_MD_BEGIN in content


def test_init_project_generates_rules(tmp_path: Path) -> None:
    """init_project() creates .claude/rules/."""
    init_project(tmp_path)

    rules_dir = tmp_path / ".claude" / "rules"
    assert (rules_dir / "insight-yaml.md").exists()
    assert (rules_dir / "analysis-workflow.md").exists()
    assert (rules_dir / "catalog-workflow.md").exists()
