"""Integration tests for init_project() skill lifecycle.

Test IDs I1-I6 map to the test-design.md specification.
These tests exercise the full init_project() flow, not individual helpers.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

from skill_helpers import create_fake_package

# ---------------------------------------------------------------------------
# I1: init_copies_all_bundled_skills
# ---------------------------------------------------------------------------


class TestInitCopiesAllBundledSkills:
    """I1: init_project() on empty dir copies all bundled skills."""

    def test_i1_all_skills_copied(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        fake_pkg = create_fake_package(
            pkg_base, {"analysis-design": "1.0.0", "catalog-register": "1.0.0"}
        )

        from insight_blueprint.storage.project import init_project

        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        skills_dir = project / ".claude" / "skills"
        assert (skills_dir / "analysis-design" / "SKILL.md").exists()
        assert (skills_dir / "catalog-register" / "SKILL.md").exists()

        # State files should be present
        assert (
            skills_dir / "analysis-design" / ".insight-blueprint-state.json"
        ).exists()
        assert (
            skills_dir / "catalog-register" / ".insight-blueprint-state.json"
        ).exists()


# ---------------------------------------------------------------------------
# I2: init_idempotent_no_change
# ---------------------------------------------------------------------------


class TestInitIdempotent:
    """I2: init_project() twice with no edits makes no changes."""

    def test_i2_idempotent_no_change(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        fake_pkg = create_fake_package(pkg_base, {"alpha": "1.0.0"})

        from insight_blueprint.storage.project import init_project

        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        dest = project / ".claude" / "skills" / "alpha"
        state_before = (dest / ".insight-blueprint-state.json").read_text()
        content_before = (dest / "SKILL.md").read_text()

        # Second call
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        # Nothing should change
        assert (dest / ".insight-blueprint-state.json").read_text() == state_before
        assert (dest / "SKILL.md").read_text() == content_before


# ---------------------------------------------------------------------------
# I3: init_respects_customization
# ---------------------------------------------------------------------------


class TestInitRespectsCustomization:
    """I3: User edits preserved, .bundled-update written on upgrade."""

    def test_i3_customization_preserved(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        fake_pkg = create_fake_package(pkg_base, {"alpha": "1.0.0"})

        from insight_blueprint.storage.project import init_project

        # Step 1: Initial copy
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        dest = project / ".claude" / "skills" / "alpha"

        # Step 2: User edits SKILL.md
        (dest / "SKILL.md").write_text("# My Custom Workflow\n")

        # Step 3: Bump bundled version
        fake_pkg_v2 = create_fake_package(pkg_base, {"alpha": "1.1.0"})

        # Step 4: Re-init
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg_v2,
        ):
            init_project(project)

        # User edit preserved
        assert "My Custom Workflow" in (dest / "SKILL.md").read_text()

        # .bundled-update written
        assert (dest / ".bundled-update.json").exists()
        update_data = json.loads((dest / ".bundled-update.json").read_text())
        assert update_data["from_version"] == "1.0.0"
        assert update_data["to_version"] == "1.1.0"

        assert (dest / ".bundled-update" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# I4: init_updates_unmodified_skill
# ---------------------------------------------------------------------------


class TestInitUpdatesUnmodified:
    """I4: Unmodified skill auto-updated on version bump."""

    def test_i4_unmodified_updated(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        fake_pkg = create_fake_package(pkg_base, {"alpha": "1.0.0"})

        from insight_blueprint.storage.project import init_project

        # Step 1: Initial copy
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        dest = project / ".claude" / "skills" / "alpha"

        # Step 2: Bump bundled version (no user edits)
        fake_pkg_v2 = create_fake_package(pkg_base, {"alpha": "1.1.0"})

        # Step 3: Re-init
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg_v2,
        ):
            init_project(project)

        # Skill should be updated
        state = json.loads((dest / ".insight-blueprint-state.json").read_text())
        assert state["installed_version"] == "1.1.0"

        # No .bundled-update (not customized)
        assert not (dest / ".bundled-update.json").exists()


# ---------------------------------------------------------------------------
# I5: init_performance
# ---------------------------------------------------------------------------


class TestInitPerformance:
    """I5: init_project() with 10 skills completes within 500ms."""

    def test_i5_performance_10_skills(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        skills = {f"skill-{i:02d}": "1.0.0" for i in range(10)}
        fake_pkg = create_fake_package(pkg_base, skills)

        from insight_blueprint.storage.project import init_project

        start = time.monotonic()
        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)
        elapsed = time.monotonic() - start

        # NFR-1: 10 skills within 500ms
        assert elapsed < 0.5, (
            f"init_project with 10 skills took {elapsed:.3f}s (>500ms)"
        )

        # Verify all skills were actually copied
        skills_dir = project / ".claude" / "skills"
        for i in range(10):
            assert (skills_dir / f"skill-{i:02d}" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# I6: init_no_regression_dirs
# ---------------------------------------------------------------------------


class TestInitNoRegression:
    """I6: init_project() still creates .insight/ dirs and .mcp.json."""

    def test_i6_insight_dirs_created(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        fake_pkg = create_fake_package(pkg_base, {"alpha": "1.0.0"})

        from insight_blueprint.storage.project import init_project

        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        # .insight/ directories
        insight = project / ".insight"
        assert (insight / "designs").is_dir()
        assert (insight / "catalog" / "knowledge").is_dir()
        assert (insight / "catalog" / "sources").is_dir()
        assert (insight / "rules").is_dir()
        assert (insight / ".sqlite").is_dir()

        # Config files
        assert (insight / "config.yaml").exists()
        assert (insight / "rules" / "review_rules.yaml").exists()
        assert (insight / "rules" / "analysis_rules.yaml").exists()
        assert (insight / "rules" / "extracted_knowledge.yaml").exists()

    def test_i6_mcp_json_registered(self, tmp_path: Path) -> None:
        pkg_base = tmp_path / "pkg"
        project = tmp_path / "project"
        project.mkdir()

        fake_pkg = create_fake_package(pkg_base, {"alpha": "1.0.0"})

        from insight_blueprint.storage.project import init_project

        with patch(
            "insight_blueprint.storage.project.importlib.resources.files",
            return_value=fake_pkg,
        ):
            init_project(project)

        mcp_json = project / ".mcp.json"
        assert mcp_json.exists()
        config = json.loads(mcp_json.read_text())
        assert "insight-blueprint" in config["mcpServers"]
