"""Integration tests for methodology_tag retry and fallback -- Integ-26.

Simulates the retry + fallback flow when methodology_tags are outside vocab.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from ruamel.yaml import YAML

JST = ZoneInfo("Asia/Tokyo")
yaml_safe = YAML(typ="safe")
yaml_out = YAML()
yaml_out.preserve_quotes = True


# =========================================================================
# Integ-26: methodology_tag retry and fallback
# =========================================================================


class TestMethodologyTagRetry:
    """Integ-26: vocab-outside tag -> retry -> fallback to descriptive."""

    @pytest.fixture(autouse=True)
    def _setup(self, insight_root: Path) -> None:
        self.insight_root = insight_root
        self.run_id = "20260420_tag_retry"
        self.design_id = "DES-TAG"
        run_dir = insight_root / "runs" / self.run_id / self.design_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Import modules
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    def test_single_retry_recovery(self) -> None:
        """1st attempt vocab-outside -> error, 2nd attempt vocab-inside -> success."""
        from skills._shared.manifest_writer import (
            MethodologyTagError,
            write_design_manifest,
        )
        from skills._shared.models import DesignManifest

        # Attempt 1: bad tags
        bad_manifest = DesignManifest(
            run_id=self.run_id,
            design_id=self.design_id,
            design_hash="sha256:tag_test",
            status="success",
            methodology_tags=["invalid_methodology_xyz"],
            verdict={
                "direction": "supports",
                "confidence": "high",
                "events_recorded": 2,
            },
            started_at=datetime.now(JST).isoformat(),
            ended_at=datetime.now(JST).isoformat(),
            elapsed_min=15.0,
            estimated_rows=1_000_000,
            error_category=None,
            error_detail=None,
        )

        with pytest.raises(MethodologyTagError):
            write_design_manifest(
                self.run_id,
                self.design_id,
                bad_manifest,
                base_dir=self.insight_root,
            )

        # Attempt 2: good tags (retry success)
        good_manifest = DesignManifest(
            run_id=self.run_id,
            design_id=self.design_id,
            design_hash="sha256:tag_test",
            status="success",
            methodology_tags=["correlation_analysis"],
            verdict={
                "direction": "supports",
                "confidence": "high",
                "events_recorded": 2,
            },
            started_at=datetime.now(JST).isoformat(),
            ended_at=datetime.now(JST).isoformat(),
            elapsed_min=15.0,
            estimated_rows=1_000_000,
            error_category=None,
            error_detail=None,
        )

        write_design_manifest(
            self.run_id,
            self.design_id,
            good_manifest,
            base_dir=self.insight_root,
        )

        # Verify manifest written successfully
        manifest_path = (
            self.insight_root / "runs" / self.run_id / self.design_id / "manifest.yaml"
        )
        assert manifest_path.exists()
        with manifest_path.open("r") as f:
            data = yaml_safe.load(f)
        assert data["status"] == "success"
        assert data["methodology_tags"] == ["correlation_analysis"]

    def test_double_failure_falls_back_descriptive(self) -> None:
        """2 consecutive vocab-outside -> fallback to [descriptive] + error_category=logic."""
        from skills._shared.manifest_writer import (
            MethodologyTagError,
            write_design_manifest,
        )
        from skills._shared.models import DesignManifest

        # Attempt 1: bad tags
        bad1 = DesignManifest(
            run_id=self.run_id,
            design_id=self.design_id,
            design_hash="sha256:double_fail",
            status="success",
            methodology_tags=["totally_wrong_tag"],
            verdict=None,
            started_at=datetime.now(JST).isoformat(),
            ended_at=datetime.now(JST).isoformat(),
            elapsed_min=15.0,
            estimated_rows=1_000_000,
            error_category=None,
            error_detail=None,
        )

        with pytest.raises(MethodologyTagError):
            write_design_manifest(
                self.run_id, self.design_id, bad1, base_dir=self.insight_root
            )

        # Attempt 2: still bad tags
        bad2 = DesignManifest(
            run_id=self.run_id,
            design_id=self.design_id,
            design_hash="sha256:double_fail",
            status="success",
            methodology_tags=["another_wrong_tag"],
            verdict=None,
            started_at=datetime.now(JST).isoformat(),
            ended_at=datetime.now(JST).isoformat(),
            elapsed_min=15.0,
            estimated_rows=1_000_000,
            error_category=None,
            error_detail=None,
        )

        with pytest.raises(MethodologyTagError):
            write_design_manifest(
                self.run_id, self.design_id, bad2, base_dir=self.insight_root
            )

        # Fallback: write with [descriptive] + error_category=logic
        fallback = DesignManifest(
            run_id=self.run_id,
            design_id=self.design_id,
            design_hash="sha256:double_fail",
            status="error",
            methodology_tags=["descriptive"],
            verdict=None,
            started_at=datetime.now(JST).isoformat(),
            ended_at=datetime.now(JST).isoformat(),
            elapsed_min=15.0,
            estimated_rows=1_000_000,
            error_category="logic",
            error_detail="methodology_tag_selection_failed",
        )

        write_design_manifest(
            self.run_id, self.design_id, fallback, base_dir=self.insight_root
        )

        manifest_path = (
            self.insight_root / "runs" / self.run_id / self.design_id / "manifest.yaml"
        )
        with manifest_path.open("r") as f:
            data = yaml_safe.load(f)
        assert data["methodology_tags"] == ["descriptive"]
        assert data["error_category"] == "logic"
        assert data["error_detail"] == "methodology_tag_selection_failed"

    def test_question_event_appended_on_double_failure(self) -> None:
        """On double failure, a question event should be recorded in journal."""
        # Simulate journal append after double failure
        journal_path = self.insight_root / "designs" / f"{self.design_id}_journal.yaml"

        # Create initial journal
        initial_journal = {
            "design_id": self.design_id,
            "events": [
                {
                    "id": f"{self.design_id}-E01",
                    "type": "observe",
                    "content": "Initial observation",
                }
            ],
        }
        with journal_path.open("w") as f:
            yaml_out.dump(initial_journal, f)

        # Load and append question event (simulating batch agent behavior)
        with journal_path.open("r") as f:
            journal = yaml_safe.load(f)

        existing_events = journal.get("events", [])
        max_id = len(existing_events)
        question_event = {
            "id": f"{self.design_id}-E{max_id + 1:02d}",
            "type": "question",
            "content": "methodology_tag_selection_failed: "
            "2 consecutive attempts produced vocab-outside tags",
            "metadata": {
                "error_category": "logic",
                "error_detail": "methodology_tag_selection_failed",
            },
        }
        existing_events.append(question_event)
        journal["events"] = existing_events

        with journal_path.open("w") as f:
            yaml_out.dump(journal, f)

        # Verify
        with journal_path.open("r") as f:
            final_journal = yaml_safe.load(f)

        events = final_journal["events"]
        question_events = [e for e in events if e["type"] == "question"]
        assert len(question_events) >= 1
        assert "methodology_tag_selection_failed" in question_events[-1]["content"]
