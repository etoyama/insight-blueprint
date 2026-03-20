"""Tests for CLAUDE.md generation and .claude/rules/ template copy."""

from pathlib import Path

from insight_blueprint.storage.project import (
    _CLAUDE_MD_BEGIN,
    _CLAUDE_MD_END,
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


# === Integration test: init_project generates CLAUDE.md ===


def test_init_project_generates_claude_md(tmp_path: Path) -> None:
    """init_project() creates CLAUDE.md."""
    init_project(tmp_path)

    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists()
    content = claude_md.read_text()
    assert _CLAUDE_MD_BEGIN in content
