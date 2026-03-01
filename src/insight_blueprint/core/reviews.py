"""Review workflow business logic (SPEC-3)."""

import logging
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from insight_blueprint.core.designs import DesignService
from insight_blueprint.core.validation import validate_id as _validate_id
from insight_blueprint.models.catalog import DomainKnowledgeEntry, KnowledgeCategory
from insight_blueprint.models.design import AnalysisDesign, DesignStatus
from insight_blueprint.models.review import BatchComment, ReviewBatch, ReviewComment
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

logger = logging.getLogger(__name__)

# Regex patterns for keyword-based extraction (case-insensitive)
_CATEGORY_PATTERNS: list[tuple[re.Pattern[str], KnowledgeCategory]] = [
    (re.compile(r"^(caution|注意)\s*:\s*", re.IGNORECASE), KnowledgeCategory.caution),
    (
        re.compile(r"^(definition|定義)\s*:\s*", re.IGNORECASE),
        KnowledgeCategory.definition,
    ),
    (
        re.compile(r"^(methodology|手法)\s*:\s*", re.IGNORECASE),
        KnowledgeCategory.methodology,
    ),
    (
        re.compile(r"^(context|背景)\s*:\s*", re.IGNORECASE),
        KnowledgeCategory.context,
    ),
]

_TABLE_PATTERN = re.compile(r"^(table|テーブル)\s*:\s*", re.IGNORECASE)


ALLOWED_TARGET_SECTIONS: set[str] = {
    "hypothesis_statement",
    "hypothesis_background",
    "metrics",
    "explanatory",
    "chart",
    "next_action",
}

VALID_REVIEW_TRANSITIONS: dict[DesignStatus, set[DesignStatus]] = {
    DesignStatus.active: {DesignStatus.pending_review},
    DesignStatus.pending_review: {
        DesignStatus.active,
        DesignStatus.supported,
        DesignStatus.rejected,
        DesignStatus.inconclusive,
    },
}


def _validate_post_review_status(status: str) -> DesignStatus:
    """Parse and validate a post-review status string.

    Raises ValueError if status is not a valid post-review transition target.
    """
    try:
        target_status = DesignStatus(status)
    except ValueError:
        valid = ", ".join(
            s.value for s in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]
        )
        raise ValueError(
            f"Invalid post-review status '{status}'. Valid: {valid}"
        ) from None

    if target_status not in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]:
        valid = ", ".join(
            s.value for s in VALID_REVIEW_TRANSITIONS[DesignStatus.pending_review]
        )
        raise ValueError(f"Invalid post-review status '{status}'. Valid: {valid}")

    return target_status


def _ensure_pending_review(design: AnalysisDesign | None, operation: str) -> None:
    """Raise ValueError if design is not in pending_review status."""
    if design is not None and design.status != DesignStatus.pending_review:
        raise ValueError(
            f"Design must be in 'pending_review' status to {operation}, "
            f"current status: '{design.status}'"
        )


