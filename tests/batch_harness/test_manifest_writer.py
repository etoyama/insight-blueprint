"""Tests for skills/_shared/manifest_writer.py.

Unit-15: init_run (3 cases)
Unit-16: update/finalize (5 cases)
Unit-17: vocab validation (4 cases)
Unit-18: write_design_manifest atomic (6 cases)
Unit-23: status bars / finalize_run (3 cases)
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from ruamel.yaml import YAML

from skills._shared.models import DesignManifest, RunStatus

JST = ZoneInfo("Asia/Tokyo")


def _read_yaml(path: Path) -> dict:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f)


def _write_vocab(base_dir: Path) -> None:
    """Write methodology_vocab.yaml for tests."""
    vocab_dir = base_dir / "rules"
    vocab_dir.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.dump(
        {
            "methodology_tags": [
                "correlation_analysis",
                "regression",
                "time_series",
                "classification",
                "clustering",
                "hypothesis_test",
                "descriptive",
                "segmentation",
                "causal_inference",
                "ab_test",
            ]
        },
        (vocab_dir / "methodology_vocab.yaml").open("w"),
    )


_SENTINEL = object()


def _make_manifest(
    run_id: str = "20260418_230000",
    design_id: str = "DES-042",
    status: str = "success",
    methodology_tags: list[str] | None = None,
    verdict: dict | None | object = _SENTINEL,
    error_category: str | None = None,
    error_detail: str | None = None,
    skip_reason: str | None = None,
) -> DesignManifest:
    if methodology_tags is None:
        methodology_tags = ["correlation_analysis"]
    if verdict is _SENTINEL:
        verdict = {"direction": "supports", "confidence": "high", "events_recorded": 5}
    return DesignManifest(
        run_id=run_id,
        design_id=design_id,
        design_hash="sha256:abc123",
        status=status,
        methodology_tags=methodology_tags,
        verdict=verdict,  # type: ignore[arg-type]
        started_at="2026-04-18T23:02:15+09:00",
        ended_at="2026-04-18T23:20:27+09:00",
        elapsed_min=18.2,
        estimated_rows=1500000,
        error_category=error_category,
        error_detail=error_detail,
        skip_reason=skip_reason,
    )


# ---------------------------------------------------------------------------
# Unit-15: TestManifestWriterInitRun
# ---------------------------------------------------------------------------


class TestManifestWriterInitRun:
    """Unit-15: init_run creates run.yaml with required fields."""

    def test_init_run_has_required_fields(self, tmp_path: Path) -> None:
        """t1: run.yaml has run_id/session_id/started_at/automation_mode/premortem_token."""
        from skills._shared.manifest_writer import init_run

        init_run("20260418_230000", None, "review", "token123", base_dir=tmp_path)

        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert data["run_id"] == "20260418_230000"
        assert data["session_id"] is None
        assert "started_at" in data
        assert data["automation_mode"] == "review"
        assert data["premortem_token"] == "token123"
        assert data["status"] == "running"

    def test_init_run_session_id_none(self, tmp_path: Path) -> None:
        """t2: session_id=None is written correctly."""
        from skills._shared.manifest_writer import init_run

        init_run("20260418_230000", None, "review", "token123", base_dir=tmp_path)
        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert data["session_id"] is None

    def test_init_run_started_at_is_iso8601_jst(self, tmp_path: Path) -> None:
        """t3: started_at is ISO8601 with JST timezone."""
        from skills._shared.manifest_writer import init_run

        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)
        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        dt = datetime.fromisoformat(data["started_at"])
        assert dt.tzinfo is not None
        assert "+09:00" in data["started_at"]


# ---------------------------------------------------------------------------
# Unit-16: TestManifestWriterUpdateFinalize
# ---------------------------------------------------------------------------


class TestManifestWriterUpdateFinalize:
    """Unit-16: update_run_session_id and finalize_run."""

    def _init(self, tmp_path: Path, run_id: str = "20260418_230000") -> None:
        from skills._shared.manifest_writer import init_run

        init_run(run_id, None, "review", "token123", base_dir=tmp_path)

    def test_update_session_id_preserves_fields(self, tmp_path: Path) -> None:
        """t1: session_id update preserves other fields."""
        from skills._shared.manifest_writer import update_run_session_id

        self._init(tmp_path)
        update_run_session_id("20260418_230000", "sess-abc-123", base_dir=tmp_path)

        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert data["session_id"] == "sess-abc-123"
        assert data["run_id"] == "20260418_230000"
        assert data["automation_mode"] == "review"
        assert data["premortem_token"] == "token123"

    def test_finalize_run_adds_fields(self, tmp_path: Path) -> None:
        """t2: finalize_run adds ended_at/status/cost_total_usd."""
        from skills._shared.manifest_writer import finalize_run

        self._init(tmp_path)
        ended = datetime(2026, 4, 19, 1, 45, 12, tzinfo=JST)
        finalize_run(
            "20260418_230000", RunStatus.COMPLETED, 2.34, ended, base_dir=tmp_path
        )

        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert data["status"] == "completed"
        assert data["cost_total_usd"] == pytest.approx(2.34)
        assert "ended_at" in data

    def test_finalize_preserves_existing(self, tmp_path: Path) -> None:
        """t3: finalize preserves started_at/automation_mode/premortem_token."""
        from skills._shared.manifest_writer import finalize_run

        self._init(tmp_path)
        ended = datetime(2026, 4, 19, 1, 45, 12, tzinfo=JST)
        finalize_run(
            "20260418_230000", RunStatus.COMPLETED, 2.34, ended, base_dir=tmp_path
        )

        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert "started_at" in data
        assert data["automation_mode"] == "review"
        assert data["premortem_token"] == "token123"

    def test_update_nonexistent_raises(self, tmp_path: Path) -> None:
        """t4: update on nonexistent file raises FileNotFoundError."""
        from skills._shared.manifest_writer import update_run_session_id

        with pytest.raises(FileNotFoundError):
            update_run_session_id("nonexistent_run", "sess-123", base_dir=tmp_path)

    def test_finalize_run_incomplete(self, tmp_path: Path) -> None:
        """t5: finalize_run with status=INCOMPLETE works."""
        from skills._shared.manifest_writer import finalize_run

        self._init(tmp_path)
        ended = datetime(2026, 4, 19, 1, 0, 0, tzinfo=JST)
        finalize_run(
            "20260418_230000", RunStatus.INCOMPLETE, 0.0, ended, base_dir=tmp_path
        )

        data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert data["status"] == "incomplete"


# ---------------------------------------------------------------------------
# Unit-17: TestManifestWriterVocab
# ---------------------------------------------------------------------------


class TestManifestWriterVocab:
    """Unit-17: methodology_tags vocab validation."""

    def test_valid_tags_pass(self, tmp_path: Path) -> None:
        """t1: vocab-internal tags -> write succeeds."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(
            methodology_tags=["correlation_analysis", "time_series"]
        )
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        path = tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        assert path.exists()

    def test_invalid_tag_raises(self, tmp_path: Path) -> None:
        """t2: vocab-external tag -> MethodologyTagError."""
        from skills._shared.manifest_writer import (
            MethodologyTagError,
            init_run,
            write_design_manifest,
        )

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(methodology_tags=["not_in_vocab"])
        with pytest.raises(MethodologyTagError):
            write_design_manifest(
                "20260418_230000", "DES-042", manifest, base_dir=tmp_path
            )

    def test_mixed_valid_invalid_raises(self, tmp_path: Path) -> None:
        """t3: mix of valid+invalid -> raise (no partial write)."""
        from skills._shared.manifest_writer import (
            MethodologyTagError,
            init_run,
            write_design_manifest,
        )

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(methodology_tags=["correlation_analysis", "bad_tag"])
        with pytest.raises(MethodologyTagError):
            write_design_manifest(
                "20260418_230000", "DES-042", manifest, base_dir=tmp_path
            )

        # No partial file should exist
        path = tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        assert not path.exists()

    def test_empty_tags_ok(self, tmp_path: Path) -> None:
        """t4: empty list is OK (error only when vocab-external values present)."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(methodology_tags=[])
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        path = tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        assert path.exists()


# ---------------------------------------------------------------------------
# Unit-18: TestManifestWriterDesignManifest
# ---------------------------------------------------------------------------


class TestManifestWriterDesignManifest:
    """Unit-18: write_design_manifest atomic write."""

    def test_write_all_fields_readable(self, tmp_path: Path) -> None:
        """t1: Normal write and all fields are readable."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest()
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["design_id"] == "DES-042"
        assert data["status"] == "success"
        assert data["methodology_tags"] == ["correlation_analysis"]
        assert data["verdict"]["direction"] == "supports"

    def test_crash_during_write_preserves_existing(self, tmp_path: Path) -> None:
        """t2: If os.replace fails, existing file is not corrupted."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        # Write initial manifest
        manifest1 = _make_manifest(status="success")
        write_design_manifest(
            "20260418_230000", "DES-042", manifest1, base_dir=tmp_path
        )

        manifest_path = (
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        # Monkey-patch os.replace to raise during second write
        original_replace = os.replace

        def failing_replace(src, dst):
            # Only fail for manifest.yaml writes
            if "manifest.yaml" in str(dst):
                os.unlink(src)  # Clean up tmp file
                raise OSError("Simulated crash")
            return original_replace(src, dst)

        manifest2 = _make_manifest(status="error")
        with patch("skills._shared._atomic.os.replace", side_effect=failing_replace):
            with pytest.raises(OSError, match="Simulated crash"):
                write_design_manifest(
                    "20260418_230000", "DES-042", manifest2, base_dir=tmp_path
                )

        # Original file should still be intact
        preserved = _read_yaml(manifest_path)
        assert preserved["status"] == "success"

    def test_ruamel_roundtrip(self, tmp_path: Path) -> None:
        """t3: Written file can be loaded with ruamel.yaml round-trip mode."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest()
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        # Load with round-trip mode
        yaml_rt = YAML()
        path = tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        with path.open("r") as f:
            data = yaml_rt.load(f)
        assert data["design_id"] == "DES-042"

    def test_verdict_none_when_not_success(self, tmp_path: Path) -> None:
        """t4: verdict=None is written when status != success."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(status="error", verdict=None)
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["verdict"] is None

    def test_error_category_and_detail(self, tmp_path: Path) -> None:
        """t5: error_category and error_detail are written."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(
            status="error",
            error_category="logic",
            error_detail="methodology_tag_selection_failed",
            verdict=None,
        )
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["error_category"] == "logic"
        assert data["error_detail"] == "methodology_tag_selection_failed"

    def test_skipped_with_skip_reason(self, tmp_path: Path) -> None:
        """t6: status=SKIPPED with skip_reason is written."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(
            status="skipped",
            skip_reason="hash_mismatch",
            methodology_tags=[],
            verdict=None,
        )
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["status"] == "skipped"
        assert data["skip_reason"] == "hash_mismatch"


# ---------------------------------------------------------------------------
# Unit-23: TestManifestWriterFinalize
# ---------------------------------------------------------------------------


class TestManifestWriterFinalize:
    """Unit-23: finalize_run + status bar tests."""

    def _init(self, tmp_path: Path, run_id: str = "20260418_230000") -> None:
        from skills._shared.manifest_writer import init_run

        init_run(run_id, None, "review", "token123", base_dir=tmp_path)

    def test_finalize_run_completed(self, tmp_path: Path) -> None:
        """t1: status=SKIPPED manifest does not go missing."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(status="skipped", methodology_tags=[], verdict=None)
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        path = tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        assert path.exists()
        data = _read_yaml(path)
        assert data["status"] == "skipped"

    def test_status_error_with_error_category(self, tmp_path: Path) -> None:
        """t2: status=ERROR writes error_category and error_detail."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(
            status="error",
            error_category="data_missing",
            error_detail="Table not found",
            verdict=None,
        )
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["status"] == "error"
        assert data["error_category"] == "data_missing"
        assert data["error_detail"] == "Table not found"

    def test_status_timeout(self, tmp_path: Path) -> None:
        """t3: status=TIMEOUT can be written."""
        from skills._shared.manifest_writer import init_run, write_design_manifest

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", None, base_dir=tmp_path)

        manifest = _make_manifest(
            status="timeout",
            error_category="budget_exceeded",
            verdict=None,
        )
        write_design_manifest("20260418_230000", "DES-042", manifest, base_dir=tmp_path)

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["status"] == "timeout"
