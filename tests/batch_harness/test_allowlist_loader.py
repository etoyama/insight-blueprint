"""Tests for allowlist_loader: YAML primary + SKILL.md fallback.

Covers:
  - YAML load success
  - YAML missing -> fallback to SKILL.md
  - Both fail -> AllowlistLoadError
  - YAML malformed -> fallback
  - SKILL.md table parsing
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skills.premortem.lib.allowlist_loader import AllowlistLoadError, load_allowlist


@pytest.fixture()
def yaml_allowlist(tmp_path: Path) -> Path:
    """Create a valid package_allowlist.yaml."""
    p = tmp_path / "package_allowlist.yaml"
    p.write_text(
        "allowed_packages:\n  pandas: pandas\n  sklearn: scikit-learn\n  numpy: numpy\n"
    )
    return p


@pytest.fixture()
def skill_md_with_table(tmp_path: Path) -> Path:
    """Create a SKILL.md with a Package Allowlist table."""
    p = tmp_path / "SKILL.md"
    p.write_text(
        "# /batch-analysis\n\n"
        "### Package Allowlist\n\n"
        "| Alias | Import | pip/uv package |\n"
        "|-------|--------|----------------|\n"
        "| pandas | pandas | pandas |\n"
        "| matplotlib | matplotlib | matplotlib |\n"
        "| scipy | scipy | scipy |\n"
        "\nSome other section.\n"
    )
    return p


class TestLoadFromYaml:
    """Primary source: YAML file."""

    def test_loads_yaml_successfully(
        self, yaml_allowlist: Path, tmp_path: Path
    ) -> None:
        result = load_allowlist(
            yaml_path=yaml_allowlist,
            skill_md_path=tmp_path / "nonexistent.md",
        )
        assert result == {
            "pandas": "pandas",
            "sklearn": "scikit-learn",
            "numpy": "numpy",
        }

    def test_yaml_takes_priority_over_skillmd(
        self, yaml_allowlist: Path, skill_md_with_table: Path
    ) -> None:
        result = load_allowlist(
            yaml_path=yaml_allowlist,
            skill_md_path=skill_md_with_table,
        )
        # YAML has 3 entries, SKILL.md has 3 different ones
        assert "sklearn" in result  # from YAML
        assert "matplotlib" not in result  # only in SKILL.md


class TestFallbackToSkillMd:
    """Fallback to SKILL.md when YAML fails."""

    def test_falls_back_when_yaml_missing(
        self, tmp_path: Path, skill_md_with_table: Path
    ) -> None:
        result = load_allowlist(
            yaml_path=tmp_path / "nonexistent.yaml",
            skill_md_path=skill_md_with_table,
        )
        assert result == {
            "pandas": "pandas",
            "matplotlib": "matplotlib",
            "scipy": "scipy",
        }

    def test_falls_back_when_yaml_malformed(
        self, tmp_path: Path, skill_md_with_table: Path
    ) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("not_allowed_packages: oops\n")
        result = load_allowlist(
            yaml_path=bad_yaml,
            skill_md_path=skill_md_with_table,
        )
        assert "pandas" in result


class TestBothFail:
    """AllowlistLoadError when neither source works."""

    def test_raises_when_both_missing(self, tmp_path: Path) -> None:
        with pytest.raises(AllowlistLoadError, match="Failed to load"):
            load_allowlist(
                yaml_path=tmp_path / "nope.yaml",
                skill_md_path=tmp_path / "nope.md",
            )

    def test_raises_when_yaml_bad_and_skillmd_no_section(self, tmp_path: Path) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("garbage: true\n")
        bad_md = tmp_path / "SKILL.md"
        bad_md.write_text("# No allowlist section here\n")
        with pytest.raises(AllowlistLoadError):
            load_allowlist(yaml_path=bad_yaml, skill_md_path=bad_md)


class TestSkillMdParsing:
    """Edge cases for SKILL.md table parsing."""

    def test_empty_table_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text(
            "### Package Allowlist\n\n"
            "| Alias | Import | pip/uv package |\n"
            "|-------|--------|----------------|\n"
            "\nEnd of section.\n"
        )
        # YAML missing, SKILL.md table empty -> error
        with pytest.raises(AllowlistLoadError):
            load_allowlist(
                yaml_path=tmp_path / "nope.yaml",
                skill_md_path=md,
            )

    def test_table_with_extra_whitespace(self, tmp_path: Path) -> None:
        md = tmp_path / "SKILL.md"
        md.write_text(
            "### Package Allowlist\n\n"
            "| Alias | Import | pip/uv package |\n"
            "|-------|--------|----------------|\n"
            "|  pandas  |  pandas  |  pandas  |\n"
            "|  sklearn  |  sklearn  |  scikit-learn  |\n"
            "\n"
        )
        result = load_allowlist(
            yaml_path=tmp_path / "nope.yaml",
            skill_md_path=md,
        )
        assert result == {"pandas": "pandas", "sklearn": "scikit-learn"}
