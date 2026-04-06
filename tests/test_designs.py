"""Tests for core/designs.py."""

import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from insight_blueprint.core.designs import DesignService
from insight_blueprint.models.design import (
    AnalysisIntent,
    ChartIntent,
    DesignStatus,
    VariableRole,
)
from insight_blueprint.storage.yaml_store import write_yaml


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
    assert design.chart[0].type == "scatter"
    assert design.chart[0].description == "外国人比率 vs 犯罪率"
    assert design.next_action == next_action
    assert design.explanatory[0].name == "foreign_ratio"
    assert design.explanatory[0].data_source == "0000010101"


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
    assert len(reloaded.chart) == 1
    assert reloaded.chart[0].type == "table"


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


# -- analysis_intent tests --


def test_analysis_intent_enum_members() -> None:
    members = set(AnalysisIntent.__members__.keys())
    expected = {"exploratory", "confirmatory", "mixed"}
    assert members == expected


def test_analysis_intent_enum_values() -> None:
    values = {i.value for i in AnalysisIntent}
    expected = {"exploratory", "confirmatory", "mixed"}
    assert values == expected


def test_analysis_design_default_analysis_intent_is_confirmatory(
    service: DesignService,
) -> None:
    design = service.create_design(
        title="Default intent",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    assert design.analysis_intent == AnalysisIntent.confirmatory


def test_create_design_with_analysis_intent(service: DesignService) -> None:
    design = service.create_design(
        title="Exploratory",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        analysis_intent="exploratory",
    )
    assert design.analysis_intent == AnalysisIntent.exploratory


def test_update_design_analysis_intent(service: DesignService) -> None:
    design = service.create_design(
        title="Intent update",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    updated = service.update_design(design.id, analysis_intent="mixed")
    assert updated is not None
    assert updated.analysis_intent == AnalysisIntent.mixed


def test_backward_compat_yaml_without_analysis_intent() -> None:
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
    assert design.analysis_intent == AnalysisIntent.confirmatory


def test_get_design_returns_analysis_intent(service: DesignService) -> None:
    service.create_design(
        title="Roundtrip intent",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        analysis_intent="exploratory",
    )
    retrieved = service.get_design("DEFAULT-H01")
    assert retrieved is not None
    assert retrieved.analysis_intent == AnalysisIntent.exploratory


# -- Typed field integration tests (verification-design) --


def test_create_design_with_untyped_explanatory_gets_default_role(
    service: DesignService,
) -> None:
    """Integ-01: create with no role -> reload -> role=covariate."""
    design = service.create_design(
        title="t",
        hypothesis_statement="s",
        hypothesis_background="b",
        explanatory=[{"name": "x1", "description": "d"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded is not None
    assert reloaded.explanatory[0].role == VariableRole.covariate


def test_create_design_with_typed_explanatory_persists_role(
    service: DesignService,
) -> None:
    """Integ-02: create with role=treatment -> reload -> role=treatment."""
    design = service.create_design(
        title="t",
        hypothesis_statement="s",
        hypothesis_background="b",
        explanatory=[{"name": "x1", "role": "treatment"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded is not None
    assert reloaded.explanatory[0].role == VariableRole.treatment


def test_create_design_with_legacy_dict_metrics_migrated(
    service: DesignService,
) -> None:
    """Integ-05: create with list[dict] metrics -> reload -> list[Metric]."""
    design = service.create_design(
        title="t",
        hypothesis_statement="s",
        hypothesis_background="b",
        metrics=[{"target": "y", "aggregation": "mean"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded is not None
    assert isinstance(reloaded.metrics, list)
    assert len(reloaded.metrics) == 1
    assert reloaded.metrics[0].target == "y"


def test_create_design_with_typed_chart_persists_intent(
    service: DesignService,
) -> None:
    """Integ-07: create with intent=trend -> reload -> intent=trend."""
    design = service.create_design(
        title="t",
        hypothesis_statement="s",
        hypothesis_background="b",
        chart=[{"intent": "trend", "type": "line", "x": "time", "y": "value"}],
    )
    reloaded = service.get_design(design.id)
    assert reloaded is not None
    assert reloaded.chart[0].intent == ChartIntent.trend


def test_create_design_without_methodology_is_none(
    service: DesignService,
) -> None:
    """Integ-08: create without methodology -> None."""
    design = service.create_design(
        title="t",
        hypothesis_statement="s",
        hypothesis_background="b",
    )
    assert design.methodology is None


def test_create_design_without_methodology_logs_warning(
    service: DesignService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """#81: create without methodology emits a warning log."""
    with caplog.at_level(logging.WARNING, logger="insight_blueprint.core.designs"):
        service.create_design(
            title="Missing method",
            hypothesis_statement="s",
            hypothesis_background="b",
        )
    assert any("methodology" in r.message.lower() for r in caplog.records)


def test_create_design_with_methodology_no_warning(
    service: DesignService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """#81: create with methodology does NOT emit a warning."""
    with caplog.at_level(logging.WARNING, logger="insight_blueprint.core.designs"):
        service.create_design(
            title="Has method",
            hypothesis_statement="s",
            hypothesis_background="b",
            methodology={"method": "OLS", "reason": "standard"},
        )
    methodology_warnings = [
        r for r in caplog.records if "methodology" in r.message.lower()
    ]
    assert len(methodology_warnings) == 0


def test_update_design_with_methodology(
    service: DesignService,
) -> None:
    """Integ-09: update with methodology dict -> reload -> Methodology object."""
    design = service.create_design(
        title="t",
        hypothesis_statement="s",
        hypothesis_background="b",
    )
    service.update_design(
        design.id,
        methodology={"method": "DID", "package": "statsmodels"},
    )
    reloaded = service.get_design(design.id)
    assert reloaded is not None
    assert reloaded.methodology is not None
    assert reloaded.methodology.method == "DID"
    assert reloaded.methodology.package == "statsmodels"


# ---------------------------------------------------------------------------
# F2: Corrupt File Isolation (Unit-07 ~ Unit-11, Unit-15)
# ---------------------------------------------------------------------------


def _valid_design_data(design_id: str, **overrides: object) -> dict:
    """Return minimal valid AnalysisDesign dict for corrupt file tests."""
    data: dict = {
        "id": design_id,
        "theme_id": "DEFAULT",
        "title": "Valid Design",
        "hypothesis_statement": "stmt",
        "hypothesis_background": "bg",
        "status": "in_review",
        "metrics": [],
        "explanatory": [],
        "chart": [],
        "source_ids": [],
        "created_at": "2025-01-01T00:00:00+09:00",
        "updated_at": "2025-01-01T00:00:00+09:00",
    }
    data.update(overrides)
    return data


def test_list_designs_skips_corrupt_file(
    service: DesignService, tmp_path: Path
) -> None:
    """Unit-07: 3 valid + 1 corrupt (invalid enum status), list_designs returns 3."""
    # Create 3 valid designs
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )
    service.create_design(
        title="T2", hypothesis_statement="s2", hypothesis_background="b2"
    )
    service.create_design(
        title="T3", hypothesis_statement="s3", hypothesis_background="b3"
    )

    # Write 1 corrupt YAML directly (invalid status enum)
    corrupt_path = tmp_path / ".insight" / "designs" / "CORRUPT-H01_hypothesis.yaml"
    write_yaml(corrupt_path, _valid_design_data("CORRUPT-H01", status="BOGUS"))

    designs = service.list_designs()
    assert len(designs) == 3


def test_list_designs_logs_warning_for_corrupt_file(
    service: DesignService, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Unit-08: caplog captures warning with filename for skipped corrupt file."""
    # Create 1 valid design
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )

    # Write 1 corrupt YAML
    corrupt_filename = "CORRUPT-H01_hypothesis.yaml"
    corrupt_path = tmp_path / ".insight" / "designs" / corrupt_filename
    write_yaml(corrupt_path, _valid_design_data("CORRUPT-H01", status="BOGUS"))

    with caplog.at_level(logging.WARNING, logger="insight_blueprint.core.designs"):
        service.list_designs()

    assert "Skipping corrupt design file" in caplog.text
    assert corrupt_filename in caplog.text


def test_list_designs_skips_file_missing_required_field(
    service: DesignService, tmp_path: Path
) -> None:
    """Unit-09: YAML with missing required field (no 'id') is skipped."""
    # Create 1 valid design
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )

    # Write YAML with no "id" field
    corrupt_path = tmp_path / ".insight" / "designs" / "NOID-H01_hypothesis.yaml"
    write_yaml(corrupt_path, {"theme_id": "X"})

    designs = service.list_designs()
    assert len(designs) == 1


def test_get_design_raises_validation_error_for_corrupt_file(
    service: DesignService, tmp_path: Path
) -> None:
    """Unit-10: get_design() raises ValidationError for corrupt file (NOT returns None)."""
    corrupt_path = tmp_path / ".insight" / "designs" / "CORRUPT-H01_hypothesis.yaml"
    write_yaml(corrupt_path, _valid_design_data("CORRUPT-H01", status="BOGUS"))

    with pytest.raises(ValidationError):
        service.get_design("CORRUPT-H01")


def test_list_designs_with_status_filter_skips_corrupt(
    service: DesignService, tmp_path: Path
) -> None:
    """Unit-11: list_designs with status filter + corrupt -> only valid matching designs."""
    # Create 2 in_review designs
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )
    service.create_design(
        title="T2", hypothesis_statement="s2", hypothesis_background="b2"
    )

    # Write 1 analyzing design directly via YAML
    analyzing_path = tmp_path / ".insight" / "designs" / "ANALYZ-H01_hypothesis.yaml"
    write_yaml(analyzing_path, _valid_design_data("ANALYZ-H01", status="analyzing"))

    # Write 1 corrupt YAML
    corrupt_path = tmp_path / ".insight" / "designs" / "CORRUPT-H01_hypothesis.yaml"
    write_yaml(corrupt_path, _valid_design_data("CORRUPT-H01", status="BOGUS"))

    designs = service.list_designs(status=DesignStatus.in_review)
    assert len(designs) == 2


@pytest.mark.parametrize(
    ("corruption_id", "corruption_type"),
    [
        ("yaml_syntax_error", "yaml_syntax_error"),
        ("non_dict_root", "non_dict_root"),
        ("missing_required", "missing_required"),
        ("invalid_enum", "invalid_enum"),
        ("invalid_nested_enum", "invalid_nested_enum"),
    ],
)
def test_list_designs_skips_corrupt_patterns(
    service: DesignService,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    corruption_id: str,
    corruption_type: str,
) -> None:
    """Unit-15: parametrize with 5 corruption patterns, each skipped by list_designs."""
    # Create 1 valid design
    service.create_design(
        title="T1", hypothesis_statement="s1", hypothesis_background="b1"
    )

    designs_dir = tmp_path / ".insight" / "designs"
    corrupt_filename = "XCRPT-H01_hypothesis.yaml"
    corrupt_path = designs_dir / corrupt_filename

    if corruption_type == "yaml_syntax_error":
        corrupt_path.write_text("id: test\n  bad indent: [unclosed")
    elif corruption_type == "non_dict_root":
        corrupt_path.write_text("- item1\n- item2")
    elif corruption_type == "missing_required":
        write_yaml(corrupt_path, {"theme_id": "X"})
    elif corruption_type == "invalid_enum":
        write_yaml(corrupt_path, _valid_design_data("XCRPT-H01", status="BOGUS"))
    elif corruption_type == "invalid_nested_enum":
        write_yaml(
            corrupt_path,
            _valid_design_data("XCRPT-H01", metrics=[{"target": "x", "tier": "BOGUS"}]),
        )

    with caplog.at_level(logging.WARNING, logger="insight_blueprint.core.designs"):
        designs = service.list_designs()

    assert len(designs) == 1, (
        f"Expected 1 valid design for {corruption_type}, got {len(designs)}"
    )
    assert corrupt_filename in caplog.text, (
        f"Expected warning log for {corruption_type} to contain {corrupt_filename}"
    )


# ---------------------------------------------------------------------------
# F1: Extra field preservation - service layer tests
# ---------------------------------------------------------------------------


def test_update_design_preserves_extra_fields(
    service: DesignService, tmp_path: Path
) -> None:
    """Unit-03: Extra fields survive update_design round-trip."""
    from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

    design = service.create_design(
        title="Original",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    # Manually add extra field to YAML
    file_path = tmp_path / ".insight" / "designs" / f"{design.id}_hypothesis.yaml"
    data = read_yaml(file_path)
    data["analyst_note"] = "important observation"
    write_yaml(file_path, data)

    # Update a different field
    service.update_design(design.id, title="New Title")

    # Verify extra field preserved and title updated
    result = read_yaml(file_path)
    assert result["analyst_note"] == "important observation"
    assert result["title"] == "New Title"


def test_update_design_referenced_knowledge_merge_preserves_extras(
    service: DesignService, tmp_path: Path
) -> None:
    """Unit-14: referenced_knowledge merge preserves extra fields."""
    from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

    design = service.create_design(
        title="Extras + refs",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
    )
    # Manually add extra field to YAML
    file_path = tmp_path / ".insight" / "designs" / f"{design.id}_hypothesis.yaml"
    data = read_yaml(file_path)
    data["analyst_note"] = "keep this"
    write_yaml(file_path, data)

    # Update with referenced_knowledge
    service.update_design(design.id, referenced_knowledge={"section": ["new_key"]})

    # Verify extra field preserved and referenced_knowledge merged
    result = read_yaml(file_path)
    assert result["analyst_note"] == "keep this"
    assert "section" in result["referenced_knowledge"]
    assert "new_key" in result["referenced_knowledge"]["section"]


def test_update_design_extra_fields_survive_yaml_round_trip(
    service: DesignService, tmp_path: Path
) -> None:
    """Integ-01: Full round-trip with extras at top-level and metrics level."""
    from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

    # Create design with metrics
    design = service.create_design(
        title="Round-trip test",
        hypothesis_statement="stmt",
        hypothesis_background="bg",
        metrics=[{"target": "revenue", "tier": "primary"}],
    )

    # Manually add extra fields at top-level AND in metrics
    file_path = tmp_path / ".insight" / "designs" / f"{design.id}_hypothesis.yaml"
    data = read_yaml(file_path)
    data["analyst_note"] = "top-level extra"
    data["metrics"][0]["note"] = "seasonal adjustment needed"
    write_yaml(file_path, data)

    # Update a different field via service
    service.update_design(design.id, title="Updated Title")

    # Read YAML after update and verify extras preserved
    result = read_yaml(file_path)
    assert result["title"] == "Updated Title"
    assert result["analyst_note"] == "top-level extra"
    assert result["metrics"][0]["note"] == "seasonal adjustment needed"
    assert result["metrics"][0]["target"] == "revenue"
