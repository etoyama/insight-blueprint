"""Thin wrapper for calling E2E runners from within Claude Code.

Optional -- runners are primarily called via bash directly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "pyproject.toml").exists():
            return ancestor
    return p.parent.parent.parent.parent


def run_e2e_scenario(scenario_name: str) -> int:
    """Run an E2E scenario runner script and return its exit code."""
    project_root = _project_root()
    runner_path = project_root / "tests" / "e2e" / "runners" / f"{scenario_name}.sh"

    if not runner_path.exists():
        print(f"Runner not found: {runner_path}", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["bash", str(runner_path)],
        cwd=str(project_root),
        capture_output=False,
    )
    return result.returncode
