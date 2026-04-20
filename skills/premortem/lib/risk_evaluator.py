"""Risk evaluator: pure-function decision tree for premortem risk assessment.

No I/O — all inputs are passed as arguments (AC-2.1 through AC-2.6).
"""

from __future__ import annotations

from skills._shared.models import (
    HistoryStats,
    PremortemConfig,
    RiskDecision,
    RiskLevel,
    SourceChecks,
)

_TERMINAL_STATUSES = frozenset({"supported", "rejected", "inconclusive"})


def evaluate(
    design: dict,
    history: HistoryStats,
    config: PremortemConfig,
    source_checks: SourceChecks,
) -> RiskDecision:
    """Evaluate risk for a single design.

    Decision tree (priority order):
      1. Terminal status -> SKIP
      2. HARD_BLOCK (source/allowlist/location explicit False)
      3. API failure (location/allowlist None) -> HIGH + flags
      4. History sufficient (n >= min_samples) -> extrapolation
      5. History insufficient -> static fallback

    Parameters
    ----------
    design:
        Design dict with at least a ``status`` key.
    history:
        Aggregated stats from past runs for the same source_ids.
    config:
        Premortem thresholds and parameters.
    source_checks:
        Results of source pre-flight checks.  ``None`` means API failure
        (not "check not needed" -- caller passes ``True`` when check is
        unnecessary).

    Returns
    -------
    RiskDecision
    """
    # ------------------------------------------------------------------
    # 1. Terminal status -> SKIP
    # ------------------------------------------------------------------
    status = design.get("status", "")
    if status in _TERMINAL_STATUSES:
        return RiskDecision(
            level=RiskLevel.SKIP,
            reasons=["terminal status"],
            flags=[],
            extrapolated_time_min=None,
        )

    # ------------------------------------------------------------------
    # 2. HARD_BLOCK conditions (explicit False)
    # ------------------------------------------------------------------
    hard_block_reasons: list[str] = []

    if source_checks.source_registered is False:
        hard_block_reasons.append("source not registered")

    if source_checks.allowlist_ok is False:
        hard_block_reasons.append("package outside allowlist")

    if source_checks.location_ok is False:
        hard_block_reasons.append("BQ location mismatch")

    if hard_block_reasons:
        return RiskDecision(
            level=RiskLevel.HARD_BLOCK,
            reasons=hard_block_reasons,
            flags=[],
            extrapolated_time_min=None,
        )

    # ------------------------------------------------------------------
    # 3. API failure (None = check attempted but failed)
    # ------------------------------------------------------------------
    api_failure_flags: list[str] = []
    api_failure_reasons: list[str] = []

    if source_checks.location_ok is None:
        api_failure_flags.append("location_check_failed")
        api_failure_reasons.append("BQ location check failed (API error)")

    if source_checks.allowlist_ok is None:
        api_failure_flags.append("allowlist_check_failed")
        api_failure_reasons.append("allowlist check failed (read error)")

    if api_failure_flags:
        return RiskDecision(
            level=RiskLevel.HIGH,
            reasons=api_failure_reasons,
            flags=api_failure_flags,
            extrapolated_time_min=None,
        )

    # ------------------------------------------------------------------
    # 4. History sufficient (n >= min_samples)
    # ------------------------------------------------------------------
    if history.n >= config.history_min_samples:
        return _evaluate_with_history(history, config, source_checks)

    # ------------------------------------------------------------------
    # 5. History insufficient -> static fallback
    # ------------------------------------------------------------------
    return _evaluate_static_fallback(config, source_checks)


def _evaluate_with_history(
    history: HistoryStats,
    config: PremortemConfig,
    source_checks: SourceChecks,
) -> RiskDecision:
    """Extrapolation-based risk when history is sufficient."""
    assert history.median_elapsed_min is not None
    assert history.median_estimated_rows is not None
    assert history.success_rate is not None

    estimated_rows = source_checks.estimated_rows or 0

    extrapolated = (
        history.median_elapsed_min
        * (estimated_rows / history.median_estimated_rows)
        * config.buffer
    )

    reasons: list[str] = []
    is_high = False

    # Time-based HIGH
    if extrapolated > config.time_high_min:
        reasons.append(
            f"extrapolated time {extrapolated:.1f} min > {config.time_high_min} min"
        )
        is_high = True

    # Success-rate-based HIGH
    if history.success_rate < config.success_rate_high_threshold:
        reasons.append(
            f"success rate {history.success_rate:.2f} < {config.success_rate_high_threshold}"
        )
        is_high = True

    if is_high:
        return RiskDecision(
            level=RiskLevel.HIGH,
            reasons=reasons,
            flags=[],
            extrapolated_time_min=extrapolated,
        )

    # MEDIUM
    if extrapolated > config.time_medium_min:
        return RiskDecision(
            level=RiskLevel.MEDIUM,
            reasons=[
                f"extrapolated time {extrapolated:.1f} min > {config.time_medium_min} min"
            ],
            flags=[],
            extrapolated_time_min=extrapolated,
        )

    # LOW
    return RiskDecision(
        level=RiskLevel.LOW,
        reasons=[f"extrapolated time {extrapolated:.1f} min within safe range"],
        flags=[],
        extrapolated_time_min=extrapolated,
    )


def _evaluate_static_fallback(
    config: PremortemConfig,
    source_checks: SourceChecks,
) -> RiskDecision:
    """Static fallback when history is insufficient."""
    estimated_rows = source_checks.estimated_rows or 0

    if estimated_rows > config.static_rows_high:
        return RiskDecision(
            level=RiskLevel.HIGH,
            reasons=[
                f"estimated rows {estimated_rows:,} > {config.static_rows_high:,} (history insufficient)"
            ],
            flags=["history_insufficient"],
            extrapolated_time_min=None,
        )

    return RiskDecision(
        level=RiskLevel.MEDIUM,
        reasons=[
            f"estimated rows {estimated_rows:,} <= {config.static_rows_high:,} (history insufficient, cautious)"
        ],
        flags=["history_insufficient"],
        extrapolated_time_min=None,
    )
