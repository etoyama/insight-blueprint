"""Integration tests for /premortem performance -- Integ-24.

Verifies wall-clock performance targets from NFR Performance.
Uses ``time.perf_counter()`` instead of pytest-benchmark.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

from tests.integration.conftest import (
    build_premortem_payload,
    run_premortem_cli,
)

JST = ZoneInfo("Asia/Tokyo")
yaml_out = YAML()
yaml_out.preserve_quotes = True


def _create_history_manifests(
    runs_dir: Path,
    source_id: str,
    count: int,
    *,
    design_prefix: str = "DES-PERF",
) -> None:
    """Create *count* past run manifests for a given source_id."""
    for i in range(count):
        run_id = f"20260301_{230000 + i:06d}"
        design_id = f"{design_prefix}-{i}"
        manifest_dir = runs_dir / run_id / design_id
        manifest_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "design_id": design_id,
            "run_id": run_id,
            "status": "completed",
            "started_at": f"2026-03-{1 + i:02d}T23:00:00+09:00",
            "ended_at": f"2026-03-{1 + i:02d}T23:20:00+09:00",
            "elapsed_min": 15.0 + (i % 5),
            "cost_usd": 0.20,
            "api_retries": 0,
            "error_category": None,
            "estimated_rows": 1_000_000,
            "design_snapshot": {
                "hash": f"sha256:perf{i:04d}",
                "source_ids": [source_id],
                "intent": "exploratory",
                "methodology": "perf test",
            },
            "methodology_tags": ["descriptive"],
            "input_profile": {
                "column_count": 20,
                "data_volume_strategy": "sample",
            },
            "verdict": {
                "direction": "supports",
                "confidence": "medium",
                "events_recorded": 3,
            },
        }
        with (manifest_dir / "manifest.yaml").open("w") as f:
            yaml_out.dump(data, f)


# =========================================================================
# Integ-24: NFR Performance
# =========================================================================


class TestPremortemPerformance:
    """Integ-24: execution time targets."""

    def test_premortem_queued_under_30s_with_10_designs_30_history(
        self,
        insight_root: Path,
        config_review_a: Path,
    ) -> None:
        """10 designs + 30 past manifests -> wall-clock < 30s."""
        base_dir = insight_root
        cwd = insight_root.parent

        # Create 30 history manifests across 3 source_ids
        for src_idx in range(3):
            _create_history_manifests(
                base_dir / "runs",
                f"perf_src_{src_idx}",
                10,
                design_prefix=f"HIST-{src_idx}",
            )

        # Build 10 designs
        designs = []
        for i in range(10):
            src_id = f"perf_src_{i % 3}"
            designs.append(
                {
                    "id": f"DES-P{i:02d}",
                    "hypothesis": f"perf test {i}",
                    "intent": "exploratory",
                    "methodology": f"analysis {i}",
                    "source_ids": [src_id],
                    "metrics": [],
                    "acceptance_criteria": [],
                    "status": "analyzing",
                    "next_action": {"type": "batch_execute"},
                }
            )

        overrides = {d["id"]: {"estimated_rows": 1_500_000} for d in designs}
        payload = build_premortem_payload(designs, overrides)

        start = time.perf_counter()
        result = run_premortem_cli(
            ["--queued", "--yes", "--mode", "auto", "--base-dir", str(base_dir)],
            payload,
            cwd=cwd,
        )
        elapsed = time.perf_counter() - start

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert elapsed < 30.0, f"Took {elapsed:.1f}s, expected < 30s"

    def test_manifest_atomic_write_under_100ms(
        self,
        insight_root: Path,
    ) -> None:
        """write_design_manifest 1 call < 100ms median (5 iterations)."""
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        from skills._shared.manifest_writer import write_design_manifest
        from skills._shared.models import DesignManifest

        base_dir = insight_root
        run_id = "20260420_perf_test"
        (base_dir / "runs" / run_id).mkdir(parents=True, exist_ok=True)

        manifest = DesignManifest(
            run_id=run_id,
            design_id="DES-PERF-M",
            design_hash="sha256:perfhash",
            status="success",
            methodology_tags=["descriptive"],
            verdict={
                "direction": "supports",
                "confidence": "high",
                "events_recorded": 1,
            },
            started_at=datetime.now(JST).isoformat(),
            ended_at=datetime.now(JST).isoformat(),
            elapsed_min=10.0,
            estimated_rows=1_000_000,
            error_category=None,
            error_detail=None,
        )

        times: list[float] = []
        for _ in range(5):
            start = time.perf_counter()
            write_design_manifest(run_id, "DES-PERF-M", manifest, base_dir=base_dir)
            times.append(time.perf_counter() - start)

        times.sort()
        median_ms = times[len(times) // 2] * 1000
        assert median_ms < 100.0, f"Median write time {median_ms:.1f}ms > 100ms"

    def test_session_id_extraction_under_500ms(
        self,
        insight_root: Path,
    ) -> None:
        """Extracting session_id from 1000-line events.jsonl < 500ms."""

        # Create a 1000-line events.jsonl with first line being system/init
        run_id = "20260420_session_perf"
        run_dir = insight_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        events_path = run_dir / "events.jsonl"
        with events_path.open("w") as f:
            # First line: system/init
            f.write(
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "PERF-SESSION-001",
                    }
                )
                + "\n"
            )
            # Fill with 999 more lines
            for i in range(999):
                f.write(json.dumps({"type": "tool_use", "index": i}) + "\n")

        # Extract session_id by reading first valid init line
        start = time.perf_counter()
        session_id = None
        with events_path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    if evt.get("type") == "system" and evt.get("subtype") == "init":
                        session_id = evt.get("session_id")
                        break
                except json.JSONDecodeError:
                    continue
        elapsed = time.perf_counter() - start

        assert session_id == "PERF-SESSION-001"
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 500.0, f"Extraction took {elapsed_ms:.1f}ms > 500ms"
