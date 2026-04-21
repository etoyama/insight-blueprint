#!/usr/bin/env python3
"""E2E harness setup -- create temp .insight/ and symlink into project root.

Usage:
    python tests/e2e/harness/setup.py --scenario e2e_01

Strategy:
  1. Create temp dir with .insight/ populated from fixtures.
  2. Move $PROJECT_ROOT/.insight to $TMP/.insight_backup.
  3. Symlink $PROJECT_ROOT/.insight -> $TMP/.insight.
  4. Teardown reverses this.

This ensures launcher.sh (which cd's to PROJECT_ROOT and reads .insight/)
sees the E2E fixtures, not the real project data.

Outputs shell-sourceable export lines to stdout.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

SCENARIOS = ("e2e_01", "e2e_02", "e2e_03")


def _project_root() -> Path:
    """Walk up from this file to find the project root (contains pyproject.toml)."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "pyproject.toml").exists():
            return ancestor
    return p.parent.parent.parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E2E harness setup")
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        required=True,
        help="Scenario name (e2e_01, e2e_02, e2e_03)",
    )
    args = parser.parse_args(argv)

    project_root = _project_root()
    fixtures_dir = project_root / "tests" / "e2e" / "fixtures"

    # Create temp directory
    tmp_dir = Path(tempfile.mkdtemp(prefix="insight-e2e-"))
    insight_dir = tmp_dir / ".insight"
    insight_dir.mkdir()

    # Copy designs
    designs_src = fixtures_dir / "designs"
    designs_dst = insight_dir / "designs"
    if designs_src.exists():
        shutil.copytree(str(designs_src), str(designs_dst))

    # Copy runs_history as past runs
    history_src = fixtures_dir / "runs_history"
    runs_dst = insight_dir / "runs"
    if history_src.exists():
        shutil.copytree(str(history_src), str(runs_dst))

    # Copy config based on scenario
    config_map = {
        "e2e_01": "review_phase_a.yaml",
        "e2e_02": "review_phase_a.yaml",
        "e2e_03": "review_phase_a.yaml",  # Phase A first, runner swaps to B
    }
    config_src = fixtures_dir / "config" / config_map[args.scenario]
    config_dst = insight_dir / "config.yaml"
    shutil.copy2(str(config_src), str(config_dst))

    # Copy rules (methodology_vocab.yaml)
    rules_src = project_root / ".insight" / "rules"
    rules_dst = insight_dir / "rules"
    if rules_src.exists():
        shutil.copytree(str(rules_src), str(rules_dst))

    # Create premortem directory
    (insight_dir / "premortem").mkdir(exist_ok=True)

    # Back up real .insight and symlink E2E .insight into project root
    real_insight = project_root / ".insight"
    backup_insight = tmp_dir / ".insight_backup"

    if real_insight.is_symlink():
        # Already symlinked (nested run?), just remove symlink
        real_insight.unlink()
    elif real_insight.exists():
        # Move real .insight to backup
        shutil.move(str(real_insight), str(backup_insight))

    # Create symlink: PROJECT_ROOT/.insight -> TMP/.insight
    real_insight.symlink_to(insight_dir)

    # Output shell-sourceable exports
    stub_bin_dir = project_root / "tests" / "e2e" / "bin"
    venv_bin_dir = project_root / ".venv" / "bin"
    print(f"export INSIGHT_ROOT={tmp_dir}")
    print(f"export STUB_FIXTURES_DIR={fixtures_dir}")
    print(f"export STUB_SCENARIO={args.scenario}")
    print(f'export PATH="{stub_bin_dir}:{venv_bin_dir}:{os.environ.get("PATH", "")}"')
    print(f"export PROJECT_ROOT={project_root}")
    print(f"export E2E_TMP_DIR={tmp_dir}")
    print(f"export VIRTUAL_ENV={project_root / '.venv'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
