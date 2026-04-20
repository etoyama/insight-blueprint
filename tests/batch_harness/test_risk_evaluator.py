"""Unit-01 to Unit-07: risk_evaluator decision tree tests.

25+ test cases covering:
  Unit-01 (5): terminal status -> SKIP
  Unit-02 (6): HARD_BLOCK conditions
  Unit-03 (3): history-based HIGH (extrapolated time)
  Unit-04 (4): history-based HIGH (success rate)
  Unit-05 (2): history-based MEDIUM
  Unit-06 (3): static fallback HIGH
  Unit-07 (2): static fallback MEDIUM
"""

from __future__ import annotations

import pytest

from skills._shared.models import (
    HistoryStats,
    PremortemConfig,
    RiskLevel,
    SourceChecks,
)
from skills.premortem.lib.risk_evaluator import evaluate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_config(**overrides: object) -> PremortemConfig:
    """PremortemConfig with defaults, overridable via kwargs."""
    defaults = {
        "time_high_min": 120,
        "time_medium_min": 45,
        "history_min_samples": 3,
        "buffer": 1.3,
        "success_rate_high_threshold": 0.6,
        "static_rows_high": 10_000_000,
        "token_ttl_hours": 24,
    }
    defaults.update(overrides)
    return PremortemConfig(**defaults)  # type: ignore[arg-type]


def _good_source_checks(estimated_rows: int = 1_000_000) -> SourceChecks:
    """All checks pass."""
    return SourceChecks(
        source_registered=True,
        location_ok=True,
        allowlist_ok=True,
        estimated_rows=estimated_rows,
    )


def _sufficient_history(
    n: int = 5,
    median_elapsed_min: float = 30.0,
    median_estimated_rows: float = 1_000_000.0,
    success_rate: float = 1.0,
) -> HistoryStats:
    return HistoryStats(
        n=n,
        median_elapsed_min=median_elapsed_min,
        median_estimated_rows=median_estimated_rows,
        success_rate=success_rate,
    )


def _no_history() -> HistoryStats:
    return HistoryStats(
        n=0, median_elapsed_min=None, median_estimated_rows=None, success_rate=None
    )


def _insufficient_history(n: int = 2) -> HistoryStats:
    return HistoryStats(
        n=n,
        median_elapsed_min=20.0,
        median_estimated_rows=500_000.0,
        success_rate=1.0,
    )


# ---------------------------------------------------------------------------
# Unit-01: terminal status -> SKIP
# ---------------------------------------------------------------------------


