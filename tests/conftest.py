"""Shared pytest fixtures."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.reviews import ReviewService
from insight_blueprint.models.design import AnalysisDesign, DesignStatus


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Return a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project

    init_project(tmp_path)
    return tmp_path


@pytest.fixture
def design_service(tmp_path: Path) -> DesignService:
    """Return a DesignService backed by a temporary directory."""
    (tmp_path / ".insight" / "designs").mkdir(parents=True)
    (tmp_path / ".insight" / "rules").mkdir(parents=True, exist_ok=True)
    return DesignService(tmp_path)


@pytest.fixture
def review_service(tmp_path: Path, design_service: DesignService) -> ReviewService:
    """Return a ReviewService backed by a temporary directory."""
    return ReviewService(tmp_path, design_service)


@pytest.fixture
def active_design(design_service: DesignService) -> AnalysisDesign:
    """Create and return an active design."""
    design = design_service.create_design(
        title="Active Design",
        hypothesis_statement="Test hypothesis",
        hypothesis_background="Test background",
    )
    updated = design_service.update_design(design.id, status=DesignStatus.active)
    assert updated is not None
    return updated


@pytest.fixture
def pending_design(
    design_service: DesignService,
    review_service: ReviewService,
    active_design: AnalysisDesign,
) -> AnalysisDesign:
    """Create and return a design in pending_review status."""
    result = review_service.submit_for_review(active_design.id)
    assert result is not None
    return result


# ---------------------------------------------------------------------------
# Inline Review Comments fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def review_batch_data() -> dict:
    """Valid ReviewBatch submission request data."""
    return {
        "status_after": "supported",
        "reviewer": "analyst",
        "comments": [
            {
                "comment": "Hypothesis indicator is vague",
                "target_section": "hypothesis_statement",
                "target_content": "The policy improves CVR",
            },
            {
                "comment": "KPI measurement period undefined",
                "target_section": "metrics",
                "target_content": {"kpi_name": "CVR", "current_value": "2.5%"},
            },
        ],
    }


def make_batch_payload(**overrides: object) -> dict:
    """Factory for batch payloads. Merge overrides into valid default."""
    base: dict = {
        "status_after": "supported",
        "reviewer": "analyst",
        "comments": [
            {
                "comment": "Test comment",
                "target_section": "hypothesis_statement",
                "target_content": "Test hypothesis",
            },
        ],
    }
    base.update(overrides)
    return base


@pytest.fixture
def non_pending_design(design_service: DesignService) -> AnalysisDesign:
    """Draft status design for rejection testing."""
    return design_service.create_design(
        title="Non-Pending Design",
        hypothesis_statement="Test hypothesis",
        hypothesis_background="Test background",
    )


@pytest.fixture
def fixed_now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Pin now_jst() to a fixed time. Patches both common and review modules."""
    fixed = datetime(2026, 3, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    monkeypatch.setattr("insight_blueprint.models.common.now_jst", lambda: fixed)
    monkeypatch.setattr("insight_blueprint.models.review.now_jst", lambda: fixed)
    return fixed


@pytest.fixture
def corrupted_reviews_yaml(tmp_path: Path) -> Path:
    """Create a corrupted reviews YAML file."""
    path = tmp_path / ".insight" / "designs" / "DES-corrupt_reviews.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("batches:\n  - invalid: [unclosed bracket", encoding="utf-8")
    return path


@pytest.fixture
def status_update_failure(
    monkeypatch: pytest.MonkeyPatch, design_service: DesignService
) -> None:
    """Force DesignService.update_design to fail (atomicity test)."""

    def fail_update(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Simulated status update failure")

    monkeypatch.setattr(design_service, "update_design", fail_update)
