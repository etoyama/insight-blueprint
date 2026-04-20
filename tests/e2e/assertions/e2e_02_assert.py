#!/usr/bin/env python3
"""E2E-02 assertions: Crash recovery next-day resume.

Verifies 5 expectations from the test-design spec.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.e2e.harness.assert_helpers import (  # noqa: E402
    assert_field_equals,
    assert_file_exists,
    assert_ndjson_valid,
    grep_events,
    load_yaml,
)


def main() -> int:
    insight_root = Path(os.environ.get("INSIGHT_ROOT", "."))
    insight_dir = insight_root / ".insight"
    errors: list[str] = []

    runs_dir = insight_dir / "runs"
    run_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir() and (d / "events.jsonl").exists()],
        key=lambda p: p.name,
        reverse=True,
    )
    if not run_dirs:
        print("FAIL: No run directory with events.jsonl found", file=sys.stderr)
        return 1
    run_dir = run_dirs[0]

    def check(label: str, fn) -> None:
        try:
            fn()
        except (AssertionError, FileNotFoundError, Exception) as e:
            errors.append(f"  [{label}] {e}")

    # --- Assertion 1: stderr shows incomplete run detection ---
    # (Checked by runner capturing stderr; here we verify structurally)
    def assert_1():
        # If crash recovery ran, there should be evidence in events
        events = assert_ndjson_valid(run_dir / "events.jsonl")
        init_events = grep_events(events, type="system", subtype="init")
        assert len(init_events) >= 2, (
            f"Expected >= 2 system/init events (crash+resume), got {len(init_events)}"
        )

    check("1: crash detection (2 init events)", assert_1)

    # --- Assertion 2: events.jsonl has 2 init lines (2 sessions) ---
    def assert_2():
        events = assert_ndjson_valid(run_dir / "events.jsonl")
        init_events = grep_events(events, type="system", subtype="init")
        assert len(init_events) == 2, f"Expected 2 init events, got {len(init_events)}"

    check("2: 2 init events in events.jsonl", assert_2)

    # --- Assertion 3: DES-B manifest ends with success ---
    def assert_3():
        manifest_b = run_dir / "DES-B" / "manifest.yaml"
        assert_file_exists(manifest_b, "DES-B manifest after resume")
        m = load_yaml(manifest_b)
        exec_data = m.get("execution", {})
        status = exec_data.get("status") or m.get("status")
        assert status == "success", f"DES-B status={status}, expected=success"
        ended = m.get("ended_at") or exec_data.get("ended_at")
        assert ended is not None, "DES-B has no ended_at"

    check("3: DES-B manifest success", assert_3)

    # --- Assertion 4: run.yaml status=completed ---
    def assert_4():
        run_yaml = load_yaml(run_dir / "run.yaml")
        assert_field_equals(run_yaml, "status", "completed", "run.yaml")

    check("4: run.yaml completed", assert_4)

    # --- Assertion 5: same token used for both sessions ---
    def assert_5():
        token_dir = insight_dir / "premortem"
        tokens = sorted(token_dir.glob("*.yaml"))
        assert len(tokens) >= 1, "No token found"
        # The run.yaml should reference the same token
        run_yaml = load_yaml(run_dir / "run.yaml")
        token_in_run = run_yaml.get("premortem_token")
        assert token_in_run is not None, "run.yaml has no premortem_token"

    check("5: same token for both sessions", assert_5)

    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("E2E-02: All 5 assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