class TestRiskEvaluatorTerminalStatus:
    """Unit-01: status in {supported, rejected, inconclusive} -> SKIP."""

    def test_supported_returns_skip(self) -> None:
        result = evaluate(
            design={"status": "supported"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(),
        )
        assert result.level == RiskLevel.SKIP
        assert "terminal status" in result.reasons[0]

    def test_rejected_returns_skip(self) -> None:
        result = evaluate(
            design={"status": "rejected"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(),
        )
        assert result.level == RiskLevel.SKIP

    def test_inconclusive_returns_skip(self) -> None:
        result = evaluate(
            design={"status": "inconclusive"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(),
        )
        assert result.level == RiskLevel.SKIP

    def test_analyzing_not_skipped(self) -> None:
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=5_000_000),
        )
        assert result.level != RiskLevel.SKIP

    def test_in_review_not_skipped(self) -> None:
        result = evaluate(
            design={"status": "in_review"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=5_000_000),
        )
        assert result.level != RiskLevel.SKIP


# ---------------------------------------------------------------------------
# Unit-02: HARD_BLOCK conditions
# ---------------------------------------------------------------------------


class TestRiskEvaluatorHardBlock:
    """Unit-02: HARD_BLOCK conditions (source/allowlist/location)."""

    def test_source_not_registered_hard_block(self) -> None:
        checks = SourceChecks(
            source_registered=False,
            location_ok=True,
            allowlist_ok=True,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HARD_BLOCK
        assert any("source not registered" in r for r in result.reasons)

    def test_package_not_in_allowlist_hard_block(self) -> None:
        checks = SourceChecks(
            source_registered=True,
            location_ok=True,
            allowlist_ok=False,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HARD_BLOCK
        assert any("package outside allowlist" in r for r in result.reasons)

    def test_bq_location_mismatch_hard_block(self) -> None:
        checks = SourceChecks(
            source_registered=True,
            location_ok=False,
            allowlist_ok=True,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HARD_BLOCK
        assert any("BQ location mismatch" in r for r in result.reasons)

    def test_multiple_hard_block_reasons_all_listed(self) -> None:
        checks = SourceChecks(
            source_registered=False,
            location_ok=False,
            allowlist_ok=False,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HARD_BLOCK
        assert len(result.reasons) >= 3

    def test_all_checks_pass_not_hard_block(self) -> None:
        result = evaluate(
            design={"status": "analyzing"},
            history=_sufficient_history(),
            config=_default_config(),
            source_checks=_good_source_checks(),
        )
        assert result.level != RiskLevel.HARD_BLOCK

    def test_allowlist_read_failure_high_with_flag(self) -> None:
        """Error #10: allowlist_ok=None -> HIGH + flag=allowlist_check_failed."""
        checks = SourceChecks(
            source_registered=True,
            location_ok=True,
            allowlist_ok=None,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_sufficient_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH
        assert "allowlist_check_failed" in result.flags

    def test_allowlist_yaml_read_failure_produces_none_flag(self) -> None:
        """Task 7.2: YAML read failure scenario.

        When ``allowlist_loader.load_allowlist`` raises ``AllowlistLoadError``,
        the caller sets ``allowlist_ok=None``.  This test verifies that the
        risk_evaluator correctly produces HIGH + allowlist_check_failed for that
        scenario -- the same path as the test above, but explicitly named for the
        YAML-failure use case (I-3 improvement).
        """
        checks = SourceChecks(
            source_registered=True,
            location_ok=True,
            allowlist_ok=None,
            estimated_rows=500_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_sufficient_history(
                n=5,
                median_elapsed_min=10.0,
                median_estimated_rows=1_000_000.0,
                success_rate=0.9,
            ),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH
        assert "allowlist_check_failed" in result.flags
        # Verify it is flagged as API failure, not HARD_BLOCK
        assert result.level != RiskLevel.HARD_BLOCK


# ---------------------------------------------------------------------------
# Unit-03: history-based HIGH (extrapolated time)
# ---------------------------------------------------------------------------


class TestRiskEvaluatorHistoryHighTime:
    """Unit-03: extrapolated time exceeds time_high_min -> HIGH."""

    def test_extrapolated_time_exceeds_high_threshold(self) -> None:
        """n=3, median=60, rows=2x -> 60*2*1.3=156 > 120 -> HIGH."""
        history = _sufficient_history(
            n=3,
            median_elapsed_min=60.0,
            median_estimated_rows=1_000_000.0,
            success_rate=1.0,
        )
        checks = _good_source_checks(estimated_rows=2_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH
        assert result.extrapolated_time_min is not None
        assert result.extrapolated_time_min == pytest.approx(156.0)

    def test_boundary_extrapolated_equals_high(self) -> None:
        """Extrapolated = 120.0 exactly -> NOT HIGH (> strict comparison)."""
        # We need median * (new_rows / median_rows) * buffer = 120
        # Let median=60, buffer=1.3, ratio = 120 / (60 * 1.3) = ~1.538
        # rows = median_rows * ratio = 1_000_000 * 120 / 78 = ~1538461.54
        # Simpler: set buffer=1.0, median=60, ratio=2 => 120
        config = _default_config(buffer=1.0)
        history = _sufficient_history(
            n=3,
            median_elapsed_min=60.0,
            median_estimated_rows=1_000_000.0,
            success_rate=1.0,
        )
        checks = _good_source_checks(estimated_rows=2_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=config,
            source_checks=checks,
        )
        # 60 * (2_000_000/1_000_000) * 1.0 = 120.0 exactly
        assert result.extrapolated_time_min == pytest.approx(120.0)
        # > strict: 120 is NOT > 120, so should be MEDIUM (or lower)
        assert result.level != RiskLevel.HIGH

    def test_extrapolated_below_high_is_not_high(self) -> None:
        """Extrapolated below time_high_min -> not HIGH."""
        history = _sufficient_history(
            n=3,
            median_elapsed_min=20.0,
            median_estimated_rows=1_000_000.0,
            success_rate=1.0,
        )
        checks = _good_source_checks(estimated_rows=1_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=_default_config(),
            source_checks=checks,
        )
        # 20 * 1 * 1.3 = 26 < 120
        assert result.level != RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Unit-04: history-based HIGH (success rate)
# ---------------------------------------------------------------------------


class TestRiskEvaluatorHistorySuccessRate:
    """Unit-04: success_rate < threshold -> HIGH."""

    def test_success_rate_below_threshold_high(self) -> None:
        """3 runs, 1 success (rate=0.33) -> HIGH."""
        history = _sufficient_history(
            n=3,
            median_elapsed_min=10.0,
            median_estimated_rows=1_000_000.0,
            success_rate=1 / 3,
        )
        checks = _good_source_checks(estimated_rows=1_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH

    def test_success_rate_at_boundary_not_high(self) -> None:
        """rate=0.6 exactly -> NOT HIGH (< strict comparison)."""
        history = _sufficient_history(
            n=5,
            median_elapsed_min=10.0,
            median_estimated_rows=1_000_000.0,
            success_rate=0.6,
        )
        checks = _good_source_checks(estimated_rows=1_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=_default_config(),
            source_checks=checks,
        )
        # 0.6 is NOT < 0.6, so not HIGH from success_rate
        # extrapolated = 10 * 1 * 1.3 = 13 < 45, so LOW
        assert result.level == RiskLevel.LOW

    def test_success_rate_high_and_time_ok(self) -> None:
        """success_rate alone triggers HIGH (time is ok)."""
        history = _sufficient_history(
            n=5,
            median_elapsed_min=10.0,
            median_estimated_rows=1_000_000.0,
            success_rate=0.5,
        )
        checks = _good_source_checks(estimated_rows=1_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH

    def test_time_and_success_rate_both_trigger_high(self) -> None:
        """Both conditions met -> HIGH with multiple reasons."""
        history = _sufficient_history(
            n=3,
            median_elapsed_min=60.0,
            median_estimated_rows=1_000_000.0,
            success_rate=0.3,
        )
        checks = _good_source_checks(estimated_rows=2_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH
        # Should have reasons for both time and success_rate
        assert len(result.reasons) >= 2


# ---------------------------------------------------------------------------
# Unit-05: history-based MEDIUM
# ---------------------------------------------------------------------------


class TestRiskEvaluatorHistoryMedium:
    """Unit-05: extrapolated between medium and high -> MEDIUM."""

    def test_extrapolated_between_medium_and_high_medium(self) -> None:
        """Extrapolated = 60 (45 < x <= 120) + success_rate ok -> MEDIUM."""
        # Need: median * ratio * buffer = 60
        # median=30, ratio=30*1.3=39... let's be explicit
        # median=30, estimated=1.5M/1M=1.5, buffer=1.3 => 30*1.5*1.3=58.5
        config = _default_config(buffer=1.0)
        history = _sufficient_history(
            n=5,
            median_elapsed_min=30.0,
            median_estimated_rows=1_000_000.0,
            success_rate=0.8,
        )
        checks = _good_source_checks(estimated_rows=2_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=config,
            source_checks=checks,
        )
        # 30 * 2 * 1.0 = 60.0; 45 < 60 <= 120 -> MEDIUM
        assert result.level == RiskLevel.MEDIUM
        assert result.extrapolated_time_min == pytest.approx(60.0)

    def test_boundary_extrapolated_equals_medium(self) -> None:
        """Extrapolated = 45.0 exactly -> NOT MEDIUM (> strict comparison)."""
        config = _default_config(buffer=1.0)
        history = _sufficient_history(
            n=5,
            median_elapsed_min=22.5,
            median_estimated_rows=1_000_000.0,
            success_rate=0.8,
        )
        checks = _good_source_checks(estimated_rows=2_000_000)
        result = evaluate(
            design={"status": "analyzing"},
            history=history,
            config=config,
            source_checks=checks,
        )
        # 22.5 * 2 * 1.0 = 45.0 exactly; 45 is NOT > 45, so LOW
        assert result.extrapolated_time_min == pytest.approx(45.0)
        assert result.level == RiskLevel.LOW


# ---------------------------------------------------------------------------
# Unit-06: static fallback HIGH
# ---------------------------------------------------------------------------


class TestRiskEvaluatorStaticHigh:
    """Unit-06: history insufficient + rows > static_rows_high -> HIGH."""

    def test_n_zero_rows_above_threshold_high_with_flag(self) -> None:
        """n=0, rows=20M -> HIGH + flag=history_insufficient."""
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=20_000_000),
        )
        assert result.level == RiskLevel.HIGH
        assert "history_insufficient" in result.flags

    def test_n_two_rows_above_threshold_high_with_flag(self) -> None:
        """n=2 (insufficient), rows=15M -> HIGH + flag."""
        result = evaluate(
            design={"status": "analyzing"},
            history=_insufficient_history(n=2),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=15_000_000),
        )
        assert result.level == RiskLevel.HIGH
        assert "history_insufficient" in result.flags

    def test_flag_history_insufficient_always_present(self) -> None:
        """Static fallback always includes history_insufficient flag."""
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=5_000_000),
        )
        # rows <= 10M -> MEDIUM, but flag must still be present
        assert "history_insufficient" in result.flags


# ---------------------------------------------------------------------------
# Unit-07: static fallback MEDIUM
# ---------------------------------------------------------------------------


class TestRiskEvaluatorStaticMedium:
    """Unit-07: history insufficient + rows <= static_rows_high -> MEDIUM."""

    def test_n_zero_rows_below_threshold_medium_with_flag(self) -> None:
        """n=0, rows=5M -> MEDIUM + flag=history_insufficient."""
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=5_000_000),
        )
        assert result.level == RiskLevel.MEDIUM
        assert "history_insufficient" in result.flags

    def test_boundary_rows_equals_threshold_medium(self) -> None:
        """rows=10M exactly -> MEDIUM (> strict comparison, equal is MEDIUM side)."""
        result = evaluate(
            design={"status": "analyzing"},
            history=_no_history(),
            config=_default_config(),
            source_checks=_good_source_checks(estimated_rows=10_000_000),
        )
        assert result.level == RiskLevel.MEDIUM
        assert "history_insufficient" in result.flags


# ---------------------------------------------------------------------------
# Unit-03 extra: Error #9/#10 (API failure)
# ---------------------------------------------------------------------------


class TestRiskEvaluatorApiFailure:
    """Unit-03 (Error #9/#10): API failure -> HIGH + flags."""

    def test_location_check_failed_high(self) -> None:
        """location_ok=None -> HIGH + flag=location_check_failed."""
        checks = SourceChecks(
            source_registered=True,
            location_ok=None,
            allowlist_ok=True,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_sufficient_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH
        assert "location_check_failed" in result.flags

    def test_allowlist_check_failed_high(self) -> None:
        """allowlist_ok=None -> HIGH + flag=allowlist_check_failed."""
        checks = SourceChecks(
            source_registered=True,
            location_ok=True,
            allowlist_ok=None,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_sufficient_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HIGH
        assert "allowlist_check_failed" in result.flags

    def test_hard_block_takes_priority_over_api_failure(self) -> None:
        """location_ok=None + source_registered=False -> HARD_BLOCK wins."""
        checks = SourceChecks(
            source_registered=False,
            location_ok=None,
            allowlist_ok=True,
            estimated_rows=1_000_000,
        )
        result = evaluate(
            design={"status": "analyzing"},
            history=_sufficient_history(),
            config=_default_config(),
            source_checks=checks,
        )
        assert result.level == RiskLevel.HARD_BLOCK
