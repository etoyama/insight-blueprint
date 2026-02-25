"""Tests for review workflow models (SPEC-3 Tasks 1.1 + 1.2)."""

from datetime import datetime

from insight_blueprint.models.design import AnalysisDesign, DesignStatus
from insight_blueprint.models.review import ReviewComment


class TestDesignStatusExtension:
    def test_design_status_pending_review_value(self) -> None:
        """AC1: pending_review enum value is stored correctly."""
        assert DesignStatus.pending_review == "pending_review"
        assert DesignStatus("pending_review") == DesignStatus.pending_review


class TestAnalysisDesignSourceIds:
    def test_analysis_design_source_ids_default_empty(self) -> None:
        """AC4: source_ids defaults to empty list when not provided."""
        design = AnalysisDesign(
            id="TEST-H01",
            title="Test",
            hypothesis_statement="stmt",
            hypothesis_background="bg",
        )
        assert design.source_ids == []

    def test_analysis_design_source_ids_with_values(self) -> None:
        """Extra: source_ids preserves explicit values."""
        design = AnalysisDesign(
            id="TEST-H01",
            title="Test",
            hypothesis_statement="stmt",
            hypothesis_background="bg",
            source_ids=["src-1", "src-2"],
        )
        assert design.source_ids == ["src-1", "src-2"]


class TestReviewComment:
    def test_review_comment_timestamps_default_to_jst(self) -> None:
        """AC2: created_at defaults to now_jst()."""
        comment = ReviewComment(
            id="RC-aabbccdd",
            design_id="TEST-H01",
            comment="Good analysis",
            status_after=DesignStatus.supported,
        )
        assert isinstance(comment.created_at, datetime)
        assert comment.created_at.tzinfo is not None
        assert str(comment.created_at.tzinfo) == "Asia/Tokyo"

    def test_review_comment_extracted_knowledge_default_empty(self) -> None:
        """AC5: extracted_knowledge defaults to empty list."""
        comment = ReviewComment(
            id="RC-aabbccdd",
            design_id="TEST-H01",
            comment="Good analysis",
            status_after=DesignStatus.supported,
        )
        assert comment.extracted_knowledge == []

    def test_review_comment_json_round_trip(self) -> None:
        """AC3: JSON serialize + deserialize produces equivalent model."""
        comment = ReviewComment(
            id="RC-aabbccdd",
            design_id="TEST-H01",
            comment="Needs more data",
            reviewer="senior_analyst",
            status_after=DesignStatus.active,
            extracted_knowledge=["TEST-H01-0"],
        )
        data = comment.model_dump(mode="json")
        restored = ReviewComment(**data)
        assert restored.id == comment.id
        assert restored.design_id == comment.design_id
        assert restored.comment == comment.comment
        assert restored.reviewer == comment.reviewer
        assert restored.status_after == comment.status_after
        assert restored.extracted_knowledge == comment.extracted_knowledge

    def test_review_comment_status_after_supported(self) -> None:
        """Extra: status_after accepts DesignStatus.supported."""
        comment = ReviewComment(
            id="RC-11223344",
            design_id="TEST-H01",
            comment="Well done",
            status_after=DesignStatus.supported,
        )
        assert comment.status_after == DesignStatus.supported
