#!/usr/bin/env python3
"""E2E-03 assertions: Phase A -> Phase B migration.

Verifies 3 expectations from the test-design spec.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.e2e.harness.assert_helpers import (  # noqa: E402
    load_yaml,
)


def main() -> int:
    insight_root = Path(os.environ.get("INSIGHT_ROOT", "."))
    insight_dir = insight_root / ".insight"
    errors: list[str] = []

    # Phase A and Phase B results are stored as env markers by the runner
    phase_a_exit = int(os.environ.get("E2E_03_PHASE_A_EXIT", "255"))
    phase_b_exit = int(os.environ.get("E2E_03_PHASE_B_EXIT", "255"))

    def check(label: str, fn) -> None:
        try:
            fn()
        except (AssertionError, FileNotFoundError, Exception) as e:
            errors.append(f"  [{label}] {e}")

    # --- Assertion 1: Phase A runs with warning (exit 0) ---
    def assert_1():
        assert phase_a_exit == 0, (
            f"Phase A should exit 0 (warning+continue), got {phase_a_exit}"
        )

    check("1: Phase A warning + continue", assert_1)

    # --- Assertion 2: Phase A run.yaml has legacy mode ---
    def assert_2():
        runs_dir = insight_dir / "runs"
        if not runs_dir.exists():
            raise AssertionError("No runs directory after Phase A")
        run_dirs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir() and (d / "run.yaml").exists()],
            key=lambda p: p.name,
            reverse=True,
        )
        # Find a run with automation_mode=legacy
        found_legacy = False
        for rd in run_dirs:
            run_yaml = load_yaml(rd / "run.yaml")
            if run_yaml.get("automation_mode") == "legacy":
                found_legacy = True
                assert run_yaml.get("premortem_token") is None, (
                    "Legacy run should have premortem_token=null"
                )
                break
        assert found_legacy, "No run.yaml with automation_mode=legacy found"

    check("2: run.yaml legacy mode", assert_2)

    # --- Assertion 3: Phase B rejects with exit 1 ---
    def assert_3():
        assert phase_b_exit == 1, (
            f"Phase B should exit 1 (required rejection), got {phase_b_exit}"
        )

    check("3: Phase B exit 1", assert_3)

    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("E2E-03: All 3 assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
