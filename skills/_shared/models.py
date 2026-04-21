"""Shared data models for batch-harness-engineering.

All enums use ``StrEnum`` (member UPPER_SNAKE_CASE, value lower_snake_case).
All dataclasses are ``frozen=True``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# StrEnum definitions
# ---------------------------------------------------------------------------


class RiskLevel(StrEnum):
    """Risk classification for premortem evaluation."""

    HARD_BLOCK = "hard_block"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"


class RunStatus(StrEnum):
    """Run-level status (run.yaml)."""

    RUNNING = "running"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    ERROR = "error"
    TIMEOUT = "timeout"


class ManifestStatus(StrEnum):
    """Per-design manifest status."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    INCOMPLETE = "incomplete"


class AutomationMode(StrEnum):
    """Automation mode for batch execution."""

    MANUAL = "manual"
    REVIEW = "review"
    AUTO = "auto"
    LEGACY = "legacy"


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignHashInput:
    """Fields included in design hash computation."""

    hypothesis: str
    intent: str
    methodology: str
    source_ids: list[str]
    metrics: list[dict[str, Any]]
    acceptance_criteria: list[dict[str, Any]]


@dataclass(frozen=True)
class DesignEntry:
    """A design queue entry with full metadata."""

    id: str
    hypothesis: str
    intent: str
    methodology: str
    source_ids: list[str]
    metrics: list[dict[str, Any]]
    acceptance_criteria: list[dict[str, Any]]
    status: str
    next_action: dict[str, Any]
    created_at: str
    updated_at: str
    review_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class Token:
    """Approval token data."""

    token_id: str
    created_at: str
    expires_at: str
    approved_by: str
    automation_mode: str
    approved_designs: list[dict[str, Any]]
    skipped_designs: list[dict[str, Any]]


@dataclass(frozen=True)
class TokenVerifyResult:
    """Result of token verification."""

    ok: bool
    reason: str | None
    token: Token | None


@dataclass(frozen=True)
class HistoryStats:
    """Aggregated statistics from past runs for a given source_ids set."""

    n: int
    median_elapsed_min: float | None
    median_estimated_rows: float | None
    success_rate: float | None


@dataclass(frozen=True)
class RiskDecision:
    """Output of risk_evaluator.evaluate."""

    level: RiskLevel
    reasons: list[str]
    flags: list[str]
    extrapolated_time_min: float | None


@dataclass(frozen=True)
class SourceChecks:
    """Results of source pre-flight checks."""

    source_registered: bool
    location_ok: bool | None
    allowlist_ok: bool | None
    estimated_rows: int | None


@dataclass(frozen=True)
class PremortemConfig:
    """Premortem + batch configuration with defaults."""

    time_high_min: int = 120
    time_medium_min: int = 45
    history_min_samples: int = 3
    buffer: float = 1.3
    success_rate_high_threshold: float = 0.6
    static_rows_high: int = 10_000_000
    token_ttl_hours: int = 24
    automation: str = "review"
    approved_by_required: bool = False
    max_turns: int = 200
    max_budget_usd: int = 10


@dataclass(frozen=True)
class DesignManifest:
    """Per-design execution manifest."""

    run_id: str
    design_id: str
    design_hash: str
    status: str
    methodology_tags: list[str]
    verdict: dict[str, Any] | None
    started_at: str
    ended_at: str | None
    elapsed_min: float | None
    estimated_rows: int | None
    error_category: str | None
    error_detail: str | None
    skip_reason: str | None = None


@dataclass(frozen=True)
class RunManifest:
    """Run-level manifest (run.yaml)."""

    run_id: str
    started_at: str
    ended_at: str | None
    session_id: str | None
    automation_mode: str
    premortem_token: str | None
    status: str
    cost_total_usd: float | None
    approved_designs: list[dict[str, Any]]
    skipped_designs: list[dict[str, Any]]


@dataclass(frozen=True)
class RunRef:
    """Lightweight reference to a run for crash recovery."""

    run_id: str
    run_yaml_path: str
    started_at: str
    status: str
