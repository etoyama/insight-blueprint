"""Review workflow business logic (SPEC-3)."""

import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from insight_blueprint.core.designs import DesignService
from insight_blueprint.models.catalog import DomainKnowledgeEntry, KnowledgeCategory
from insight_blueprint.models.design import AnalysisDesign, DesignStatus
from insight_blueprint.models.review import ReviewComment
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

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

VALID_REVIEW_TRANSITIONS: dict[DesignStatus, set[DesignStatus]] = {
    DesignStatus.active: {DesignStatus.pending_review},
    DesignStatus.pending_review: {
        DesignStatus.active,
        DesignStatus.supported,
        DesignStatus.rejected,
        DesignStatus.inconclusive,
    },
}


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
        # Validate post-review status
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

        design = self._design_service.get_design(design_id)
        if design is None:
            return None

        if design.status != DesignStatus.pending_review:
            raise ValueError(
                f"Design must be in 'pending_review' status to save review comment, "
                f"current status: '{design.status}'"
            )

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

    def list_comments(self, design_id: str) -> list[ReviewComment]:
        """Read all review comments for a design.

        Returns empty list if no reviews file exists.
        """
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
        ek_path = self._rules_dir / "extracted_knowledge.yaml"
        data: dict[str, Any] = read_yaml(ek_path)
        if not data:
            data = {"source_id": "review", "entries": []}

        entries_list: list[dict[str, Any]] = data.get("entries", [])
        existing_keys = {e["key"] for e in entries_list}
        saved: list[DomainKnowledgeEntry] = []

        for entry in entries:
            if entry.key in existing_keys:
                continue
            entries_list.append(entry.model_dump(mode="json"))
            data["entries"] = entries_list
            existing_keys.add(entry.key)
            saved.append(entry)

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
                            ek_list.extend(keys_for_comment)
                            comment_data["extracted_knowledge"] = ek_list
                    write_yaml(reviews_path, reviews_data)

        return saved
