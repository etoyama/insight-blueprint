"""Unit-19: history_query — glob + YAML read only, no sqlite3.

6 test cases covering:
  t1: empty glob → n=0, median=None, success_rate=None
  t2: source_ids exact match only (set equality)
  t3: median calculation across multiple runs (even count)
  t4: success_rate computation (SUCCESS / total)
  t5: corrupted YAML file skipped with warnings.warn
  t6: sqlite3.connect never called during query
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest import mock

from ruamel.yaml import YAML

from skills.premortem.lib.history_query import query


def _write_manifest(
    base: Path,
    run_name: str,
    design_id: str,
    source_ids: list[str],
    elapsed_min: float,
    estimated_rows: int,
    status: str = "success",
) -> Path:
    """Helper to create a manifest.yaml fixture."""
    manifest_dir = base / run_name / design_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.yaml"
    yaml = YAML()
    data = {
        "design_id": design_id,
        "run_id": run_name,
        "design_snapshot": {
            "source_ids": source_ids,
            "hash": "sha256:fake",
            "intent": "exploratory",
            "methodology": "test",
        },
        "execution": {
            "elapsed_min": elapsed_min,
            "status": status,
        },
        "input_profile": {
            "estimated_rows": estimated_rows,
        },
    }
    with manifest_path.open("w") as f:
        yaml.dump(data, f)
    return manifest_path


class TestHistoryQueryNoSqlite:
    """Unit-19: history_query tests."""

    def test_empty_history_returns_n_zero(self, tmp_path: Path) -> None:
        """t1: glob results 0 files -> n=0, median=None, success_rate=None."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        result = query(
            source_ids=["sales_raw"],
            min_samples=3,
            runs_dir=runs_dir,
        )

        assert result.n == 0
        assert result.median_elapsed_min is None
        assert result.median_estimated_rows is None
        assert result.success_rate is None

    def test_source_ids_exact_match_filter(self, tmp_path: Path) -> None:
        """t2: Only manifests with exact source_ids set match."""
        runs_dir = tmp_path / "runs"

        # Match: source_ids = ["a", "b"]
        _write_manifest(runs_dir, "run1", "DES-001", ["a", "b"], 10.0, 1000)
        # Match: same ids different order
        _write_manifest(runs_dir, "run2", "DES-002", ["b", "a"], 20.0, 2000)
        # No match: subset
        _write_manifest(runs_dir, "run3", "DES-003", ["a"], 30.0, 3000)
        # No match: superset
        _write_manifest(runs_dir, "run4", "DES-004", ["a", "b", "c"], 40.0, 4000)
        # No match: different set
        _write_manifest(runs_dir, "run5", "DES-005", ["x", "y"], 50.0, 5000)

        result = query(
            source_ids=["a", "b"],
            min_samples=3,
            runs_dir=runs_dir,
        )

        assert result.n == 2

    def test_median_calculation_three_runs(self, tmp_path: Path) -> None:
        """t3: 3 runs with elapsed_min=[10, 20, 30] -> median=20."""
        runs_dir = tmp_path / "runs"

        _write_manifest(runs_dir, "run1", "DES-001", ["src"], 10.0, 1000)
        _write_manifest(runs_dir, "run2", "DES-002", ["src"], 30.0, 3000)
        _write_manifest(runs_dir, "run3", "DES-003", ["src"], 20.0, 2000)

        result = query(
            source_ids=["src"],
            min_samples=3,
            runs_dir=runs_dir,
        )

        assert result.n == 3
        assert result.median_elapsed_min == 20.0
        assert result.median_estimated_rows == 2000.0

    def test_median_even_count(self, tmp_path: Path) -> None:
        """t3 (extension): Even number of runs -> median is average of middle two."""
        runs_dir = tmp_path / "runs"

        _write_manifest(runs_dir, "run1", "DES-001", ["src"], 10.0, 1000)
        _write_manifest(runs_dir, "run2", "DES-002", ["src"], 20.0, 2000)
        _write_manifest(runs_dir, "run3", "DES-003", ["src"], 30.0, 3000)
        _write_manifest(runs_dir, "run4", "DES-004", ["src"], 40.0, 4000)

        result = query(
            source_ids=["src"],
            min_samples=3,
            runs_dir=runs_dir,
        )

        assert result.n == 4
        assert result.median_elapsed_min == 25.0  # (20 + 30) / 2
        assert result.median_estimated_rows == 2500.0  # (2000 + 3000) / 2

    def test_success_rate_from_status(self, tmp_path: Path) -> None:
        """t4: 3 runs, 2 success + 1 error -> success_rate ~0.667."""
        runs_dir = tmp_path / "runs"

        _write_manifest(
            runs_dir, "run1", "DES-001", ["src"], 10.0, 1000, status="success"
        )
        _write_manifest(
            runs_dir, "run2", "DES-002", ["src"], 20.0, 2000, status="success"
        )
        _write_manifest(
            runs_dir, "run3", "DES-003", ["src"], 30.0, 3000, status="error"
        )

        result = query(
            source_ids=["src"],
            min_samples=3,
            runs_dir=runs_dir,
        )

        assert result.n == 3
        assert result.success_rate is not None
        assert abs(result.success_rate - 2 / 3) < 1e-9

    def test_corrupted_yaml_skipped(self, tmp_path: Path) -> None:
        """t5: Corrupted YAML files are skipped with warnings.warn."""
        runs_dir = tmp_path / "runs"

        # Valid manifest
        _write_manifest(runs_dir, "run1", "DES-001", ["src"], 10.0, 1000)

        # Corrupted manifest
        corrupt_dir = runs_dir / "run2" / "DES-002"
        corrupt_dir.mkdir(parents=True)
        corrupt_file = corrupt_dir / "manifest.yaml"
        corrupt_file.write_text("invalid: yaml: [[[broken")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = query(
                source_ids=["src"],
                min_samples=3,
                runs_dir=runs_dir,
            )

        assert result.n == 1
        assert len(w) >= 1
        assert any(
            "YAML" in str(warning.message) or "yaml" in str(warning.message)
            for warning in w
        )

    def test_no_sqlite_connect_called(self, tmp_path: Path) -> None:
        """t6: sqlite3.connect is never called during query execution."""
        runs_dir = tmp_path / "runs"

        _write_manifest(runs_dir, "run1", "DES-001", ["src"], 10.0, 1000)

        with mock.patch("sqlite3.connect") as mock_connect:
            query(
                source_ids=["src"],
                min_samples=3,
                runs_dir=runs_dir,
            )

        mock_connect.assert_not_called()
