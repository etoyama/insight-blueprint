"""Tests for core/reviews.py (SPEC-3 Tasks 2.1 + 2.2)."""

from pathlib import Path

import pytest

from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.reviews import ReviewService
from insight_blueprint.models.catalog import DomainKnowledgeEntry
from insight_blueprint.models.design import AnalysisDesign, DesignStatus
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml


class TestSubmitForReview:
    def test_submit_for_review_active_design(
        self,
        review_service: ReviewService,
        active_design: AnalysisDesign,
        design_service: DesignService,
    ) -> None:
        """R2-AC1: active design transitions to pending_review."""
        result = review_service.submit_for_review(active_design.id)
        assert result is not None
        assert result.status == DesignStatus.pending_review
        reloaded = design_service.get_design(active_design.id)
        assert reloaded is not None
        assert reloaded.status == DesignStatus.pending_review
        assert reloaded.updated_at > active_design.updated_at

    def test_submit_for_review_draft_raises_value_error(
        self,
        review_service: ReviewService,
        design_service: DesignService,
    ) -> None:
        """R2-AC2: submitting a draft design raises ValueError."""
        draft = design_service.create_design(
            title="Draft",
            hypothesis_statement="stmt",
            hypothesis_background="bg",
        )
        with pytest.raises(ValueError, match="active"):
            review_service.submit_for_review(draft.id)

    def test_submit_for_review_missing_returns_none(
        self,
        review_service: ReviewService,
    ) -> None:
        """R2-AC3: nonexistent design returns None."""
        result = review_service.submit_for_review("NONEXISTENT-H99")
        assert result is None


