"""History query: glob + YAML read for past run statistics.

No sqlite3 usage — pathlib + ruamel.yaml + statistics only (AC-4.5).
"""

from __future__ import annotations

import statistics
import warnings
from pathlib import Path

from ruamel.yaml import YAML, YAMLError

from skills._shared.models import HistoryStats

_DEFAULT_RUNS_DIR = Path(".insight/runs")


def query(
    source_ids: list[str],
    min_samples: int,
    *,
    runs_dir: Path | None = None,
) -> HistoryStats:
    """Query past manifests for runs matching *source_ids* (set equality).

    Parameters
    ----------
    source_ids:
        The source IDs to match (order-insensitive, exact set equality).
    min_samples:
        Informational minimum; the function always returns whatever data
        is available (``n`` may be less than *min_samples*).
    runs_dir:
        Override for ``.insight/runs`` root (mainly for testing).

    Returns
    -------
    HistoryStats
        Aggregated statistics.  Fields are ``None`` when computation is
        impossible (e.g. n == 0).
    """
    if runs_dir is None:
        runs_dir = _DEFAULT_RUNS_DIR

    target_set = set(source_ids)
    yaml = YAML()

    elapsed_values: list[float] = []
    rows_values: list[float] = []
    success_count = 0
    total_count = 0

    for manifest_path in sorted(runs_dir.glob("*/*/manifest.yaml")):
        try:
            with manifest_path.open("r") as f:
                data = yaml.load(f)
        except YAMLError as exc:
            warnings.warn(
                f"Skipping corrupted YAML file {manifest_path}: {exc}",
                stacklevel=2,
            )
            continue

        if data is None:
            continue

        # Extract source_ids from design_snapshot
        snapshot = data.get("design_snapshot")
        if snapshot is None:
            continue

        manifest_source_ids = snapshot.get("source_ids")
        if manifest_source_ids is None:
            continue

        # Set equality check (order-insensitive)
        if set(manifest_source_ids) != target_set:
            continue

        total_count += 1

        # Collect elapsed_min (top-level per flat contract)
        elapsed = data.get("elapsed_min")
        if elapsed is not None:
            elapsed_values.append(float(elapsed))

        # Collect estimated_rows (top-level per flat contract)
        est_rows = data.get("estimated_rows")
        if est_rows is None:
            # Backward-compat: older manifests may still have input_profile.estimated_rows
            input_profile = data.get("input_profile", {})
            est_rows = input_profile.get("estimated_rows")
        if est_rows is not None:
            rows_values.append(float(est_rows))

        # Count successes (top-level status, "completed" enum)
        status = data.get("status", "")
        if status == "completed":
            success_count += 1

    # Compute aggregates
    median_elapsed: float | None = None
    median_rows: float | None = None
    success_rate: float | None = None

    if elapsed_values:
        median_elapsed = statistics.median(elapsed_values)

    if rows_values:
        median_rows = statistics.median(rows_values)

    if total_count > 0:
        success_rate = success_count / total_count

    return HistoryStats(
        n=total_count,
        median_elapsed_min=median_elapsed,
        median_estimated_rows=median_rows,
        success_rate=success_rate,
    )
