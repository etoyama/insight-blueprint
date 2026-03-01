"""Tests for core/reviews.py (SPEC-3 Tasks 2.1 + 2.2)."""

import logging
import re
from pathlib import Path

import pytest

from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.reviews import ReviewService
from insight_blueprint.models.catalog import DomainKnowledgeEntry
from insight_blueprint.models.design import AnalysisDesign, DesignStatus
from insight_blueprint.models.review import ReviewBatch
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


# ---------------------------------------------------------------------------
# Inline Review Comments — save_review_batch tests (P2)
# ---------------------------------------------------------------------------

_BAD_DESIGN_IDS = [
    "../etc/passwd",
    "foo/bar",
    "id with spaces",
    "",
    "valid-id\n",
    "back\\slash",
]


class TestSaveReviewBatch:
    """Tests for ReviewService.save_review_batch (FR-8, FR-12, FR-14, NFR-8)."""

    def test_save_batch_with_valid_data(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        review_batch_data: dict,
    ) -> None:
        """FR-8, FR-12: Valid batch is saved and returns ReviewBatch."""
        result = review_service.save_review_batch(
            pending_design.id,
            review_batch_data["status_after"],
            review_batch_data["comments"],
            review_batch_data["reviewer"],
        )
        assert result is not None
        assert isinstance(result, ReviewBatch)
        assert result.id.startswith("RB-")
        assert result.design_id == pending_design.id
        assert len(result.comments) == 2

    def test_save_batch_transitions_design_status(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        design_service: DesignService,
    ) -> None:
        """FR-8: Design status transitions to status_after."""
        review_service.save_review_batch(
            pending_design.id,
            "supported",
            [{"comment": "Good"}],
        )
        reloaded = design_service.get_design(pending_design.id)
        assert reloaded is not None
        assert reloaded.status == DesignStatus.supported

    def test_save_batch_persists_to_yaml(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        tmp_path: Path,
    ) -> None:
        """FR-14: Batch is persisted to YAML file."""
        review_service.save_review_batch(
            pending_design.id,
            "supported",
            [{"comment": "Persisted"}],
        )
        reviews_path = (
            tmp_path / ".insight" / "designs" / f"{pending_design.id}_reviews.yaml"
        )
        data = read_yaml(reviews_path)
        assert "batches" in data
        assert len(data["batches"]) == 1

    def test_save_batch_preserves_target_section(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """FR-4: target_section is preserved in saved batch."""
        result = review_service.save_review_batch(
            pending_design.id,
            "supported",
            [
                {
                    "comment": "Check this",
                    "target_section": "hypothesis_statement",
                    "target_content": "Test",
                }
            ],
        )
        assert result is not None
        assert result.comments[0].target_section == "hypothesis_statement"

    def test_save_batch_preserves_target_content_text(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """FR-11: Text target_content is preserved."""
        result = review_service.save_review_batch(
            pending_design.id,
            "supported",
            [
                {
                    "comment": "Note",
                    "target_section": "hypothesis_statement",
                    "target_content": "CVR will improve by 10%",
                }
            ],
        )
        assert result is not None
        assert result.comments[0].target_content == "CVR will improve by 10%"

    def test_save_batch_preserves_target_content_json(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """FR-11: JSON target_content (dict) is preserved."""
        content = {"kpi_name": "CVR", "current_value": "2.5%"}
        result = review_service.save_review_batch(
            pending_design.id,
            "supported",
            [
                {
                    "comment": "Metrics",
                    "target_section": "metrics",
                    "target_content": content,
                }
            ],
        )
        assert result is not None
        assert result.comments[0].target_content == content

    def test_save_batch_rejects_non_pending_review(
        self,
        review_service: ReviewService,
        non_pending_design: AnalysisDesign,
    ) -> None:
        """AC: Non-pending_review design raises ValueError."""
        with pytest.raises(ValueError, match="pending_review"):
            review_service.save_review_batch(
                non_pending_design.id,
                "supported",
                [{"comment": "Should fail"}],
            )

    def test_save_batch_rejects_invalid_status(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """Invalid status_after is rejected."""
        with pytest.raises(ValueError, match="Invalid"):
            review_service.save_review_batch(
                pending_design.id,
                "pending_review",
                [{"comment": "Bad status"}],
            )

    def test_save_batch_rejects_empty_comments(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """Empty comments list is rejected."""
        with pytest.raises((ValueError, Exception)):
            review_service.save_review_batch(
                pending_design.id,
                "supported",
                [],
            )

    @pytest.mark.parametrize("bad_id", _BAD_DESIGN_IDS)
    def test_save_batch_rejects_invalid_design_id(
        self,
        review_service: ReviewService,
        bad_id: str,
    ) -> None:
        """Path traversal and invalid IDs are rejected."""
        with pytest.raises(ValueError, match="Invalid"):
            review_service.save_review_batch(
                bad_id,
                "supported",
                [{"comment": "Bad ID"}],
            )

    def test_save_batch_missing_design(
        self,
        review_service: ReviewService,
    ) -> None:
        """Nonexistent design_id returns None."""
        result = review_service.save_review_batch(
            "NONEXIST-H99",
            "supported",
            [{"comment": "Ghost"}],
        )
        assert result is None

    def test_save_batch_yaml_write_failure_no_status_change(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        design_service: DesignService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """NFR-8: YAML write failure prevents status transition."""
        monkeypatch.setattr(
            "insight_blueprint.core.reviews.write_yaml",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("Disk full")),
        )
        with pytest.raises(OSError):
            review_service.save_review_batch(
                pending_design.id,
                "supported",
                [{"comment": "Fail write"}],
            )
        reloaded = design_service.get_design(pending_design.id)
        assert reloaded is not None
        assert reloaded.status == DesignStatus.pending_review

    def test_save_batch_status_update_failure_keeps_batch(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        status_update_failure: None,
        tmp_path: Path,
    ) -> None:
        """NFR-8: YAML succeeds but status update fails — batch is preserved."""
        with pytest.raises(RuntimeError, match="Simulated"):
            review_service.save_review_batch(
                pending_design.id,
                "supported",
                [{"comment": "Batch saved, status not"}],
            )
        # Batch should be persisted even though status update failed
        reviews_path = (
            tmp_path / ".insight" / "designs" / f"{pending_design.id}_reviews.yaml"
        )
        data = read_yaml(reviews_path)
        assert "batches" in data
        assert len(data["batches"]) == 1

    @pytest.mark.parametrize(
        "status", ["supported", "rejected", "inconclusive", "active"]
    )
    def test_save_batch_all_status_transitions(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
        status: str,
    ) -> None:
        """FR-7: All 4 post-review status transitions work."""
        # Submit for review each time
        review_service.submit_for_review(active_design.id)
        result = review_service.save_review_batch(
            active_design.id,
            status,
            [{"comment": f"Setting to {status}"}],
        )
        assert result is not None
        assert result.status_after.value == status
        reloaded = design_service.get_design(active_design.id)
        assert reloaded is not None
        assert reloaded.status.value == status
        # Reset for next iteration if needed
        if status == "active":
            return
        design_service.update_design(active_design.id, status=DesignStatus.active)

    def test_save_batch_appends_to_existing_batches(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """Appends to existing batches in the YAML file."""
        # First batch
        review_service.submit_for_review(active_design.id)
        review_service.save_review_batch(
            active_design.id,
            "active",
            [{"comment": "First batch"}],
        )
        # Second batch
        review_service.submit_for_review(active_design.id)
        result = review_service.save_review_batch(
            active_design.id,
            "supported",
            [{"comment": "Second batch"}],
        )
        assert result is not None
        batches = review_service.list_review_batches(active_design.id)
        assert len(batches) == 2

    def test_save_batch_creates_new_file(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        tmp_path: Path,
    ) -> None:
        """Creates reviews.yaml if it doesn't exist."""
        reviews_path = (
            tmp_path / ".insight" / "designs" / f"{pending_design.id}_reviews.yaml"
        )
        assert not reviews_path.exists()
        review_service.save_review_batch(
            pending_design.id,
            "supported",
            [{"comment": "Creates file"}],
        )
        assert reviews_path.exists()


class TestSaveReviewBatchTargetSectionValidation:
    """Tests for target_section validation against ALLOWED_TARGET_SECTIONS (NFR-7)."""

    @pytest.mark.parametrize(
        "section",
        [
            "hypothesis_statement",
            "hypothesis_background",
            "metrics",
            "explanatory",
            "chart",
            "next_action",
        ],
    )
    def test_valid_target_sections_accepted(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        section: str,
    ) -> None:
        """NFR-7: All 6 valid sections are accepted."""
        result = review_service.save_review_batch(
            pending_design.id,
            "supported",
            [
                {
                    "comment": "Valid section",
                    "target_section": section,
                    "target_content": "x",
                }
            ],
        )
        assert result is not None

    def test_invalid_target_section_rejected(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """NFR-7: Invalid section name is rejected."""
        with pytest.raises(ValueError, match="target_section"):
            review_service.save_review_batch(
                pending_design.id,
                "supported",
                [
                    {
                        "comment": "Bad section",
                        "target_section": "nonexistent_section",
                        "target_content": "x",
                    }
                ],
            )

    def test_null_target_section_accepted(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """NFR-7: None target_section is allowed (no anchor)."""
        result = review_service.save_review_batch(
            pending_design.id,
            "supported",
            [{"comment": "No anchor"}],
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Inline Review Comments — list_review_batches tests (P3)
# ---------------------------------------------------------------------------


class TestListReviewBatches:
    """Tests for ReviewService.list_review_batches (FR-13)."""

    def test_list_batches_returns_all(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """FR-13: Returns all batches for a design."""
        # Create two batches
        review_service.submit_for_review(active_design.id)
        review_service.save_review_batch(
            active_design.id, "active", [{"comment": "First"}]
        )
        review_service.submit_for_review(active_design.id)
        review_service.save_review_batch(
            active_design.id, "supported", [{"comment": "Second"}]
        )
        batches = review_service.list_review_batches(active_design.id)
        assert len(batches) == 2

    def test_list_batches_descending_order(
        self,
        review_service: ReviewService,
        design_service: DesignService,
        active_design: AnalysisDesign,
    ) -> None:
        """FR-13: Batches are sorted by created_at descending."""
        review_service.submit_for_review(active_design.id)
        review_service.save_review_batch(
            active_design.id, "active", [{"comment": "Earlier"}]
        )
        review_service.submit_for_review(active_design.id)
        review_service.save_review_batch(
            active_design.id, "supported", [{"comment": "Later"}]
        )
        batches = review_service.list_review_batches(active_design.id)
        assert len(batches) == 2
        assert batches[0].created_at >= batches[1].created_at

    def test_list_batches_empty(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """No batches returns empty list."""
        batches = review_service.list_review_batches(pending_design.id)
        assert batches == []

    def test_list_batches_nonexistent_design(
        self,
        review_service: ReviewService,
    ) -> None:
        """Nonexistent design_id returns empty list."""
        batches = review_service.list_review_batches("NONEXIST-H99")
        assert batches == []

    def test_list_batches_no_file(
        self,
        review_service: ReviewService,
        active_design: AnalysisDesign,
    ) -> None:
        """No reviews file returns empty list."""
        batches = review_service.list_review_batches(active_design.id)
        assert batches == []

    def test_list_batches_no_batches_key(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """YAML without 'batches' key returns empty list + warning."""
        reviews_path = (
            tmp_path / ".insight" / "designs" / f"{pending_design.id}_reviews.yaml"
        )
        write_yaml(reviews_path, {"comments": [{"old": "format"}]})
        with caplog.at_level(logging.WARNING):
            batches = review_service.list_review_batches(pending_design.id)
        assert batches == []
        assert (
            any(
                "batches" in r.message.lower() or "warning" in r.message.lower()
                for r in caplog.records
            )
            or len(caplog.records) > 0
        )

    def test_list_batches_preserves_target_content(
        self,
        review_service: ReviewService,
        pending_design: AnalysisDesign,
    ) -> None:
        """target_content is preserved through save + list round-trip."""
        content = {"kpi": "CVR", "value": 2.5}
        review_service.save_review_batch(
            pending_design.id,
            "supported",
            [
                {
                    "comment": "With content",
                    "target_section": "metrics",
                    "target_content": content,
                }
            ],
        )
        batches = review_service.list_review_batches(pending_design.id)
        assert len(batches) == 1
        assert batches[0].comments[0].target_content == content

    def test_list_batches_corrupted_yaml(
        self,
        review_service: ReviewService,
        corrupted_reviews_yaml: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Error#7: Corrupted YAML returns empty list + warning."""
        with caplog.at_level(logging.WARNING):
            batches = review_service.list_review_batches("DES-corrupt")
        assert batches == []
        assert len(caplog.records) > 0


# ---------------------------------------------------------------------------
# Section Definition Sync Contract Test (P4 — Task 4.2)
# ---------------------------------------------------------------------------

_SECTIONS_TS_PATH = Path(__file__).resolve().parent.parent / (
    "frontend/src/pages/design-detail/components/sections.ts"
)


class TestSectionDefinitionSync:
    """NFR-7: Backend ALLOWED_TARGET_SECTIONS must match frontend COMMENTABLE_SECTIONS."""

    def test_backend_and_frontend_section_ids_match(self) -> None:
        """Contract test: section IDs are identical between backend and frontend."""
        from insight_blueprint.core.reviews import ALLOWED_TARGET_SECTIONS

        # Parse frontend TypeScript source to extract section IDs
        ts_source = _SECTIONS_TS_PATH.read_text(encoding="utf-8")
        # Match lines like: { id: "hypothesis_statement", ...
        frontend_ids = set(re.findall(r'id:\s*"([^"]+)"', ts_source))

        assert frontend_ids, "Failed to parse any section IDs from sections.ts"
        assert frontend_ids == ALLOWED_TARGET_SECTIONS, (
            f"Section ID mismatch!\n"
            f"  Backend only:  {sorted(ALLOWED_TARGET_SECTIONS - frontend_ids)}\n"
            f"  Frontend only: {sorted(frontend_ids - ALLOWED_TARGET_SECTIONS)}"
        )
