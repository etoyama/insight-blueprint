"""Crash recovery: detect incomplete runs and finalize them.

Scans ``.insight/runs/*/run.yaml`` for non-completed runs and provides
helpers to mark unfinished designs as incomplete.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

from skills._shared.manifest_writer import (
    DesignManifest,
    RunStatus,
    finalize_run,
    write_design_manifest,
)
from skills._shared.models import RunRef

JST = ZoneInfo("Asia/Tokyo")
_DEFAULT_BASE_DIR = Path(".insight")

_UNFINISHED_STATUSES = frozenset({"incomplete", "running", None})


def detect_incomplete(base_dir: Path = _DEFAULT_BASE_DIR) -> list[RunRef]:
    """Scan ``.insight/runs/*/run.yaml`` and return non-completed runs.

    Results are sorted by ``started_at`` descending (newest first).
    """
    runs_dir = base_dir / "runs"
    if not runs_dir.exists():
        return []

    yaml = YAML(typ="safe")
    refs: list[RunRef] = []

    for run_yaml_path in sorted(runs_dir.glob("*/run.yaml")):
        with run_yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.load(f)
        if not isinstance(data, dict):
            continue

        status = data.get("status")
        if status == "completed":
            continue

        refs.append(
            RunRef(
                run_id=data.get("run_id", run_yaml_path.parent.name),
                run_yaml_path=str(run_yaml_path),
                started_at=data.get("started_at", ""),
                status=status or "unknown",
            )
        )

    # Sort descending by started_at (newest first)
    refs.sort(key=lambda r: r.started_at, reverse=True)
    return refs


def unfinished_designs(
    run_ref: RunRef,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> list[str]:
    """Return design_ids that are missing a manifest or have incomplete status.

    Reads the token's ``approved_designs`` to know which designs were expected.
    """
    yaml = YAML(typ="safe")
    run_yaml_path = Path(run_ref.run_yaml_path)
    with run_yaml_path.open("r", encoding="utf-8") as f:
        run_data = yaml.load(f)

    token_id = run_data.get("premortem_token")
    if not token_id:
        return []

    # Load token to get approved design list
    token_path = base_dir / "premortem" / f"{token_id}.yaml"
    if not token_path.exists():
        return []

    with token_path.open("r", encoding="utf-8") as f:
        token_data = yaml.load(f)

    approved = token_data.get("approved_designs", [])
    unfinished: list[str] = []

    for entry in approved:
        design_id = entry.get("design_id", "")
        manifest_path = base_dir / "runs" / run_ref.run_id / design_id / "manifest.yaml"

        if not manifest_path.exists():
            unfinished.append(design_id)
            continue

        with manifest_path.open("r", encoding="utf-8") as f:
            manifest_data = yaml.load(f)

        status = (
            manifest_data.get("status") if isinstance(manifest_data, dict) else None
        )
        if status in _UNFINISHED_STATUSES:
            unfinished.append(design_id)

    return unfinished


def finalize_incomplete(
    run_id: str,
    design_ids: list[str],
    reason: str,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> None:
    """Mark each design as incomplete and update run.yaml status.

    Uses ``manifest_writer`` for atomic writes.
    """
    now = datetime.now(JST)

    for design_id in design_ids:
        manifest = DesignManifest(
            run_id=run_id,
            design_id=design_id,
            design_hash="",
            status="incomplete",
            methodology_tags=[],
            verdict=None,
            started_at=now.isoformat(),
            ended_at=now.isoformat(),
            elapsed_min=None,
            estimated_rows=None,
            error_category=None,
            error_detail=None,
            skip_reason=reason,
        )
        write_design_manifest(run_id, design_id, manifest, base_dir=base_dir)

    finalize_run(run_id, RunStatus.INCOMPLETE, 0.0, now, base_dir=base_dir)
