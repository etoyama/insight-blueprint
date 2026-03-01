"""Shared helpers for skill-related tests.

Provides FakeTraversable and factory functions used by
test_skill_update.py and test_skill_integration.py.
"""

from pathlib import Path
from typing import Any


class FakeTraversable:
    """Minimal Traversable implementation backed by a real directory.

    Mirrors the interface of importlib.resources Traversable so we can
    feed real file content into _discover_bundled_skills / _copy_skill_tree
    without depending on a real installed package.
    """

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
            yield FakeTraversable(child)

    def read_text(self, encoding: str = "utf-8") -> str:
        return self._path.read_text(encoding=encoding)

    def read_bytes(self) -> bytes:
        return self._path.read_bytes()

    def __truediv__(self, other: str) -> "FakeTraversable":
        return FakeTraversable(self._path / other)

    def __str__(self) -> str:
        return str(self._path)


def make_traversable(base_dir: Path) -> Any:
    """Create a FakeTraversable tree from a real directory."""
    return FakeTraversable(base_dir)


def create_fake_package(
    base: Path,
    skills: dict[str, str | None],
    *,
    include_templates: bool = True,
    include_rules: bool = True,
) -> FakeTraversable:
    """Create a fake package directory with _skills/ and return Traversable.

    Args:
        base: Root directory for fake package.
        skills: Mapping of skill_name -> version (None = no version field).
        include_templates: Also create _templates/ with CLAUDE.md.template.
        include_rules: Also create _rules/ with bundled rule files.
    """
    skills_dir = base / "_skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name, version in skills.items():
        skill = skills_dir / name
        skill.mkdir(parents=True, exist_ok=True)
        frontmatter = f"---\nname: {name}\n"
        if version is not None:
            frontmatter += f'version: "{version}"\n'
        frontmatter += f"description: {name} skill\n---\n# {name}\n"
        (skill / "SKILL.md").write_text(frontmatter)

    if include_templates:
        templates_dir = base / "_templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / "__init__.py").write_text("")
        (templates_dir / "CLAUDE.md.template").write_text(
            "## insight-blueprint\n\nManaged content.\n"
        )

    if include_rules:
        rules_dir = base / "_rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "__init__.py").write_text("")
        for rule_name in (
            "insight-yaml.md",
            "analysis-workflow.md",
            "catalog-workflow.md",
        ):
            (rules_dir / rule_name).write_text(
                f'---\nversion: "1.0.0"\npaths:\n  - ".insight/**"\n---\n# {rule_name}\n'
            )

    return FakeTraversable(base)
