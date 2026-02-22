"""Integration test: full round-trip from init to CRUD."""

from pathlib import Path

from insight_blueprint.core.designs import DesignService
from insight_blueprint.models.design import DesignStatus
from insight_blueprint.storage.project import init_project


def test_full_round_trip(tmp_path: Path) -> None:
    """Integration test: init -> create -> get -> list."""
    # 1. Init project
    init_project(tmp_path)
    service = DesignService(tmp_path)

    # 2. Create
    design = service.create_design(
        title="Crime Rate Analysis",
        hypothesis_statement="No positive correlation",
        hypothesis_background="Background context",
        theme_id="FP",
    )
    assert design.id == "FP-H01"

    # 3. Verify YAML file exists
    yaml_path = tmp_path / ".insight" / "designs" / "FP-H01_hypothesis.yaml"
    assert yaml_path.exists()

    # 4. Get
    retrieved = service.get_design("FP-H01")
    assert retrieved is not None
    assert retrieved.title == "Crime Rate Analysis"
    assert retrieved.id == "FP-H01"

    # 5. List
    all_designs = service.list_designs()
    assert len(all_designs) == 1
    assert all_designs[0].id == "FP-H01"

    # 6. List with status filter
    drafts = service.list_designs(status=DesignStatus.draft)
    assert len(drafts) == 1

    active = service.list_designs(status=DesignStatus.active)
    assert len(active) == 0

    # 7. Missing design returns None
    missing = service.get_design("FP-H99")
    assert missing is None