class TestSaveReviewComment:
    def test_save_review_comment_sets_status_supported(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        design_service: DesignService,
    ) -> None:
        """R2-AC4: save comment with status supported transitions design."""
        comment = review_service.save_review_comment(
            pending_design.id, "Good analysis", "supported"
        )
        assert comment is not None
        assert comment.status_after == DesignStatus.supported
        assert comment.design_id == pending_design.id
        assert comment.id.startswith("RC-")
        reloaded = design_service.get_design(pending_design.id)
        assert reloaded is not None
        assert reloaded.status == DesignStatus.supported

    def test_save_review_comment_sets_status_active(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        design_service: DesignService,
    ) -> None:
        """R2-AC5: save comment with status active (request changes)."""
        comment = review_service.save_review_comment(
            pending_design.id, "Needs more data", "active"
        )
        assert comment is not None
        assert comment.status_after == DesignStatus.active
        reloaded = design_service.get_design(pending_design.id)
        assert reloaded is not None
        assert reloaded.status == DesignStatus.active

    def test_save_review_comment_sets_status_rejected(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        design_service: DesignService,
    ) -> None:
        """Extra: rejected status works."""
        comment = review_service.save_review_comment(
            pending_design.id, "Hypothesis disproved", "rejected"
        )
        assert comment is not None
        assert comment.status_after == DesignStatus.rejected

    def test_save_review_comment_sets_status_inconclusive(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        design_service: DesignService,
    ) -> None:
        """Extra: inconclusive status works."""
        comment = review_service.save_review_comment(
            pending_design.id, "Not enough evidence", "inconclusive"
        )
        assert comment is not None
        assert comment.status_after == DesignStatus.inconclusive

    def test_save_review_comment_on_draft_raises_value_error(
        self,
        review_service: ReviewService,
        design_service: DesignService,
    ) -> None:
        """R2-AC6: commenting on a draft design raises ValueError."""
        draft = design_service.create_design(
            title="Draft",
            hypothesis_statement="stmt",
            hypothesis_background="bg",
        )
        with pytest.raises(ValueError, match="pending_review"):
            review_service.save_review_comment(draft.id, "comment", "supported")

    def test_save_review_comment_pending_review_invalid(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """R2-AC7: pending_review is not a valid post-review status."""
        with pytest.raises(ValueError, match="Invalid post-review status"):
            review_service.save_review_comment(
                pending_design.id, "comment", "pending_review"
            )

    def test_save_review_comment_missing_returns_none(
        self,
        review_service: ReviewService,
    ) -> None:
        """Extra: commenting on nonexistent design returns None."""
        result = review_service.save_review_comment(
            "NONEXISTENT-H99", "comment", "supported"
        )
        assert result is None


class TestListComments:
    def test_list_comments_returns_both_in_order(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R2-AC8: two comments listed in chronological order."""
        # First review cycle
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(active_design.id, "First comment", "active")
        # Second review cycle (re-submit)
        design_service.update_design(active_design.id, status=DesignStatus.active)
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id, "Second comment", "supported"
        )

        comments = review_service.list_comments(active_design.id)
        assert len(comments) == 2
        assert comments[0].comment == "First comment"
        assert comments[1].comment == "Second comment"

    def test_list_comments_nonexistent_returns_empty(
        self,
        review_service: ReviewService,
    ) -> None:
        """R2-AC9: nonexistent design returns empty list."""
        comments = review_service.list_comments("NONEXISTENT-H99")
        assert comments == []

    def test_list_comments_no_reviews_file_returns_empty(
        self,
        review_service: ReviewService,
        active_design: AnalysisDesign,
    ) -> None:
        """Extra: design with no reviews file returns empty list."""
        comments = review_service.list_comments(active_design.id)
        assert comments == []


class TestExtractDomainKnowledge:
    def test_extract_caution_from_comment(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC1: caution prefix extracts as caution category."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: watch for nulls in column X",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        assert entries[0].category == "caution"
        assert "nulls" in entries[0].content

    def test_extract_definition_from_comment(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC2: definition prefix extracts as definition category."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "definition: MAU = Monthly Active Users",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        assert entries[0].category == "definition"
        assert "MAU" in entries[0].content

    def test_extract_returns_preview_not_persisted(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
        tmp_path: Path,
    ) -> None:
        """R3-AC3: extract returns preview, NOT persisted to YAML."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: check data quality",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        # Verify NOT persisted
        ek_path = tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml"
        data = read_yaml(ek_path)
        persisted_entries = data.get("entries", []) if data else []
        assert len(persisted_entries) == 0

    def test_extract_no_comments_returns_empty(
        self,
        review_service: ReviewService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC6: design with no comments returns empty list."""
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert entries == []

    def test_extract_no_prefix_defaults_to_context(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC7: lines without prefix default to context category."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "This analysis targets Q3 planning",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        assert entries[0].category == "context"

    def test_extract_table_annotation_sets_scope(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC8: table: annotation sets affects_columns."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "table: population_stats\ncaution: data changed in 2015",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        assert entries[0].affects_columns == ["population_stats"]

    def test_extract_design_source_ids_default_scope(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC9: design.source_ids used as default scope."""
        design_service.update_design(active_design.id, source_ids=["src-A", "src-B"])
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: handle missing values",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        assert entries[0].affects_columns == ["src-A", "src-B"]

    def test_extract_no_scope_defaults_to_empty(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """R3-AC10: no annotation + no source_ids = unscoped."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: general data warning",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 1
        assert entries[0].affects_columns == []


class TestSaveExtractedKnowledge:
    def test_save_extracted_persists_to_yaml(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
        tmp_path: Path,
    ) -> None:
        """R3-AC4: save persists entries to extracted_knowledge.yaml."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: check nulls",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        saved = review_service.save_extracted_knowledge(active_design.id, entries)
        assert len(saved) == 1

        ek_path = tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml"
        data = read_yaml(ek_path)
        assert len(data["entries"]) == 1
        assert data["source_id"] == "review"

    def test_save_extracted_duplicate_keys_skipped(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
        tmp_path: Path,
    ) -> None:
        """R3-AC5: duplicate keys are skipped on re-save."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: check nulls",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        review_service.save_extracted_knowledge(active_design.id, entries)
        # Save again with same entries
        saved = review_service.save_extracted_knowledge(active_design.id, entries)
        assert len(saved) == 0  # All duplicates skipped

        ek_path = tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml"
        data = read_yaml(ek_path)
        assert len(data["entries"]) == 1  # Still only 1 entry

    def test_save_extracted_updates_comment_extracted_knowledge(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """Extra: save updates ReviewComment.extracted_knowledge with saved keys."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: check nulls",
            "supported",
        )
        entries = review_service.extract_domain_knowledge(active_design.id)
        review_service.save_extracted_knowledge(active_design.id, entries)

        comments = review_service.list_comments(active_design.id)
        assert len(comments) == 1
        assert len(comments[0].extracted_knowledge) > 0
        assert comments[0].extracted_knowledge[0] == entries[0].key

    def test_save_extracted_assigns_keys_to_correct_comment(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """Regression: keys must only be added to originating comment, not all."""
        # Comment 1: request changes (returns to active)
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "caution: null check needed",
            "active",
        )
        # Comment 2: supported
        review_service.submit_for_review(active_design.id)
        review_service.save_review_comment(
            active_design.id,
            "definition: MAU means monthly active users",
            "supported",
        )

        entries = review_service.extract_domain_knowledge(active_design.id)
        assert len(entries) == 2

        review_service.save_extracted_knowledge(active_design.id, entries)

        comments = review_service.list_comments(active_design.id)
        assert len(comments) == 2

        # Comment 1 should only have the key from its own entry
        assert len(comments[0].extracted_knowledge) == 1
        assert comments[0].extracted_knowledge[0] == entries[0].key

        # Comment 2 should only have the key from its own entry
        assert len(comments[1].extracted_knowledge) == 1
        assert comments[1].extracted_knowledge[0] == entries[1].key


_BAD_IDS = [
    "../etc/passwd",
    "foo/bar",
    "id with spaces",
    "",
    "valid-id\n",
    "back\\slash",
]


class TestIdValidation:
    @pytest.mark.parametrize("bad_id", _BAD_IDS)
    def test_submit_for_review_invalid_id_raises_error(
        self,
        review_service: ReviewService,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            review_service.submit_for_review(bad_id)

    @pytest.mark.parametrize("bad_id", _BAD_IDS)
    def test_save_review_comment_invalid_id_raises_error(
        self,
        review_service: ReviewService,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            review_service.save_review_comment(bad_id, "comment", "supported")

    @pytest.mark.parametrize("bad_id", _BAD_IDS)
    def test_list_comments_invalid_id_raises_error(
        self,
        review_service: ReviewService,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            review_service.list_comments(bad_id)

    @pytest.mark.parametrize("bad_id", _BAD_IDS)
    def test_extract_domain_knowledge_invalid_id_raises_error(
        self,
        review_service: ReviewService,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            review_service.extract_domain_knowledge(bad_id)

    @pytest.mark.parametrize("bad_id", _BAD_IDS)
    def test_save_extracted_knowledge_invalid_id_raises_error(
        self,
        review_service: ReviewService,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            review_service.save_extracted_knowledge(bad_id, [])


class TestImmutability:
    def test_save_extracted_knowledge_does_not_mutate_existing_data(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
        tmp_path: Path,
    ) -> None:
        """Verify save_extracted_knowledge does not mutate existing entries list."""
        ek_path = tmp_path / ".insight" / "rules" / "extracted_knowledge.yaml"
        # Write initial data
        initial_entry = {
            "key": "existing-key",
            "title": "Existing",
            "content": "Existing knowledge entry",
            "category": "context",
            "source": "manual",
            "affects_columns": [],
        }
        initial_data = {"source_id": "review", "entries": [initial_entry]}
        write_yaml(ek_path, initial_data)

        # Read back to get reference to the dict
        data_before = read_yaml(ek_path)
        entries_before = list(data_before["entries"])  # shallow copy for comparison

        # Save new entries
        new_entry = DomainKnowledgeEntry(
            key="new-key",
            title="New",
            content="New knowledge entry",
            category="caution",
            source=f"review:RC-abc@{active_design.id}",
            affects_columns=[],
        )
        review_service.save_extracted_knowledge(active_design.id, [new_entry])

        # Verify data_before dict was not mutated
        assert len(entries_before) == 1
        assert entries_before[0]["key"] == "existing-key"

        # Verify file now has both entries
        data_after = read_yaml(ek_path)
        assert len(data_after["entries"]) == 2
