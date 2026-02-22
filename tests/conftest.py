"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Return a temporary project directory with .insight/ initialized."""
    from insight_blueprint.storage.project import init_project

    init_project(tmp_path)
    return tmp_path
