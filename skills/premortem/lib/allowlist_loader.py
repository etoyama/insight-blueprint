"""Load package allowlist from YAML (primary) or SKILL.md table (fallback).

The allowlist maps import aliases (e.g. ``sklearn``) to pip/uv package names
(e.g. ``scikit-learn``).

Raises ``AllowlistLoadError`` when both sources fail.
"""

from __future__ import annotations

import re
from pathlib import Path

from ruamel.yaml import YAML

_YAML_PATH = Path(".insight/rules/package_allowlist.yaml")
_SKILL_MD_PATH = Path("skills/batch-analysis/SKILL.md")

# Regex for markdown table rows: ``| alias | import | package |``
_TABLE_ROW_RE = re.compile(r"^\|\s*(\S+)\s*\|\s*\S+\s*\|\s*(\S+)\s*\|$")


class AllowlistLoadError(Exception):
    """Raised when both YAML and SKILL.md sources fail."""


def load_allowlist(
    yaml_path: Path | None = None,
    skill_md_path: Path | None = None,
) -> dict[str, str]:
    """Load the package allowlist.

    Parameters
    ----------
    yaml_path:
        Override path for the YAML file (testing).
    skill_md_path:
        Override path for SKILL.md (testing).

    Returns
    -------
    dict[str, str]
        Mapping of import alias -> pip/uv package name.

    Raises
    ------
    AllowlistLoadError
        When both primary (YAML) and fallback (SKILL.md) sources fail.
    """
    yaml_file = yaml_path or _YAML_PATH
    skill_file = skill_md_path or _SKILL_MD_PATH

    # Primary: YAML
    try:
        return _load_from_yaml(yaml_file)
    except Exception:
        pass

    # Fallback: SKILL.md markdown table
    try:
        return _load_from_skill_md(skill_file)
    except Exception:
        pass

    raise AllowlistLoadError(
        f"Failed to load allowlist from both {yaml_file} and {skill_file}"
    )


def _load_from_yaml(path: Path) -> dict[str, str]:
    """Read allowlist from YAML file."""
    yaml = YAML(typ="safe")
    with path.open("r") as f:
        data = yaml.load(f)

    if not isinstance(data, dict):
        msg = f"Invalid YAML structure in {path}"
        raise ValueError(msg)

    packages = data.get("allowed_packages")
    if not isinstance(packages, dict):
        msg = f"Missing or invalid 'allowed_packages' key in {path}"
        raise ValueError(msg)

    return {str(k): str(v) for k, v in packages.items()}


def _load_from_skill_md(path: Path) -> dict[str, str]:
    """Parse allowlist from SKILL.md markdown table.

    Expects a section ``### Package Allowlist`` followed by a markdown table
    with columns: Alias | Import | pip/uv package.
    """
    text = path.read_text()

    # Find the Package Allowlist section
    section_start = text.find("### Package Allowlist")
    if section_start == -1:
        msg = "Package Allowlist section not found in SKILL.md"
        raise ValueError(msg)

    section_text = text[section_start:]

    # Find the table and parse rows
    result: dict[str, str] = {}
    in_table = False

    for line in section_text.split("\n"):
        stripped = line.strip()

        # Skip header separator (|---|---|---|)
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue

        if in_table:
            # End of table
            if not stripped.startswith("|"):
                break

            match = _TABLE_ROW_RE.match(stripped)
            if match:
                alias = match.group(1)
                package = match.group(2)
                # Skip header row values
                if alias.lower() != "alias":
                    result[alias] = package

    if not result:
        msg = "No packages found in SKILL.md table"
        raise ValueError(msg)

    return result
