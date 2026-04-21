"""Integration tests for mode x risk matrix -- Integ-23.

Table-driven parametrize over 3 modes x 5 risk levels = 15 combinations.
Each test invokes cli.py via subprocess and asserts exit code + token contents.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.integration.conftest import (
    build_premortem_payload,
    run_premortem_cli,
)

yaml = YAML(typ="safe")


# ---------------------------------------------------------------------------
# Matrix definition
# ---------------------------------------------------------------------------

# (mode, risk_label, source_checks_override, expected_exit, in_approved, in_skipped, note)
# For manual mode, --yes is passed but stdin is not a TTY, so cli.py exits non-zero.
# We encode that as expected_exit=1 for manual (interactive failure).

_MATRIX = [
    # manual mode -- requires interactive, --yes over subprocess fails
    ("manual", "LOW", {"estimated_rows": 100_000}, 1, False, False, "interactive_fail"),
    (
        "manual",
        "MEDIUM",
        {"estimated_rows": 100_000},
        1,
        False,
        False,
        "interactive_fail",
    ),
    (
        "manual",
        "HIGH",
        {"estimated_rows": 50_000_000},
        1,
        False,
        False,
        "interactive_fail",
    ),
    (
        "manual",
        "HARD_BLOCK",
        {"source_registered": False, "estimated_rows": 100},
        1,
        False,
        False,
        "interactive_fail",
    ),
    (
        "manual",
        "SKIP",
        {"estimated_rows": 100_000},
        1,
        False,
        False,
        "interactive_fail",
    ),
    # review mode
    ("review", "LOW", {"estimated_rows": 100_000}, 0, True, False, "auto_approved"),
    ("review", "MEDIUM", {"estimated_rows": 100_000}, 0, True, False, "auto_approved"),
    ("review", "HIGH", {"estimated_rows": 50_000_000}, 2, False, False, "blocked_high"),
    (
        "review",
        "HARD_BLOCK",
        {"source_registered": False, "estimated_rows": 100},
        0,
        False,
        True,
        "hard_block_skipped",
    ),
    ("review", "SKIP", {"estimated_rows": 100_000}, 0, False, False, "terminal_skip"),
    # auto mode
    ("auto", "LOW", {"estimated_rows": 100_000}, 0, True, False, "auto_approved"),
    ("auto", "MEDIUM", {"estimated_rows": 100_000}, 0, True, False, "auto_approved"),
    (
        "auto",
        "HIGH",
        {"estimated_rows": 50_000_000},
        0,
        True,
        False,
        "high_approved_warning",
    ),
    (
        "auto",
        "HARD_BLOCK",
        {"source_registered": False, "estimated_rows": 100},
        0,
        False,
        True,
        "hard_block_skipped",
    ),
    ("auto", "SKIP", {"estimated_rows": 100_000}, 0, False, False, "terminal_skip"),
]


def _make_id(mode: str, risk: str, note: str) -> str:
    return f"{mode}_{risk}_{note}"


# =========================================================================
# Integ-23: mode x risk full matrix
# =========================================================================


class TestModeRiskMatrix:
    """Integ-23: automation mode x risk level full combination test."""

    @pytest.mark.parametrize(
        "mode,risk_label,sc_override,expected_exit,in_approved,in_skipped,note",
        _MATRIX,
        ids=[_make_id(m, r, n) for m, r, _, _, _, _, n in _MATRIX],
    )
    def test_mode_risk_combination(
        self,
        insight_root: Path,
        config_review_a: Path,
        mode: str,
        risk_label: str,
        sc_override: dict,
        expected_exit: int,
        in_approved: bool,
        in_skipped: bool,
        note: str,
    ) -> None:
        base_dir = insight_root
        cwd = insight_root.parent
        design_id = f"DES-{mode.upper()}-{risk_label}"

        # Build design
        status = "analyzing"
        if risk_label == "SKIP":
            status = "supported"  # terminal status -> SKIP

        designs = [
            {
                "id": design_id,
                "hypothesis": f"test {mode} {risk_label}",
                "intent": "exploratory",
                "methodology": "test",
                "source_ids": [f"src_{risk_label.lower()}"],
                "metrics": [],
                "acceptance_criteria": [],
                "status": status,
                "next_action": {"type": "batch_execute"},
            }
        ]

        payload = build_premortem_payload(designs, {design_id: sc_override})

        result = run_premortem_cli(
            ["--queued", "--yes", "--mode", mode, "--base-dir", str(base_dir)],
            payload,
            cwd=cwd,
        )

        assert result.returncode == expected_exit, (
            f"[{mode}/{risk_label}] Expected exit {expected_exit}, "
            f"got {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # For manual mode, no token is issued (interactive fail)
        if mode == "manual":
            return

        # For review + HIGH (exit 2), no token is issued
        if expected_exit == 2:
            tokens = list((base_dir / "premortem").glob("*.yaml"))
            assert len(tokens) == 0, "Token should not be issued on exit 2"
            return

        # For SKIP designs (terminal status), no designs in queue
        if risk_label == "SKIP":
            # Token may be issued but design should not be in either list
            tokens = list((base_dir / "premortem").glob("*.yaml"))
            if tokens:
                with tokens[0].open("r") as f:
                    data = yaml.load(f)
                approved_ids = {
                    d["design_id"] for d in data.get("approved_designs", [])
                }
                skipped_ids = {d["design_id"] for d in data.get("skipped_designs", [])}
                assert design_id not in approved_ids
                assert design_id not in skipped_ids
            return

        # Check token contents for non-manual, non-exit-2 cases
        tokens = list((base_dir / "premortem").glob("*.yaml"))
        assert len(tokens) >= 1, f"Expected token for {mode}/{risk_label}"

        with tokens[0].open("r") as f:
            data = yaml.load(f)

        approved_ids = {d["design_id"] for d in data.get("approved_designs", [])}
        skipped_ids = {d["design_id"] for d in data.get("skipped_designs", [])}

        if in_approved:
            assert design_id in approved_ids, (
                f"[{mode}/{risk_label}] Expected in approved, found: {approved_ids}"
            )
        if in_skipped:
            assert design_id in skipped_ids, (
                f"[{mode}/{risk_label}] Expected in skipped, found: {skipped_ids}"
            )
        if not in_approved and not in_skipped:
            assert design_id not in approved_ids
            assert design_id not in skipped_ids
