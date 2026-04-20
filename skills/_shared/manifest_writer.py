"""Run and per-design manifest I/O with atomic writes and vocab validation.

Files written:
  - ``.insight/runs/{run_id}/run.yaml``
  - ``.insight/runs/{run_id}/{design_id}/manifest.yaml``
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

from skills._shared._atomic import atomic_write_yaml
from skills._shared.models import DesignManifest, RunStatus

JST = ZoneInfo("Asia/Tokyo")
_DEFAULT_BASE_DIR = Path(".insight")


class MethodologyTagError(ValueError):
    """Raised when methodology_tags contain values outside the predefined vocab."""


# ---------------------------------------------------------------------------
# Vocab helpers
# ---------------------------------------------------------------------------


def load_vocab(base_dir: Path = _DEFAULT_BASE_DIR) -> set[str]:
    """Load methodology vocabulary from ``.insight/rules/methodology_vocab.yaml``."""
    vocab_path = base_dir / "rules" / "methodology_vocab.yaml"
    yaml = YAML(typ="safe")
    with vocab_path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    return set(data.get("methodology_tags", []))


def _validate_tags(tags: list[str], vocab: set[str]) -> None:
    """Raise MethodologyTagError if any tag is outside vocab."""
    if not tags:
        return  # empty list is OK
    invalid = set(tags) - vocab
    if invalid:
        raise MethodologyTagError(f"Tags not in methodology_vocab: {sorted(invalid)}")


# ---------------------------------------------------------------------------
# run.yaml lifecycle
# ---------------------------------------------------------------------------


def _run_yaml_path(run_id: str, base_dir: Path) -> Path:
    return base_dir / "runs" / run_id / "run.yaml"


def _load_run_yaml(run_id: str, base_dir: Path) -> dict:
    path = _run_yaml_path(run_id, base_dir)
    if not path.exists():
        raise FileNotFoundError(f"run.yaml not found: {path}")
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f)


def init_run(
    run_id: str,
    session_id: str | None,
    automation_mode: str,
    token_id: str | None,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> None:
    """Create ``run.yaml`` with initial fields (status=running)."""
    now = datetime.now(JST)
    data = {
        "run_id": run_id,
        "session_id": session_id,
        "started_at": now.isoformat(),
        "automation_mode": automation_mode,
        "premortem_token": token_id,
        "status": RunStatus.RUNNING.value,
    }
    atomic_write_yaml(_run_yaml_path(run_id, base_dir), data)


def update_run_session_id(
    run_id: str,
    session_id: str,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> None:
    """Update ``session_id`` in an existing run.yaml, preserving all other fields."""
    data = _load_run_yaml(run_id, base_dir)
    data["session_id"] = session_id
    atomic_write_yaml(_run_yaml_path(run_id, base_dir), data)


def finalize_run(
    run_id: str,
    status: RunStatus,
    cost_total_usd: float,
    ended_at: datetime,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> None:
    """Finalize a run by adding ended_at, status, and cost_total_usd."""
    data = _load_run_yaml(run_id, base_dir)
    data["ended_at"] = ended_at.isoformat()
    data["status"] = status.value
    data["cost_total_usd"] = cost_total_usd
    atomic_write_yaml(_run_yaml_path(run_id, base_dir), data)


# ---------------------------------------------------------------------------
# Per-design manifest
# ---------------------------------------------------------------------------


def write_design_manifest(
    run_id: str,
    design_id: str,
    manifest: DesignManifest,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> None:
    """Write per-design manifest atomically after vocab validation."""
    vocab = load_vocab(base_dir)
    _validate_tags(manifest.methodology_tags, vocab)

    data = asdict(manifest)
    path = base_dir / "runs" / run_id / design_id / "manifest.yaml"
    atomic_write_yaml(path, data)
