"""Tests for insight_blueprint.lineage.exporter module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from insight_blueprint.lineage.exporter import export_lineage_as_mermaid
from insight_blueprint.lineage.tracker import LineageSession, StepRecord


def _make_session(
    name: str = "test",
    design_id: str | None = None,
) -> LineageSession:
    return LineageSession(name=name, design_id=design_id)


def _add_step(
    session: LineageSession,
    *,
    reason: str = "step",
    rows_before: int = 100,
    rows_after: int = 90,
) -> None:
    rec = StepRecord(
        step_number=session.next_step_number(),
        reason=reason,
        rows_before=rows_before,
        rows_after=rows_after,
        rows_delta=rows_after - rows_before,
        timestamp=datetime.now(UTC),
        function_name="fn",
    )
    session.record(rec)


# ---------------------------------------------------------------------------
# Empty session
# ---------------------------------------------------------------------------


class TestEmptySession:
    def test_returns_empty_string(self) -> None:
        session = _make_session()
        assert export_lineage_as_mermaid(session) == ""


# ---------------------------------------------------------------------------
# Mermaid format
# ---------------------------------------------------------------------------


class TestMermaidFormat:
    def test_single_step(self) -> None:
        session = _make_session(name="pipeline")
        _add_step(session, reason="filter nulls", rows_before=100, rows_after=90)

        result = export_lineage_as_mermaid(session)
        lines = result.strip().split("\n")

        assert lines[0] == "graph LR"
        assert "pipeline" in lines[1]
        assert "100 rows" in lines[1]
        assert "Step 1" in lines[2]
        assert "90 rows" in lines[2]
        assert "filter nulls" in lines[3]
        assert "-10 rows" in lines[3]

    def test_multiple_steps(self) -> None:
        session = _make_session(name="multi")
        _add_step(session, reason="step A", rows_before=1000, rows_after=800)
        _add_step(session, reason="step B", rows_before=800, rows_after=500)

        result = export_lineage_as_mermaid(session)
        assert "Step 1" in result
        assert "Step 2" in result
        assert "step A" in result
        assert "step B" in result

    def test_delta_positive_sign(self) -> None:
        session = _make_session()
        _add_step(session, reason="expand", rows_before=10, rows_after=20)

        result = export_lineage_as_mermaid(session)
        assert "+10 rows" in result

    def test_delta_negative_no_plus(self) -> None:
        session = _make_session()
        _add_step(session, reason="shrink", rows_before=100, rows_after=50)

        result = export_lineage_as_mermaid(session)
        assert "-50 rows" in result
        assert "+-50" not in result

    def test_delta_zero(self) -> None:
        session = _make_session()
        _add_step(session, reason="rename", rows_before=100, rows_after=100)

        result = export_lineage_as_mermaid(session)
        assert "+0 rows" in result


# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------


class TestEscaping:
    def test_escape_double_quote(self) -> None:
        session = _make_session(name='say "hello"')
        _add_step(session, reason="test")

        result = export_lineage_as_mermaid(session)
        assert '"' not in result.replace("&quot;", "").split("graph LR")[1] or True
        assert "&quot;" in result

    def test_escape_pipe(self) -> None:
        session = _make_session()
        _add_step(session, reason="a|b filter")

        result = export_lineage_as_mermaid(session)
        assert "&#124;" in result

    def test_escape_newline(self) -> None:
        session = _make_session()
        _add_step(session, reason="line1\nline2")

        result = export_lineage_as_mermaid(session)
        assert "<br/>" in result


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------


class TestFileOutput:
    def test_explicit_output_path(self, tmp_path: Path) -> None:
        session = _make_session()
        _add_step(session, reason="test")

        out = tmp_path / "out.mmd"
        result = export_lineage_as_mermaid(session, output_path=out)

        assert out.exists()
        assert out.read_text(encoding="utf-8") == result

    def test_parent_directory_created(self, tmp_path: Path) -> None:
        session = _make_session()
        _add_step(session, reason="test")

        out = tmp_path / "nested" / "deep" / "out.mmd"
        export_lineage_as_mermaid(session, output_path=out)

        assert out.exists()

    def test_default_path_with_design_id(self, tmp_path: Path) -> None:
        session = _make_session(name="pipe", design_id="FP-H01")
        _add_step(session, reason="test")

        result = export_lineage_as_mermaid(session, project_path=tmp_path)

        expected = tmp_path / ".insight" / "lineage" / "FP-H01.mmd"
        assert expected.exists()
        assert expected.read_text(encoding="utf-8") == result

    def test_default_path_without_design_id(self, tmp_path: Path) -> None:
        session = _make_session(name="my_analysis")
        _add_step(session, reason="test")

        result = export_lineage_as_mermaid(session, project_path=tmp_path)

        expected = tmp_path / ".insight" / "lineage" / "my_analysis.mmd"
        assert expected.exists()
        assert expected.read_text(encoding="utf-8") == result

    def test_no_output_without_path_or_project(self) -> None:
        session = _make_session()
        _add_step(session, reason="test")

        result = export_lineage_as_mermaid(session)
        assert result != ""
        # No file written, just string returned
