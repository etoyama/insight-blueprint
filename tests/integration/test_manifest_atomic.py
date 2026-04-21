"""Integration tests for manifest atomic write -- Integ-08.

Tests atomic write across processes and tempfile cleanup.
"""

from __future__ import annotations

import multiprocessing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

JST = ZoneInfo("Asia/Tokyo")
yaml = YAML(typ="safe")


def _write_manifest_worker(args: tuple) -> None:
    """Worker function for multiprocess atomic write test."""
    base_dir, run_id, design_id, worker_id = args
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from skills._shared.manifest_writer import write_design_manifest
    from skills._shared.models import DesignManifest

    manifest = DesignManifest(
        run_id=run_id,
        design_id=design_id,
        design_hash=f"sha256:worker_{worker_id}",
        status="success",
        methodology_tags=["descriptive"],
        verdict={"direction": "supports", "confidence": "high", "events_recorded": 1},
        started_at=datetime.now(JST).isoformat(),
        ended_at=datetime.now(JST).isoformat(),
        elapsed_min=10.0,
        estimated_rows=1_000_000,
        error_category=None,
        error_detail=None,
    )
    write_design_manifest(run_id, design_id, manifest, base_dir=Path(base_dir))


# =========================================================================
# Integ-08: Atomic write across processes
# =========================================================================


class TestManifestAtomicWriteIntegration:
    """Integ-08: atomic writes are safe across concurrent processes."""

    def test_replace_atomic_across_processes(
        self,
        insight_root: Path,
    ) -> None:
        """Two processes writing same manifest -> last rename wins, no corruption."""
        run_id = "20260420_atomic_test"
        design_id = "DES-ATOMIC"
        manifest_dir = insight_root / "runs" / run_id / design_id
        manifest_dir.mkdir(parents=True, exist_ok=True)

        # Write methodology vocab
        # (already done by insight_root fixture)

        # Launch 2 processes that write to the same manifest
        args_list = [
            (str(insight_root), run_id, design_id, 0),
            (str(insight_root), run_id, design_id, 1),
        ]

        with multiprocessing.Pool(2) as pool:
            pool.map(_write_manifest_worker, args_list)

        # The file should exist and be valid YAML
        manifest_path = manifest_dir / "manifest.yaml"
        assert manifest_path.exists()

        with manifest_path.open("r") as f:
            data = yaml.load(f)

        # Should have valid structure (whichever worker wrote last wins)
        assert data is not None
        assert data["design_id"] == design_id
        assert data["run_id"] == run_id
        assert data["status"] == "success"
        # Hash should be from one of the workers
        assert data["design_hash"] in ("sha256:worker_0", "sha256:worker_1")

    def test_partial_tempfile_cleanup(
        self,
        insight_root: Path,
    ) -> None:
        """After successful write, no .tmp files remain in directory."""
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        from skills._shared.manifest_writer import write_design_manifest
        from skills._shared.models import DesignManifest

        run_id = "20260420_cleanup_test"
        design_id = "DES-CLEANUP"
        manifest_dir = insight_root / "runs" / run_id / design_id
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest = DesignManifest(
            run_id=run_id,
            design_id=design_id,
            design_hash="sha256:cleanup_hash",
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
        write_design_manifest(run_id, design_id, manifest, base_dir=insight_root)

        # No .tmp files should remain
        tmp_files = list(manifest_dir.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Leftover temp files: {tmp_files}"

        # Lock files existing is OK (filelock leaves them), but the manifest
        # should be valid
        manifest_path = manifest_dir / "manifest.yaml"
        assert manifest_path.exists()
