"""Shared pytest fixtures."""

from pathlib import Path

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
