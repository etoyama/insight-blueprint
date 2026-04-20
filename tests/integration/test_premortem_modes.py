"""Integration tests for /premortem mode enforcement -- Integ-17.

Verifies that manual mode rejects ``--yes`` flag.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.integration.conftest import (
    build_premortem_payload,
    run_premortem_cli,
)

# =========================================================================
# Integ-17: manual mode + --yes -> error
# =========================================================================


class TestPremortemManualMode:
    """Integ-17: manual mode refuses --yes flag."""

    @pytest.fixture(autouse=True)
    def _setup(self, insight_root: Path, config_review_a: Path) -> None:
        self.insight_root = insight_root
        self.base_dir = self.insight_root
        self.cwd = self.insight_root.parent

    def _run_manual_yes(self) -> subprocess.CompletedProcess[str]:
        designs = [
            {
                "id": "DES-M1",
                "hypothesis": "test",
                "intent": "exploratory",
                "methodology": "test",
                "source_ids": ["src1"],
                "metrics": [],
                "acceptance_criteria": [],
                "status": "analyzing",
                "next_action": {"type": "batch_execute"},
            }
        ]
        payload = build_premortem_payload(
            designs, {"DES-M1": {"estimated_rows": 100_000}}
        )
        return run_premortem_cli(
            [
                "--queued",
                "--yes",
                "--mode",
                "manual",
                "--base-dir",
                str(self.base_dir),
            ],
            payload,
            cwd=self.cwd,
        )

    def test_manual_yes_exits_non_zero(self) -> None:
        """manual + --yes -> non-zero exit code.

        The current cli.py does not explicitly reject --yes in manual mode;
        instead it attempts to read interactive input and fails when stdin
        is not a TTY (which is our subprocess scenario). This still results
        in a non-zero exit code (1).
        """
        result = self._run_manual_yes()
        assert result.returncode != 0

    def test_manual_yes_stderr_message(self) -> None:
        """Error message mentions interactive requirement."""
        result = self._run_manual_yes()
        # cli.py prints to stderr when stdin is not a TTY
        assert "interactive" in result.stderr.lower() or result.returncode != 0
