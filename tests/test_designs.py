"""Tests for core/designs.py."""

from pathlib import Path

import pytest

from insight_blueprint.core.designs import DesignService
from insight_blueprint.models.design import DesignStatus


@pytest.fixture
def service(tmp_path: Path) -> DesignService:
    (tmp_path / ".insight" / "designs").mkdir(parents=True)
    return DesignService(tmp_path)


def test_design_status_members() -> None:
    members = set(DesignStatus.__members__.keys())
    expected = {
        "in_review",
        "revision_requested",
        "analyzing",
        "supported",
        "rejected",
        "inconclusive",
    }
    assert members == expected


def test_design_status_values() -> None:
    values = {s.value for s in DesignStatus}
    expected = {
        "in_review",
        "revision_requested",
        "analyzing",
        "supported",
        "rejected",
        "inconclusive",
    }
    assert values == expected


def test_create_design_returns_design_with_generated_id(
    service: DesignService,
) -> None:
    design = service.create_design(
        title="Test Hypothesis",
        hypothesis_statement="No correlation exists",
        hypothesis_background="Background info",
    )
    assert design.id == "DEFAULT-H01"
    assert design.status == DesignStatus.in_review


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
    in_review = service.list_designs(status=DesignStatus.in_review)
    assert len(in_review) == 2
    analyzing = service.list_designs(status=DesignStatus.analyzing)
    assert len(analyzing) == 0


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


# -- referenced_knowledge tests --


def test_referenced_knowledge_default_empty_dict(service: DesignService) -> None:
    """T-4.1: referenced_knowledge defaults to empty dict."""
    design = service.create_design(
        title="No refs",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    assert design.referenced_knowledge == {}


def test_referenced_knowledge_backward_compat_with_existing_yaml(
    tmp_path: Path,
) -> None:
    """T-4.6: Existing YAML without referenced_knowledge loads fine."""
    from insight_blueprint.models.design import AnalysisDesign

    yaml_data = {
        "id": "TEST-H01",
        "theme_id": "TEST",
        "title": "Old design",
        "hypothesis_statement": "stmt",
        "hypothesis_background": "bg",
        "status": "in_review",
        "metrics": {},
        "explanatory": [],
        "chart": [],
        "source_ids": [],
        "created_at": "2025-01-01T00:00:00+09:00",
        "updated_at": "2025-01-01T00:00:00+09:00",
    }
    design = AnalysisDesign(**yaml_data)
    assert design.referenced_knowledge == {}


# -- referenced_knowledge: create/update/get tests --


def test_create_design_with_referenced_knowledge(service: DesignService) -> None:
    """T-4.2: create_design with referenced_knowledge passes through."""
    refs = {"hypothesis_statement": ["K-001"]}
    design = service.create_design(
        title="With refs",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        referenced_knowledge=refs,
    )
    assert design.referenced_knowledge == {"hypothesis_statement": ["K-001"]}


def test_update_design_merge_new_section_key(service: DesignService) -> None:
    """T-4.3: update_design merges new section key."""
    design = service.create_design(
        title="Merge test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        referenced_knowledge={"hypothesis_statement": ["K-001"]},
    )
    updated = service.update_design(
        design.id, referenced_knowledge={"source_ids": ["K-002"]}
    )
    assert updated is not None
    assert updated.referenced_knowledge == {
        "hypothesis_statement": ["K-001"],
        "source_ids": ["K-002"],
    }


def test_update_design_merge_same_section_key_union(service: DesignService) -> None:
    """T-4.4: update_design merges same section key with union."""
    design = service.create_design(
        title="Union test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        referenced_knowledge={"hypothesis_statement": ["K-001"]},
    )
    updated = service.update_design(
        design.id, referenced_knowledge={"hypothesis_statement": ["K-002"]}
    )
    assert updated is not None
    assert updated.referenced_knowledge == {
        "hypothesis_statement": ["K-001", "K-002"],
    }


def test_update_design_merge_dedup(service: DesignService) -> None:
    """T-4.5: update_design deduplicates keys in same section."""
    design = service.create_design(
        title="Dedup test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        referenced_knowledge={"hypothesis_statement": ["K-001"]},
    )
    updated = service.update_design(
        design.id, referenced_knowledge={"hypothesis_statement": ["K-001", "K-002"]}
    )
    assert updated is not None
    assert updated.referenced_knowledge == {
        "hypothesis_statement": ["K-001", "K-002"],
    }


def test_get_design_returns_referenced_knowledge(service: DesignService) -> None:
    """T-4.7: get_design returns referenced_knowledge."""
    refs = {"hypothesis_statement": ["K-001"], "source_ids": ["K-002"]}
    design = service.create_design(
        title="Get refs",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        referenced_knowledge=refs,
    )
    retrieved = service.get_design(design.id)
    assert retrieved is not None
    assert retrieved.referenced_knowledge == refs


# -- ID validation tests --


@pytest.mark.parametrize(
    "bad_id",
    ["../etc/passwd", "foo/bar", "id with spaces", "", "valid-id\n", "back\\slash"],
)
def test_get_design_invalid_id_raises_error(
    service: DesignService, bad_id: str
) -> None:
    with pytest.raises(ValueError, match="Invalid"):
        service.get_design(bad_id)


@pytest.mark.parametrize(
    "bad_id",
    ["../etc/passwd", "foo/bar", "id with spaces", "", "valid-id\n", "back\\slash"],
)
def test_update_design_invalid_id_raises_error(
    service: DesignService, bad_id: str
) -> None:
    with pytest.raises(ValueError, match="Invalid"):
        service.update_design(bad_id, title="x")
