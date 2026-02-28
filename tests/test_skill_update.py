"""Tests for the version-aware skill update engine in storage/project.py.

Test IDs U1-U33 map to the test-design.md specification.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from skill_helpers import make_traversable

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    """Create a minimal skill directory with SKILL.md."""
    skill = tmp_path / "test-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        '---\nname: test-skill\nversion: "1.0.0"\n'
        "description: Test skill\n---\n# Test Skill\n"
    )
    return skill


@pytest.fixture
def bundled_skills_dir(tmp_path: Path) -> Path:
    """Create a mock _skills/ directory with multiple skills."""
    skills = tmp_path / "_skills"
    for name in ["alpha", "beta"]:
        d = skills / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f'---\nname: {name}\nversion: "1.0.0"\n'
            f"description: {name} skill\n---\n# {name}\n"
        )
    return skills


# ===========================================================================
# U1-U4: _discover_bundled_skills()
# ===========================================================================


class TestDiscoverBundledSkills:
    """Tests for _discover_bundled_skills()."""

    def test_u1_discover_with_multiple_skills(self, bundled_skills_dir: Path) -> None:
        """U1: Returns sorted list of dir names that contain SKILL.md."""
        from insight_blueprint.storage.project import _discover_bundled_skills

        fake_pkg = make_traversable(bundled_skills_dir.parent)
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            result = _discover_bundled_skills()

        assert result == ["alpha", "beta"]

    def test_u2_discover_empty_skills_dir(self, tmp_path: Path) -> None:
        """U2: Empty _skills/ returns []."""
        from insight_blueprint.storage.project import _discover_bundled_skills

        skills = tmp_path / "_skills"
        skills.mkdir()
        fake_pkg = make_traversable(tmp_path)
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            result = _discover_bundled_skills()

        assert result == []

    def test_u3_discover_skips_dir_without_skill_md(
        self, bundled_skills_dir: Path
    ) -> None:
        """U3: Directory without SKILL.md is excluded."""
        from insight_blueprint.storage.project import _discover_bundled_skills

        # Add a dir without SKILL.md
        no_skill = bundled_skills_dir / "no-skill"
        no_skill.mkdir()
        (no_skill / "README.md").write_text("# Not a skill")

        fake_pkg = make_traversable(bundled_skills_dir.parent)
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            result = _discover_bundled_skills()

        assert "no-skill" not in result
        assert result == ["alpha", "beta"]

    def test_u4_discover_skips_files(self, bundled_skills_dir: Path) -> None:
        """U4: Files (not dirs) directly in _skills/ are excluded."""
        from insight_blueprint.storage.project import _discover_bundled_skills

        # Add a file directly in _skills/
        (bundled_skills_dir / "README.md").write_text("# Skills README")

        fake_pkg = make_traversable(bundled_skills_dir.parent)
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            result = _discover_bundled_skills()

        assert result == ["alpha", "beta"]


# ===========================================================================
# U5-U9: _get_skill_version()
# ===========================================================================


class TestGetSkillVersion:
    """Tests for _get_skill_version()."""

    def test_u5_version_valid_semver(self, tmp_path: Path) -> None:
        """U5: Returns version string for valid semver."""
        from insight_blueprint.storage.project import _get_skill_version

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            '---\nname: test\nversion: "1.2.3"\ndescription: x\n---\n# Test\n'
        )
        assert _get_skill_version(skill_md) == "1.2.3"

    def test_u6_version_missing_field(self, tmp_path: Path) -> None:
        """U6: Returns None when version field is absent."""
        from insight_blueprint.storage.project import _get_skill_version

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\ndescription: x\n---\n# Test\n")
        assert _get_skill_version(skill_md) is None

    def test_u7_version_invalid_frontmatter(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """U7: Returns None + warning on broken frontmatter."""
        from insight_blueprint.storage.project import _get_skill_version

        skill_md = tmp_path / "SKILL.md"
        # Broken: no closing ---
        skill_md.write_text("---\nname: test\nversion: 1.0.0\n# No closing delimiter\n")

        with caplog.at_level(logging.WARNING):
            result = _get_skill_version(skill_md)

        assert result is None
        assert any("frontmatter" in r.message.lower() for r in caplog.records)

    def test_u8_version_invalid_semver(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """U8: Returns None + warning for invalid semver like 'latest'."""
        from insight_blueprint.storage.project import _get_skill_version

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            '---\nname: test\nversion: "latest"\ndescription: x\n---\n# Test\n'
        )

        with caplog.at_level(logging.WARNING):
            result = _get_skill_version(skill_md)

        assert result is None
        assert any("version" in r.message.lower() for r in caplog.records)

    def test_u9_version_no_quotes(self, tmp_path: Path) -> None:
        """U9: YAML float coercion (version: 1.0.0 without quotes) handled."""
        from insight_blueprint.storage.project import _get_skill_version

        skill_md = tmp_path / "SKILL.md"
        # version: 1.0.0 without quotes — YAML would parse as float 1.0
        # but our string parser should extract "1.0.0" correctly
        skill_md.write_text(
            "---\nname: test\nversion: 1.0.0\ndescription: x\n---\n# Test\n"
        )
        result = _get_skill_version(skill_md)
        assert result == "1.0.0"


# ===========================================================================
# U10-U15: _hash_skill_directory()
# ===========================================================================


class TestHashSkillDirectory:
    """Tests for _hash_skill_directory()."""

    def test_u10_hash_deterministic(self, skill_dir: Path) -> None:
        """U10: Same directory contents produce same hash on repeated calls."""
        from insight_blueprint.storage.project import _hash_skill_directory

        h1 = _hash_skill_directory(skill_dir)
        h2 = _hash_skill_directory(skill_dir)
        assert h1 == h2
        assert isinstance(h1, str)
        assert len(h1) == 64  # SHA-256 hex digest

    def test_u11_hash_changes_on_edit(self, skill_dir: Path) -> None:
        """U11: Modifying file content changes the hash."""
        from insight_blueprint.storage.project import _hash_skill_directory

        h_before = _hash_skill_directory(skill_dir)
        (skill_dir / "SKILL.md").write_text("---\nname: changed\n---\n# Changed\n")
        h_after = _hash_skill_directory(skill_dir)
        assert h_before != h_after

    def test_u12_hash_excludes_managed_files(self, skill_dir: Path) -> None:
        """U12: .insight-blueprint-state.json excluded with exclude_managed=True."""
        from insight_blueprint.storage.project import _hash_skill_directory

        h_before = _hash_skill_directory(skill_dir, exclude_managed=True)
        # Add managed file
        (skill_dir / ".insight-blueprint-state.json").write_text('{"v": "1.0.0"}')
        h_after = _hash_skill_directory(skill_dir, exclude_managed=True)
        assert h_before == h_after

        # Without exclude_managed, hash should change
        h_with_managed = _hash_skill_directory(skill_dir, exclude_managed=False)
        assert h_with_managed != h_before

    def test_u13_hash_excludes_bundled_update(self, skill_dir: Path) -> None:
        """U13: .bundled-update.json and .bundled-update/ excluded with exclude_managed."""
        from insight_blueprint.storage.project import _hash_skill_directory

        h_before = _hash_skill_directory(skill_dir, exclude_managed=True)
        # Add bundled-update files
        (skill_dir / ".bundled-update.json").write_text('{"from": "1.0.0"}')
        bundled_dir = skill_dir / ".bundled-update"
        bundled_dir.mkdir()
        (bundled_dir / "SKILL.md").write_text("new content")
        h_after = _hash_skill_directory(skill_dir, exclude_managed=True)
        assert h_before == h_after

    def test_u14_hash_normalizes_line_endings(self, tmp_path: Path) -> None:
        """U14: LF and CRLF produce the same hash."""
        from insight_blueprint.storage.project import _hash_skill_directory

        dir_lf = tmp_path / "lf"
        dir_lf.mkdir()
        (dir_lf / "SKILL.md").write_bytes(b"line1\nline2\n")

        dir_crlf = tmp_path / "crlf"
        dir_crlf.mkdir()
        (dir_crlf / "SKILL.md").write_bytes(b"line1\r\nline2\r\n")

        assert _hash_skill_directory(dir_lf) == _hash_skill_directory(dir_crlf)

    def test_u15_hash_includes_subdirectory(self, skill_dir: Path) -> None:
        """U15: Files in subdirectories are included in the hash."""
        from insight_blueprint.storage.project import _hash_skill_directory

        h_before = _hash_skill_directory(skill_dir)
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "foo.md").write_text("# Reference\n")
        h_after = _hash_skill_directory(skill_dir)
        assert h_before != h_after


# ===========================================================================
# U16-U19: _load_skill_state() / _save_skill_state()
# ===========================================================================


class TestSkillState:
    """Tests for _load_skill_state() and _save_skill_state()."""

    def test_u16_save_and_load_roundtrip(self, skill_dir: Path) -> None:
        """U16: Save state then load — all fields match."""
        from insight_blueprint.storage.project import (
            _load_skill_state,
            _save_skill_state,
        )

        _save_skill_state(skill_dir, "1.0.0", "abc123hash")
        state = _load_skill_state(skill_dir)
        assert state["installed_version"] == "1.0.0"
        assert state["installed_bundled_hash"] == "abc123hash"
        assert "updated_at" in state

    def test_u17_load_missing_state(self, skill_dir: Path) -> None:
        """U17: Missing state file returns empty dict."""
        from insight_blueprint.storage.project import _load_skill_state

        state = _load_skill_state(skill_dir)
        assert state == {}

    def test_u18_load_invalid_json(
        self, skill_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """U18: Corrupt JSON returns empty dict + warning."""
        from insight_blueprint.storage.project import _load_skill_state

        state_file = skill_dir / ".insight-blueprint-state.json"
        state_file.write_text("{invalid json!!")

        with caplog.at_level(logging.WARNING):
            state = _load_skill_state(skill_dir)

        assert state == {}
        assert len(caplog.records) > 0

    def test_u19_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """U19: Save works even if skill dir already exists (file absent)."""
        from insight_blueprint.storage.project import (
            _load_skill_state,
            _save_skill_state,
        )

        skill = tmp_path / "new-skill"
        skill.mkdir()
        _save_skill_state(skill, "2.0.0", "xyz789")
        state = _load_skill_state(skill)
        assert state["installed_version"] == "2.0.0"


# ===========================================================================
# U20-U23: _copy_skill_tree()
# ===========================================================================


class TestCopySkillTree:
    """Tests for _copy_skill_tree()."""

    def test_u20_copy_single_file(self, tmp_path: Path) -> None:
        """U20: Copy Traversable with SKILL.md only."""
        from insight_blueprint.storage.project import _copy_skill_tree

        src_dir = tmp_path / "src-skill"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# My Skill\n")

        dest = tmp_path / "dest-skill"
        _copy_skill_tree(make_traversable(src_dir), dest)

        assert (dest / "SKILL.md").exists()
        assert (dest / "SKILL.md").read_text() == "# My Skill\n"

    def test_u21_copy_with_subdirectory(self, tmp_path: Path) -> None:
        """U21: Traversable with SKILL.md + references/foo.md."""
        from insight_blueprint.storage.project import _copy_skill_tree

        src_dir = tmp_path / "src-skill"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# Skill\n")
        refs = src_dir / "references"
        refs.mkdir()
        (refs / "foo.md").write_text("# Reference\n")

        dest = tmp_path / "dest-skill"
        _copy_skill_tree(make_traversable(src_dir), dest)

        assert (dest / "SKILL.md").exists()
        assert (dest / "references" / "foo.md").exists()
        assert (dest / "references" / "foo.md").read_text() == "# Reference\n"

    def test_u22_copy_overwrites_existing(self, tmp_path: Path) -> None:
        """U22: Pre-existing dest/SKILL.md is overwritten with new content."""
        from insight_blueprint.storage.project import _copy_skill_tree

        src_dir = tmp_path / "src-skill"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# New Content\n")

        dest = tmp_path / "dest-skill"
        dest.mkdir()
        (dest / "SKILL.md").write_text("# Old Content\n")

        _copy_skill_tree(make_traversable(src_dir), dest)

        assert (dest / "SKILL.md").read_text() == "# New Content\n"

    def test_u23_copy_atomic_backup_restore(self, tmp_path: Path) -> None:
        """U23: On failure mid-copy, original files are restored from .backup."""
        from unittest.mock import patch as mock_patch

        from insight_blueprint.storage.project import _copy_skill_tree

        src_dir = tmp_path / "src-skill"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# New\n")
        (src_dir / "extra.md").write_text("# Extra\n")

        dest = tmp_path / "dest-skill"
        dest.mkdir()
        (dest / "SKILL.md").write_text("# Original\n")

        # Patch Path.write_bytes to fail on second file write
        original_write_bytes = Path.write_bytes
        call_count = 0

        def failing_write_bytes(self_path, data):  # noqa: ANN001, ANN201
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise OSError("Disk full")
            return original_write_bytes(self_path, data)

        with mock_patch.object(Path, "write_bytes", failing_write_bytes):
            with pytest.raises(OSError, match="Disk full"):
                _copy_skill_tree(make_traversable(src_dir), dest)

        # Original should be restored
        assert dest.exists()
        assert (dest / "SKILL.md").read_text() == "# Original\n"


# ===========================================================================
# U24-U26: _write_bundled_update()
# ===========================================================================


class TestWriteBundledUpdate:
    """Tests for _write_bundled_update()."""

    def test_u24_write_creates_json_and_dir(self, tmp_path: Path) -> None:
        """U24: Creates .bundled-update.json and .bundled-update/ dir."""
        import json

        from insight_blueprint.storage.project import _write_bundled_update

        src_dir = tmp_path / "bundled-skill"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# New Skill v1.1.0\n")

        dest = tmp_path / "installed-skill"
        dest.mkdir()
        (dest / "SKILL.md").write_text("# Old Skill v1.0.0\n")

        _write_bundled_update(make_traversable(src_dir), dest, "1.1.0", "1.0.0")

        update_json = dest / ".bundled-update.json"
        assert update_json.exists()
        data = json.loads(update_json.read_text())
        assert "from_version" in data
        assert "to_version" in data
        assert "created_at" in data
        assert "message" in data

        update_dir = dest / ".bundled-update"
        assert update_dir.is_dir()
        assert (update_dir / "SKILL.md").exists()
        assert (update_dir / "SKILL.md").read_text() == "# New Skill v1.1.0\n"

    def test_u25_write_includes_diff_message(self, tmp_path: Path) -> None:
        """U25: JSON includes from_version, to_version, diff command."""
        import json

        from insight_blueprint.storage.project import _write_bundled_update

        src_dir = tmp_path / "bundled"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# New\n")

        dest = tmp_path / "installed"
        dest.mkdir()

        _write_bundled_update(make_traversable(src_dir), dest, "1.1.0", "1.0.0")

        data = json.loads((dest / ".bundled-update.json").read_text())
        assert data["from_version"] == "1.0.0"
        assert data["to_version"] == "1.1.0"
        assert "diff" in data["message"].lower()

    def test_u26_write_permission_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """U26: Permission error is caught, warning logged, no crash."""
        from insight_blueprint.storage.project import _write_bundled_update

        src_dir = tmp_path / "bundled"
        src_dir.mkdir()
        (src_dir / "SKILL.md").write_text("# New\n")

        dest = tmp_path / "readonly"
        dest.mkdir()

        # Make dest read-only
        dest.chmod(0o444)

        with caplog.at_level(logging.WARNING):
            # Should not raise
            _write_bundled_update(make_traversable(src_dir), dest, "1.1.0", "1.0.0")

        # Restore permissions for cleanup
        dest.chmod(0o755)

        assert len(caplog.records) > 0


# ===========================================================================
# U27-U33: _copy_skills_template() — Decision Logic
# ===========================================================================


def _setup_bundled_skill(
    tmp_path: Path,
    name: str,
    version: str | None = "1.0.0",
    content: str = "# Bundled\n",
) -> Path:
    """Create a bundled skill directory under _skills/."""
    skills = tmp_path / "_skills"
    skill = skills / name
    skill.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\nname: {name}\n"
    if version is not None:
        frontmatter += f'version: "{version}"\n'
    frontmatter += f"description: {name} skill\n---\n{content}"
    (skill / "SKILL.md").write_text(frontmatter)
    return skills


class TestCopySkillsTemplate:
    """Tests for _copy_skills_template() version-aware decision logic."""

    def _patch_and_call(self, tmp_path: Path, project_path: Path) -> None:
        """Patch importlib.resources.files and call _copy_skills_template."""
        from insight_blueprint.storage.project import _copy_skills_template

        fake_pkg = make_traversable(tmp_path)
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            _copy_skills_template(project_path)

    def test_u27_case1_fresh_copy(self, tmp_path: Path) -> None:
        """U27: dest does not exist -> skill copied + state saved."""
        import json

        project = tmp_path / "project"
        project.mkdir()
        _setup_bundled_skill(tmp_path, "alpha", "1.0.0")

        self._patch_and_call(tmp_path, project)

        dest = project / ".claude" / "skills" / "alpha"
        assert dest.exists()
        assert (dest / "SKILL.md").exists()
        state_file = dest / ".insight-blueprint-state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["installed_version"] == "1.0.0"

    def test_u28_case2_same_version_skip(self, tmp_path: Path) -> None:
        """U28: bundled v1.0.0, installed v1.0.0 -> no copy, no change."""
        project = tmp_path / "project"
        project.mkdir()
        _setup_bundled_skill(tmp_path, "alpha", "1.0.0")

        # First copy
        self._patch_and_call(tmp_path, project)
        dest = project / ".claude" / "skills" / "alpha"
        original_content = (dest / "SKILL.md").read_text()

        # Modify SKILL.md slightly to detect if it gets overwritten
        (dest / "SKILL.md").write_text(original_content + "\n# user edit\n")

        # Second copy with same version
        self._patch_and_call(tmp_path, project)

        # User edit should be preserved (no overwrite)
        assert "# user edit" in (dest / "SKILL.md").read_text()

    def test_u29_case3_upgrade_unmodified(self, tmp_path: Path) -> None:
        """U29: bundled v1.1.0, installed v1.0.0, hash matches -> updated."""
        import json

        project = tmp_path / "project"
        project.mkdir()
        _setup_bundled_skill(tmp_path, "alpha", "1.0.0")

        # First copy
        self._patch_and_call(tmp_path, project)
        dest = project / ".claude" / "skills" / "alpha"

        # Upgrade bundled to v1.1.0
        _setup_bundled_skill(tmp_path, "alpha", "1.1.0", "# Upgraded\n")

        # Second copy — should auto-update
        self._patch_and_call(tmp_path, project)

        state = json.loads((dest / ".insight-blueprint-state.json").read_text())
        assert state["installed_version"] == "1.1.0"
        assert "Upgraded" in (dest / "SKILL.md").read_text()

    def test_u30_case4_upgrade_customized(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """U30: bundled v1.1.0, installed v1.0.0, hash differs -> skip + .bundled-update."""
        project = tmp_path / "project"
        project.mkdir()
        _setup_bundled_skill(tmp_path, "alpha", "1.0.0")

        # First copy
        self._patch_and_call(tmp_path, project)
        dest = project / ".claude" / "skills" / "alpha"

        # User customizes the skill
        (dest / "SKILL.md").write_text("# My Custom Skill\n")

        # Upgrade bundled to v1.1.0
        _setup_bundled_skill(tmp_path, "alpha", "1.1.0", "# Upgraded\n")

        with caplog.at_level(logging.WARNING):
            self._patch_and_call(tmp_path, project)

        # User customization preserved
        assert "My Custom Skill" in (dest / "SKILL.md").read_text()
        # .bundled-update written
        assert (dest / ".bundled-update.json").exists()
        assert (dest / ".bundled-update" / "SKILL.md").exists()
        # Warning logged
        assert any(
            "customized" in r.message.lower() or "skip" in r.message.lower()
            for r in caplog.records
        )

    def test_u31_case5_downgrade_skip(self, tmp_path: Path) -> None:
        """U31: bundled v0.9.0, installed v1.0.0 -> no copy."""
        import json

        project = tmp_path / "project"
        project.mkdir()
        _setup_bundled_skill(tmp_path, "alpha", "1.0.0")

        # First copy
        self._patch_and_call(tmp_path, project)
        dest = project / ".claude" / "skills" / "alpha"

        # Downgrade bundled to v0.9.0
        _setup_bundled_skill(tmp_path, "alpha", "0.9.0", "# Old\n")

        self._patch_and_call(tmp_path, project)

        # Should still be v1.0.0
        state = json.loads((dest / ".insight-blueprint-state.json").read_text())
        assert state["installed_version"] == "1.0.0"

    def test_u32_case6_no_version_legacy(self, tmp_path: Path) -> None:
        """U32: bundled has no version, dest exists -> skip (legacy behavior)."""
        project = tmp_path / "project"
        project.mkdir()

        # Create dest manually (simulating legacy install)
        dest = project / ".claude" / "skills" / "alpha"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("# Legacy Skill\n")

        # Bundled has no version
        _setup_bundled_skill(tmp_path, "alpha", version=None)

        self._patch_and_call(tmp_path, project)

        # Legacy content preserved
        assert "Legacy Skill" in (dest / "SKILL.md").read_text()

    def test_u33_case7_no_version_fresh(self, tmp_path: Path) -> None:
        """U33: bundled has no version, dest absent -> fresh copy."""
        project = tmp_path / "project"
        project.mkdir()

        # Bundled has no version
        _setup_bundled_skill(tmp_path, "alpha", version=None)

        self._patch_and_call(tmp_path, project)

        dest = project / ".claude" / "skills" / "alpha"
        assert dest.exists()
        assert (dest / "SKILL.md").exists()

    def test_g8_invalid_version_in_installed_state(self, tmp_path: Path) -> None:
        """G8: InvalidVersion in installed state -> fallthrough, treat as upgrade."""
        import json

        project = tmp_path / "project"
        project.mkdir()
        _setup_bundled_skill(tmp_path, "alpha", "1.0.0")

        # First copy
        self._patch_and_call(tmp_path, project)
        dest = project / ".claude" / "skills" / "alpha"

        # Corrupt installed_version to non-semver
        state_file = dest / ".insight-blueprint-state.json"
        state = json.loads(state_file.read_text())
        state["installed_version"] = "not-a-version"
        state_file.write_text(json.dumps(state))

        # Upgrade bundled to v1.1.0
        _setup_bundled_skill(tmp_path, "alpha", "1.1.0", "# Upgraded\n")

        # Should not crash — InvalidVersion caught, falls through to hash check
        self._patch_and_call(tmp_path, project)

        # Since hash matches (unmodified), should auto-update
        new_state = json.loads(state_file.read_text())
        assert new_state["installed_version"] == "1.1.0"


# ===========================================================================
# G1-G9: Error Path Tests (from review gaps)
# ===========================================================================


class TestGetSkillVersionFromTraversable:
    """G1-G3: Direct tests for _get_skill_version_from_traversable error paths."""

    def test_g1_traversable_read_error(self, tmp_path: Path) -> None:
        """G1: OSError/AttributeError on read_text returns None."""
        from insight_blueprint.storage.project import (
            _get_skill_version_from_traversable,
        )

        class _BrokenTraversable:
            def read_text(self, encoding: str = "utf-8") -> str:
                raise OSError("Permission denied")

        result = _get_skill_version_from_traversable(_BrokenTraversable())
        assert result is None

    def test_g1b_traversable_attribute_error(self) -> None:
        """G1b: AttributeError on read_text returns None."""
        from insight_blueprint.storage.project import (
            _get_skill_version_from_traversable,
        )

        class _NoReadTraversable:
            def read_text(self, encoding: str = "utf-8") -> str:
                raise AttributeError("no read_text")

        result = _get_skill_version_from_traversable(_NoReadTraversable())
        assert result is None

    def test_g2_traversable_invalid_frontmatter(self, tmp_path: Path) -> None:
        """G2: Invalid frontmatter (no closing ---) returns None."""
        from insight_blueprint.storage.project import (
            _get_skill_version_from_traversable,
        )

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\nversion: 1.0.0\n# No closing\n")
        fake = make_traversable(tmp_path) / "SKILL.md"
        result = _get_skill_version_from_traversable(fake)
        assert result is None

    def test_g3_traversable_invalid_version(self, tmp_path: Path) -> None:
        """G3: Invalid semver in Traversable returns None."""
        from insight_blueprint.storage.project import (
            _get_skill_version_from_traversable,
        )

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            '---\nname: test\nversion: "latest"\ndescription: x\n---\n# Test\n'
        )
        fake = make_traversable(tmp_path) / "SKILL.md"
        result = _get_skill_version_from_traversable(fake)
        assert result is None


class TestDiscoverBundledSkillsEdgeCases:
    """G4-G5: Edge cases for _discover_bundled_skills."""

    def test_g4_skills_dir_not_existing(self) -> None:
        """G4: _skills/ does not exist -> returns []."""
        from insight_blueprint.storage.project import _discover_bundled_skills

        class _EmptyTraversable:
            def __truediv__(self, other: str) -> "_EmptyTraversable":
                return _EmptyTraversable()

            def iterdir(self):  # noqa: ANN201
                raise FileNotFoundError("_skills not found")

        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=_EmptyTraversable(),
        ):
            result = _discover_bundled_skills()
        assert result == []

    def test_g5_broken_traversable_entry(self, bundled_skills_dir: Path) -> None:
        """G5: AttributeError on is_file() is caught, skill skipped."""
        from insight_blueprint.storage.project import _discover_bundled_skills

        # Add a skill directory where SKILL.md raises on is_file()
        broken = bundled_skills_dir / "broken"
        broken.mkdir()
        (broken / "SKILL.md").write_text("---\nname: broken\n---\n# Broken\n")

        class _PartiallyBrokenTraversable:
            """Traversable that breaks on is_file for one specific entry."""

            def __init__(self, path: Path) -> None:
                self._path = path

            @property
            def name(self) -> str:
                return self._path.name

            def is_file(self) -> bool:
                return self._path.is_file()

            def is_dir(self) -> bool:
                return self._path.is_dir()

            def iterdir(self):  # noqa: ANN201
                for child in sorted(self._path.iterdir()):
                    yield _PartiallyBrokenTraversable(child)

            def __truediv__(self, other: str) -> "_PartiallyBrokenTraversable":
                child = _PartiallyBrokenTraversable(self._path / other)
                # Make broken/SKILL.md raise TypeError on is_file
                if self._path.name == "broken" and other == "SKILL.md":

                    class _Broken:
                        def is_file(self) -> bool:
                            raise TypeError("broken traversable")

                    return _Broken()  # type: ignore[return-value]
                return child

        fake_pkg = _PartiallyBrokenTraversable(bundled_skills_dir.parent)
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            result = _discover_bundled_skills()

        # alpha and beta should still be found, broken should be skipped
        assert "alpha" in result
        assert "beta" in result
        assert "broken" not in result


class TestGetSkillVersionOSError:
    """G6: _get_skill_version with unreadable file."""

    def test_g6_unreadable_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """G6: PermissionError on read_text -> None + warning."""
        from insight_blueprint.storage.project import _get_skill_version

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nversion: 1.0.0\n---\n")
        skill_md.chmod(0o000)

        with caplog.at_level(logging.WARNING):
            result = _get_skill_version(skill_md)

        skill_md.chmod(0o644)  # Restore for cleanup
        assert result is None
        assert any("cannot read" in r.message.lower() for r in caplog.records)


class TestRegisterMcpServerErrorCleanup:
    """G7: _register_mcp_server atomic write failure cleanup."""

    def test_g7_atomic_write_failure_cleans_tempfile(self, tmp_path: Path) -> None:
        """G7: os.replace failure -> tempfile cleaned up, exception raised."""
        from insight_blueprint.storage.project import _register_mcp_server

        project = tmp_path / "project"
        project.mkdir()

        with patch(
            "insight_blueprint.storage.project.os.replace",
            side_effect=OSError("replace failed"),
        ):
            with pytest.raises(OSError, match="replace failed"):
                _register_mcp_server(project)

        # No leftover .tmp files
        tmp_files = list(project.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestCollectTraversableEntriesNested:
    """G9: _collect_traversable_entries with nested subdirectories."""

    def test_g9_nested_subdirectory(self, tmp_path: Path) -> None:
        """G9: Nested dirs in Traversable are collected recursively."""
        from insight_blueprint.storage.project import (
            _collect_traversable_entries,
        )

        src = tmp_path / "skill"
        src.mkdir()
        (src / "SKILL.md").write_text("# Top level\n")
        refs = src / "references"
        refs.mkdir()
        (refs / "intro.md").write_text("# Intro\n")
        sub = refs / "deep"
        sub.mkdir()
        (sub / "detail.md").write_text("# Detail\n")

        entries: list[tuple[str, bytes]] = []
        _collect_traversable_entries(make_traversable(src), "", entries)

        paths = [e[0] for e in entries]
        assert "SKILL.md" in paths
        assert "references/intro.md" in paths
        assert "references/deep/detail.md" in paths


class TestWriteBundledUpdatePreExisting:
    """G10: _write_bundled_update with pre-existing .bundled-update/ dir."""

    def test_g10_replaces_existing_bundled_update(self, tmp_path: Path) -> None:
        """G10: Second call replaces pre-existing .bundled-update/ dir."""
        from insight_blueprint.storage.project import _write_bundled_update

        src = tmp_path / "bundled"
        src.mkdir()
        (src / "SKILL.md").write_text("# V1.1\n")

        dest = tmp_path / "installed"
        dest.mkdir()

        # First write
        _write_bundled_update(make_traversable(src), dest, "1.1.0", "1.0.0")
        assert (dest / ".bundled-update" / "SKILL.md").read_text() == "# V1.1\n"

        # Change bundled content
        (src / "SKILL.md").write_text("# V1.2\n")

        # Second write — should replace
        _write_bundled_update(make_traversable(src), dest, "1.2.0", "1.0.0")
        assert (dest / ".bundled-update" / "SKILL.md").read_text() == "# V1.2\n"
