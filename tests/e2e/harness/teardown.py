#!/usr/bin/env python3
"""E2E harness teardown -- restore real .insight and remove temp directory.

Usage:
    python tests/e2e/harness/teardown.py

Reads E2E_TMP_DIR and PROJECT_ROOT from environment.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    tmp_dir = os.environ.get("E2E_TMP_DIR")
    project_root = os.environ.get("PROJECT_ROOT")

    if not tmp_dir or not project_root:
        print("No E2E_TMP_DIR or PROJECT_ROOT set", file=sys.stderr)
        return 0

    tmp_path = Path(tmp_dir)
    proj_path = Path(project_root)
    real_insight = proj_path / ".insight"
    backup_insight = tmp_path / ".insight_backup"

    # Restore real .insight from backup
    try:
        if real_insight.is_symlink():
            real_insight.unlink()
        elif real_insight.exists():
            # Something unexpected -- don't destroy it
            pass

        if backup_insight.exists():
            shutil.move(str(backup_insight), str(real_insight))
    except Exception as e:
        print(f"WARNING: failed to restore .insight: {e}", file=sys.stderr)

    # Remove temp directory
    if "insight-e2e-" in str(tmp_path):
        try:
            shutil.rmtree(str(tmp_path), ignore_errors=True)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
