"""Tests for core/designs.py."""

from pathlib import Path

import pytest

from insight_blueprint.core.designs import DesignService
from insight_blueprint.models.design import DesignStatus


@pytest.fixture
def service(tmp_path: Path) -> DesignService:
    (tmp_path / ".insight" / "designs").mkdir(parents=True)
    return DesignService(tmp_path)


def test_create_design_returns_design_with_generated_id(
    service: DesignService,
) -> None:
    design = service.create_design(
        title="Test Hypothesis",
        hypothesis_statement="No correlation exists",
        hypothesis_background="Background info",
    )
    assert design.id == "DEFAULT-H01"
    assert design.status == DesignStatus.draft


def test_create_design_saves_yaml_file(service: DesignService, tmp_path: Path) -> None:
    service.create_design(
        title="Test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    assert (tmp_path / ".insight" / "designs" / "DEFAULT-H01_hypothesis.yaml").exists()


def test_create_design_sequential_ids(service: DesignService) -> None:
    d1 = service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )
    d2 = service.create_design(
        title="T2", hypothesis_statement="s2", hypothesis_background="b2"
    )
    d3 = service.create_design(
        title="T3", hypothesis_statement="s3", hypothesis_background="b3"
    )
    assert d1.id == "DEFAULT-H01"
    assert d2.id == "DEFAULT-H02"
    assert d3.id == "DEFAULT-H03"


def test_get_design_returns_correct_design(service: DesignService) -> None:
    created = service.create_design(
        title="Round trip",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    retrieved = service.get_design(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == created.title


def test_get_design_returns_none_for_missing_id(
    service: DesignService,
) -> None:
    result = service.get_design("FP-H99")
    assert result is None


def test_list_designs_returns_all(service: DesignService) -> None:
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )
    service.create_design(
        title="T2", hypothesis_statement="s2", hypothesis_background="b2"
    )
    designs = service.list_designs()
    assert len(designs) == 2


def test_list_designs_filtered_by_status(service: DesignService) -> None:
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )
    service.create_design(
        title="T2", hypothesis_statement="s2", hypothesis_background="b2"
    )
    drafts = service.list_designs(status=DesignStatus.draft)
    assert len(drafts) == 2
    active = service.list_designs(status=DesignStatus.active)
    assert len(active) == 0


def test_create_design_with_theme_id_uses_theme_prefix(
    service: DesignService,
) -> None:
    design = service.create_design(
        title="FP test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        theme_id="FP",
    )
    assert design.id == "FP-H01"
    assert design.theme_id == "FP"


def test_create_design_in_different_themes_number_independently(
    service: DesignService,
) -> None:
    fp1 = service.create_design(
        title="FP1",
        hypothesis_statement="s",
        hypothesis_background="b",
        theme_id="FP",
    )
    tx1 = service.create_design(
        title="TX1",
        hypothesis_statement="s",
        hypothesis_background="b",
        theme_id="TX",
    )
    fp2 = service.create_design(
        title="FP2",
        hypothesis_statement="s",
        hypothesis_background="b",
        theme_id="FP",
    )
    assert fp1.id == "FP-H01"
    assert tx1.id == "TX-H01"
    assert fp2.id == "FP-H02"


def test_create_design_with_invalid_theme_id_raises_value_error(
    service: DesignService,
) -> None:
    with pytest.raises(ValueError, match="must match"):
        service.create_design(
            title="T",
            hypothesis_statement="s",
            hypothesis_background="b",
            theme_id="fp",
        )
    with pytest.raises(ValueError):
        service.create_design(
            title="T",
            hypothesis_statement="s",
            hypothesis_background="b",
            theme_id="FP/X",
        )
    with pytest.raises(ValueError):
        service.create_design(
            title="T",
            hypothesis_statement="s",
            hypothesis_background="b",
            theme_id="1FP",
        )


def test_list_designs_sorted_by_filename_ascending(
    service: DesignService,
) -> None:
    service.create_design(
        title="T1",
        hypothesis_statement="s",
        hypothesis_background="b",
        theme_id="FP",
    )
    service.create_design(
        title="T2",
        hypothesis_statement="s",
        hypothesis_background="b",
        theme_id="FP",
    )
    service.create_design(
        title="T3",
        hypothesis_statement="s",
        hypothesis_background="b",
        theme_id="FP",
    )
    designs = service.list_designs()
    ids = [d.id for d in designs]
    assert ids == sorted(ids)


def test_create_design_with_chart_and_next_action(service: DesignService) -> None:
    chart = [{"type": "scatter", "description": "外国人比率 vs 犯罪率"}]
    next_action = {
        "if_supported": "パネル分析へ進む",
        "if_rejected": {"reason": "相関なし", "pivot": "時系列分析"},
    }
    explanatory = [
        {
            "name": "foreign_ratio",
            "description": "外国人比率",
            "data_source": "0000010101",
            "time_points": "2012-2022",
        }
    ]
    design = service.create_design(
        title="FP test with enrichment",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        chart=chart,
        next_action=next_action,
        explanatory=explanatory,
    )
    assert design.chart == chart
    assert design.next_action == next_action
    assert design.explanatory == explanatory


def test_update_design_patches_fields_and_updates_timestamp(
    service: DesignService,
) -> None:
    import time

    design = service.create_design(
        title="Original", hypothesis_statement="stmt", hypothesis_background="bg"
    )
    original_updated_at = design.updated_at
    time.sleep(0.01)

    updated = service.update_design(
        design.id,
        title="Updated Title",
        next_action={"if_supported": "proceed"},
    )
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.next_action == {"if_supported": "proceed"}
    assert updated.hypothesis_statement == "stmt"  # unchanged
    assert updated.updated_at > original_updated_at


def test_update_design_returns_none_for_missing_id(service: DesignService) -> None:
    result = service.update_design("FP-H99", title="Ghost")
    assert result is None


def test_update_design_persists_to_yaml(service: DesignService) -> None:
    design = service.create_design(
        title="Persist test", hypothesis_statement="s", hypothesis_background="b"
    )
    service.update_design(design.id, chart=[{"type": "table"}])
    reloaded = service.get_design(design.id)
    assert reloaded is not None
    assert reloaded.chart == [{"type": "table"}]


# -- ID validation tests --


def test_get_design_invalid_id_raises_error(service: DesignService) -> None:
    with pytest.raises(ValueError, match="Invalid"):
        service.get_design("../etc/passwd")


def test_update_design_invalid_id_raises_error(service: DesignService) -> None:
    with pytest.raises(ValueError, match="Invalid"):
        service.update_design("foo/bar", title="x")
