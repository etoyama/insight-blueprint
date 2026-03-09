"""Tests for scripts/check_tag_version.py (tag-version consistency check)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts.check_tag_version import check_tag_version


def _create_pyproject(tmp_path: Path, version: str = "0.1.0") -> Path:
    """Create a minimal pyproject.toml with the given version."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        f'[project]\nname = "test-package"\nversion = "{version}"\n'
    )
    return pyproject_path


class TestCheckTagVersion:
    """Tests for tag-version consistency checking."""

    def test_matching_tag_and_version(self, tmp_path: Path) -> None:
        """Tag 'v0.1.0' with pyproject version '0.1.0' should pass."""
        pyproject_path = _create_pyproject(tmp_path, "0.1.0")
        ok, message = check_tag_version("v0.1.0", pyproject_path)
        assert ok is True
        assert "match" in message.lower() or "ok" in message.lower()

    def test_mismatched_tag_and_version(self, tmp_path: Path) -> None:
        """Tag 'v0.2.0' with pyproject version '0.1.0' should fail."""
        pyproject_path = _create_pyproject(tmp_path, "0.1.0")
        ok, message = check_tag_version("v0.2.0", pyproject_path)
        assert ok is False
        assert "0.2.0" in message
        assert "0.1.0" in message

    def test_tag_without_v_prefix(self, tmp_path: Path) -> None:
        """Tag '0.1.0' (no 'v' prefix) should fail with guidance."""
        pyproject_path = _create_pyproject(tmp_path, "0.1.0")
        ok, message = check_tag_version("0.1.0", pyproject_path)
        assert ok is False
        assert "v" in message.lower()

    def test_no_tag_provided_and_no_git_tag(self, tmp_path: Path) -> None:
        """When no tag is provided and git has no tag, should fail with guidance."""
        pyproject_path = _create_pyproject(tmp_path, "0.1.0")

        # Mock subprocess.run to simulate 'git describe' failure (no tags)
        with patch("scripts.check_tag_version.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "fatal: no tags"

            ok, message = check_tag_version(None, pyproject_path)
            assert ok is False
            assert "tag" in message.lower()

    def test_no_tag_provided_with_matching_git_tag(self, tmp_path: Path) -> None:
        """When no tag is provided but git describe finds a matching tag."""
        pyproject_path = _create_pyproject(tmp_path, "0.1.0")

        with patch("scripts.check_tag_version.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "v0.1.0\n"

            ok, message = check_tag_version(None, pyproject_path)
            assert ok is True
            assert "0.1.0" in message