class ReviewService:
    """Service for managing the review workflow on analysis designs."""

    def __init__(self, project_path: Path, design_service: DesignService) -> None:
        self._project_path = project_path
        self._designs_dir = project_path / ".insight" / "designs"
        self._rules_dir = project_path / ".insight" / "rules"
        self._design_service = design_service

    def submit_for_review(self, design_id: str) -> AnalysisDesign | None:
        """Transition an active design to pending_review.

        Returns None if design not found.
        Raises ValueError if design is not in active status.
        """
        _validate_id(design_id, "design_id")
        design = self._design_service.get_design(design_id)
        if design is None:
            return None
        if design.status != DesignStatus.active:
            raise ValueError(
                f"Design must be in 'active' status to submit for review, "
                f"current status: '{design.status}'"
            )
        return self._design_service.update_design(
            design_id, status=DesignStatus.pending_review
        )

    def save_review_comment(
        self,
        design_id: str,
        comment: str,
        status: str,
        reviewer: str = "analyst",
    ) -> ReviewComment | None:
        """Save a review comment and transition the design status.

        Returns None if design not found.
        Raises ValueError if design is not in pending_review status
        or if status is not a valid post-review status.
        """
        _validate_id(design_id, "design_id")
        target_status = _validate_post_review_status(status)

        design = self._design_service.get_design(design_id)
        if design is None:
            return None
        _ensure_pending_review(design, "save review comment")

        # Create comment
        comment_id = f"RC-{uuid.uuid4().hex[:8]}"
        review_comment = ReviewComment(
            id=comment_id,
            design_id=design_id,
            comment=comment,
            reviewer=reviewer,
            status_after=target_status,
        )

        # Persist comment
        reviews_path = self._designs_dir / f"{design_id}_reviews.yaml"
        existing = read_yaml(reviews_path)
        comments_list = existing.get("comments", [])
        comments_list.append(review_comment.model_dump(mode="json"))
        write_yaml(reviews_path, {"comments": comments_list})

        # Transition design status
        self._design_service.update_design(design_id, status=target_status)

        return review_comment

    def save_review_batch(
        self,
        design_id: str,
        status: str,
        comments: list[dict],
        reviewer: str = "analyst",
    ) -> ReviewBatch | None:
        """Save a batch of review comments and transition the design status.

        Returns None if design not found.
        Raises ValueError if design is not pending_review, status is invalid,
        or target_section is not in ALLOWED_TARGET_SECTIONS.
        """
        _validate_id(design_id, "design_id")
        target_status = _validate_post_review_status(status)

        # Validate comments not empty
        if not comments:
            raise ValueError("comments must not be empty")

        # Validate target_section values
        for c in comments:
            section = c.get("target_section")
            if section is not None and section not in ALLOWED_TARGET_SECTIONS:
                raise ValueError(
                    f"Invalid target_section '{section}'. "
                    f"Allowed: {sorted(ALLOWED_TARGET_SECTIONS)}"
                )

        design = self._design_service.get_design(design_id)
        if design is None:
            return None
        _ensure_pending_review(design, "save review batch")

        # Create batch
        batch_id = f"RB-{uuid.uuid4().hex[:8]}"
        batch_comments = [BatchComment(**c) for c in comments]
        batch = ReviewBatch(
            id=batch_id,
            design_id=design_id,
            status_after=target_status,
            reviewer=reviewer,
            comments=batch_comments,
        )

        # Persist batch to YAML (atomic write first)
        reviews_path = self._designs_dir / f"{design_id}_reviews.yaml"
        existing = read_yaml(reviews_path)
        batches_list: list[dict] = existing.get("batches", [])
        batches_list.append(batch.model_dump(mode="json"))
        write_yaml(reviews_path, {**existing, "batches": batches_list})

        # Transition design status (after YAML write succeeds)
        self._design_service.update_design(design_id, status=target_status)

        return batch

    def list_review_batches(self, design_id: str) -> list[ReviewBatch]:
        """Read all review batches for a design.

        Returns empty list if no file, no 'batches' key, or corrupted YAML.
        Sorted by created_at descending (newest first).
        """
        _validate_id(design_id, "design_id")
        reviews_path = self._designs_dir / f"{design_id}_reviews.yaml"

        try:
            data = read_yaml(reviews_path)
        except Exception:
            logger.warning("Failed to read reviews YAML for %s", design_id)
            return []

        if not data:
            return []

        if "batches" not in data:
            if "comments" in data:
                logger.warning(
                    "Old format (comments key) found for %s, "
                    "batches key missing — returning empty list",
                    design_id,
                )
            else:
                logger.warning("No batches key found in reviews YAML for %s", design_id)
            return []

        raw_batches = data["batches"]
        if not isinstance(raw_batches, list):
            logger.warning("Batches key is not a list for %s", design_id)
            return []

        try:
            batches = [ReviewBatch(**b) for b in raw_batches]
        except Exception:
            logger.warning("Failed to parse review batches for %s", design_id)
            return []

        # Sort by created_at descending
        batches.sort(key=lambda b: b.created_at, reverse=True)
        return batches

    def list_comments(self, design_id: str) -> list[ReviewComment]:
        """Read all review comments for a design.

        Returns empty list if no reviews file exists.
        """
        _validate_id(design_id, "design_id")
        reviews_path = self._designs_dir / f"{design_id}_reviews.yaml"
        data = read_yaml(reviews_path)
        if not data or "comments" not in data:
            return []
        return [ReviewComment(**c) for c in data["comments"]]

    def extract_domain_knowledge(self, design_id: str) -> list[DomainKnowledgeEntry]:
        """Extract domain knowledge entries from review comments as preview.

        Returns a list of DomainKnowledgeEntry items (NOT persisted).
        Scope priority: table: annotation > design.source_ids > [].
        """
        _validate_id(design_id, "design_id")
        comments = self.list_comments(design_id)
        if not comments:
            return []

        # Get default scope from design.source_ids
        design = self._design_service.get_design(design_id)
        default_scope: list[str] = (
            list(design.source_ids) if design and design.source_ids else []
        )

        entries: list[DomainKnowledgeEntry] = []
        index = 0

        for comment in comments:
            current_scope: list[str] | None = None  # None = use default

            for raw_line in comment.comment.split("\n"):
                line = unicodedata.normalize("NFKC", raw_line).strip()
                if not line:
                    continue

                # Check for table: annotation
                table_match = _TABLE_PATTERN.match(line)
                if table_match:
                    table_name = line[table_match.end() :].strip()
                    current_scope = [table_name] if table_name else []
                    continue

                # Check for category prefix
                category = KnowledgeCategory.context  # default
                content = line
                for pattern, cat in _CATEGORY_PATTERNS:
                    match = pattern.match(line)
                    if match:
                        category = cat
                        content = line[match.end() :].strip()
                        break

                if not content:
                    continue

                # Determine scope
                scope = current_scope if current_scope is not None else default_scope

                entry = DomainKnowledgeEntry(
                    key=f"{design_id}-{index}",
                    title=content[:80],
                    content=content,
                    category=category,
                    source=f"review:{comment.id}@{design_id}",
                    affects_columns=list(scope),
                )
                entries.append(entry)
                index += 1

        return entries

    def save_extracted_knowledge(
        self,
        design_id: str,
        entries: list[DomainKnowledgeEntry],
    ) -> list[DomainKnowledgeEntry]:
        """Persist user-confirmed knowledge entries to extracted_knowledge.yaml.

        Duplicate keys are skipped (not overwritten).
        Updates ReviewComment.extracted_knowledge with saved keys.
        Returns the list of newly saved entries.
        """
        _validate_id(design_id, "design_id")
        ek_path = self._rules_dir / "extracted_knowledge.yaml"
        data: dict[str, Any] = read_yaml(ek_path)
        if not data:
            data = {"source_id": "review", "entries": []}

        existing_entries: list[dict[str, Any]] = data.get("entries", [])
        existing_keys = {e["key"] for e in existing_entries}
        saved: list[DomainKnowledgeEntry] = []
        new_entries: list[dict[str, Any]] = []

        for entry in entries:
            if entry.key in existing_keys:
                continue
            new_entries.append(entry.model_dump(mode="json"))
            existing_keys.add(entry.key)
            saved.append(entry)

        data = {**data, "entries": [*existing_entries, *new_entries]}
        write_yaml(ek_path, data)

        # Update ReviewComment.extracted_knowledge per comment
        if saved:
            # Build comment_id -> [keys] mapping from entry source field
            comment_keys: dict[str, list[str]] = {}
            for entry in saved:
                # source format: "review:{comment_id}@{design_id}"
                if entry.source.startswith("review:") and "@" in entry.source:
                    comment_id = entry.source[len("review:") : entry.source.index("@")]
                    comment_keys.setdefault(comment_id, []).append(entry.key)

            if comment_keys:
                reviews_path = self._designs_dir / f"{design_id}_reviews.yaml"
                reviews_data = read_yaml(reviews_path)
                if reviews_data and "comments" in reviews_data:
                    for comment_data in reviews_data["comments"]:
                        keys_for_comment = comment_keys.get(
                            comment_data.get("id", ""), []
                        )
                        if keys_for_comment:
                            ek_list = comment_data.get("extracted_knowledge", [])
                            comment_data["extracted_knowledge"] = [
                                *ek_list,
                                *keys_for_comment,
                            ]
                    write_yaml(reviews_path, reviews_data)

        return saved
