"""Tests for skills/_shared/crash_recovery.py.

Unit-20: detect_incomplete (4 cases)
Unit-21: unfinished_designs (2 cases)
Unit-22: finalize_incomplete (3 cases)
"""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

JST = ZoneInfo("Asia/Tokyo")


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)


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


def _make_run_yaml(
    base_dir: Path,
    run_id: str,
    status: str = "running",
    started_at: str = "2026-04-18T23:00:00+09:00",
    token_id: str | None = "token_123",
) -> None:
    data = {
        "run_id": run_id,
        "session_id": "sess-abc",
        "started_at": started_at,
        "automation_mode": "review",
        "premortem_token": token_id,
        "status": status,
    }
    _write_yaml(base_dir / "runs" / run_id / "run.yaml", data)


def _make_token_yaml(
    base_dir: Path,
    token_id: str,
    approved_designs: list[dict] | None = None,
) -> None:
    data = {
        "token_id": token_id,
        "created_at": "2026-04-18T18:30:15+09:00",
        "expires_at": "2026-04-19T18:30:15+09:00",
        "approved_by": "human",
        "automation_mode": "review",
        "risk_summary": {},
        "approved_designs": approved_designs or [],
        "skipped_designs": [],
    }
    _write_yaml(base_dir / "premortem" / f"{token_id}.yaml", data)


# ---------------------------------------------------------------------------
# Unit-20: TestCrashRecoveryDetect
# ---------------------------------------------------------------------------


class TestCrashRecoveryDetect:
    """Unit-20: detect_incomplete scans run.yaml for non-completed runs."""

    def test_no_incomplete_returns_empty(self, tmp_path: Path) -> None:
        """t1: All completed -> empty list."""
        from skills._shared.crash_recovery import detect_incomplete

        _make_run_yaml(tmp_path, "20260418_230000", status="completed")
        result = detect_incomplete(base_dir=tmp_path)
        assert result == []

    def test_one_incomplete_detected(self, tmp_path: Path) -> None:
        """t2: One running run -> detected."""
        from skills._shared.crash_recovery import detect_incomplete

        _make_run_yaml(tmp_path, "20260418_230000", status="running")
        result = detect_incomplete(base_dir=tmp_path)
        assert len(result) == 1
        assert result[0].run_id == "20260418_230000"

    def test_multiple_sorted_desc(self, tmp_path: Path) -> None:
        """t3: Multiple incomplete sorted by started_at descending."""
        from skills._shared.crash_recovery import detect_incomplete

        _make_run_yaml(
            tmp_path,
            "20260417_100000",
            status="running",
            started_at="2026-04-17T10:00:00+09:00",
        )
        _make_run_yaml(
            tmp_path,
            "20260418_230000",
            status="incomplete",
            started_at="2026-04-18T23:00:00+09:00",
        )
        result = detect_incomplete(base_dir=tmp_path)
        assert len(result) == 2
        assert result[0].run_id == "20260418_230000"  # newer first
        assert result[1].run_id == "20260417_100000"

    def test_completed_not_included(self, tmp_path: Path) -> None:
        """t4: Completed run is not in the result."""
        from skills._shared.crash_recovery import detect_incomplete

        _make_run_yaml(tmp_path, "20260418_230000", status="completed")
        _make_run_yaml(tmp_path, "20260417_100000", status="running")
        result = detect_incomplete(base_dir=tmp_path)
        assert len(result) == 1
        assert result[0].run_id == "20260417_100000"


# ---------------------------------------------------------------------------
# Unit-21: TestCrashRecoveryUnfinished
# ---------------------------------------------------------------------------


class TestCrashRecoveryUnfinished:
    """Unit-21: unfinished_designs detects missing/incomplete manifests."""

    def test_manifest_missing_detected(self, tmp_path: Path) -> None:
        """t1: Design with no manifest.yaml is unfinished."""
        from skills._shared.crash_recovery import detect_incomplete, unfinished_designs

        _make_run_yaml(tmp_path, "20260418_230000", status="running")
        _make_token_yaml(
            tmp_path,
            "token_123",
            approved_designs=[
                {
                    "design_id": "DES-042",
                    "design_hash": "sha256:abc",
                    "risk_at_approval": "low",
                    "est_min": 18.0,
                }
            ],
        )

        # Create run dir but no manifest for DES-042
        (tmp_path / "runs" / "20260418_230000" / "DES-042").mkdir(
            parents=True, exist_ok=True
        )

        runs = detect_incomplete(base_dir=tmp_path)
        result = unfinished_designs(runs[0], base_dir=tmp_path)
        assert "DES-042" in result

    def test_manifest_incomplete_detected(self, tmp_path: Path) -> None:
        """t2: Design with status=incomplete is unfinished."""
        from skills._shared.crash_recovery import detect_incomplete, unfinished_designs

        _make_run_yaml(tmp_path, "20260418_230000", status="running")
        _make_token_yaml(
            tmp_path,
            "token_123",
            approved_designs=[
                {
                    "design_id": "DES-042",
                    "design_hash": "sha256:abc",
                    "risk_at_approval": "low",
                    "est_min": 18.0,
                }
            ],
        )

        # Write manifest with status=incomplete
        _write_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml",
            {"design_id": "DES-042", "status": "incomplete"},
        )

        runs = detect_incomplete(base_dir=tmp_path)
        result = unfinished_designs(runs[0], base_dir=tmp_path)
        assert "DES-042" in result


# ---------------------------------------------------------------------------
# Unit-22: TestCrashRecoveryFinalize
# ---------------------------------------------------------------------------


class TestCrashRecoveryFinalize:
    """Unit-22: finalize_incomplete writes manifest + updates run status."""

    def test_finalize_writes_manifest_incomplete(self, tmp_path: Path) -> None:
        """t1: Manifest is written with status=incomplete."""
        from skills._shared.crash_recovery import finalize_incomplete
        from skills._shared.manifest_writer import init_run

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", "token_123", base_dir=tmp_path)

        finalize_incomplete(
            run_id="20260418_230000",
            design_ids=["DES-042"],
            reason="token_expired_or_crashed",
            base_dir=tmp_path,
        )

        manifest_path = (
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert manifest_path.exists()
        data = _read_yaml(manifest_path)
        assert data["status"] == "incomplete"

    def test_skip_reason_recorded(self, tmp_path: Path) -> None:
        """t2: skip_reason is written in manifest."""
        from skills._shared.crash_recovery import finalize_incomplete
        from skills._shared.manifest_writer import init_run

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", "token_123", base_dir=tmp_path)

        finalize_incomplete(
            run_id="20260418_230000",
            design_ids=["DES-042"],
            reason="token_expired_or_crashed",
            base_dir=tmp_path,
        )

        data = _read_yaml(
            tmp_path / "runs" / "20260418_230000" / "DES-042" / "manifest.yaml"
        )
        assert data["skip_reason"] == "token_expired_or_crashed"

    def test_run_yaml_status_updated(self, tmp_path: Path) -> None:
        """t3: run.yaml status is updated to incomplete."""
        from skills._shared.crash_recovery import finalize_incomplete
        from skills._shared.manifest_writer import init_run

        _write_vocab(tmp_path)
        init_run("20260418_230000", None, "review", "token_123", base_dir=tmp_path)

        finalize_incomplete(
            run_id="20260418_230000",
            design_ids=["DES-042"],
            reason="token_expired_or_crashed",
            base_dir=tmp_path,
        )

        run_data = _read_yaml(tmp_path / "runs" / "20260418_230000" / "run.yaml")
        assert run_data["status"] == "incomplete"
