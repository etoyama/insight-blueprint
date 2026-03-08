"""Analysis design CRUD business logic."""

import logging
import re
from pathlib import Path

from insight_blueprint.core.validation import validate_id as _validate_id
from insight_blueprint.models.common import now_jst
from insight_blueprint.models.design import AnalysisDesign, AnalysisIntent, DesignStatus
from insight_blueprint.storage.yaml_store import read_yaml, write_yaml

logger = logging.getLogger(__name__)

THEME_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*$")


def _merge_referenced_knowledge(
    current: dict[str, list[str]],
    incoming: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Merge incoming referenced_knowledge into current (union with dedup)."""
    result = dict(current)
    for section_key, new_keys in incoming.items():
        existing = result.get(section_key, [])
        result[section_key] = list(dict.fromkeys([*existing, *new_keys]))
    return result


class DesignService:
    """Service for managing analysis design documents."""

    def __init__(self, project_path: Path) -> None:
        self._designs_dir = project_path / ".insight" / "designs"

    def create_design(
        self,
        title: str,
        hypothesis_statement: str,
        hypothesis_background: str,
        parent_id: str | None = None,
        theme_id: str = "DEFAULT",
        metrics: list[dict] | None = None,
        explanatory: list[dict] | None = None,
        chart: list[dict] | None = None,
        next_action: dict | None = None,
        referenced_knowledge: dict[str, list[str]] | None = None,
        analysis_intent: str | AnalysisIntent = AnalysisIntent.confirmatory,
        methodology: dict | None = None,
    ) -> AnalysisDesign:
        """Create a new analysis design.

        Raises:
            ValueError: If theme_id does not match [A-Z][A-Z0-9]*
        """
        if not THEME_ID_PATTERN.match(theme_id):
            raise ValueError(
                f"Invalid theme_id '{theme_id}': must match [A-Z][A-Z0-9]*"
            )

        next_n = self._next_id_number(theme_id)
        design_id = f"{theme_id}-H{next_n:02d}"

        kwargs: dict = {
            "id": design_id,
            "theme_id": theme_id,
            "title": title,
            "hypothesis_statement": hypothesis_statement,
            "hypothesis_background": hypothesis_background,
            "analysis_intent": AnalysisIntent(analysis_intent),
            "parent_id": parent_id,
            "metrics": metrics or [],
            "explanatory": explanatory or [],
            "chart": chart or [],
            "next_action": next_action,
            "referenced_knowledge": referenced_knowledge or {},
        }
        if methodology is not None:
            kwargs["methodology"] = methodology

        design = AnalysisDesign(**kwargs)

        file_path = self._designs_dir / f"{design_id}_hypothesis.yaml"
        write_yaml(file_path, design.model_dump(mode="json"))

        return design

    def update_design(self, design_id: str, **fields: object) -> AnalysisDesign | None:
        """Partially update an existing design.

        Only provided fields are updated. updated_at is always refreshed.
        Returns None if design_id not found.
        """
        _validate_id(design_id, "design_id")
        design = self.get_design(design_id)
        if design is None:
            return None

        if "analysis_intent" in fields:
            fields["analysis_intent"] = AnalysisIntent(fields["analysis_intent"])

        # Merge referenced_knowledge: union lists with dedup, preserve existing keys
        if "referenced_knowledge" in fields:
            merged_ref = _merge_referenced_knowledge(
                dict(design.referenced_knowledge),
                fields.pop("referenced_knowledge"),  # type: ignore[arg-type]
            )
            fields["referenced_knowledge"] = merged_ref

        merged = {**design.model_dump(mode="json"), **fields, "updated_at": now_jst()}
        updated = AnalysisDesign.model_validate(merged)
        file_path = self._designs_dir / f"{design_id}_hypothesis.yaml"
        write_yaml(file_path, updated.model_dump(mode="json"))
        return updated

    def get_design(self, design_id: str) -> AnalysisDesign | None:
        """Get a design by ID. Returns None if not found."""
        _validate_id(design_id, "design_id")
        file_path = self._designs_dir / f"{design_id}_hypothesis.yaml"
        data = read_yaml(file_path)
        if not data:
            return None
        return AnalysisDesign(**data)

    def list_designs(self, status: DesignStatus | None = None) -> list[AnalysisDesign]:
        """List all designs, optionally filtered by status.

        Returns designs sorted by filename ascending (ID order).
        """
        if not self._designs_dir.exists():
            return []

        files = sorted(self._designs_dir.glob("*_hypothesis.yaml"))

        designs = []
        for file_path in files:
            try:
                data = read_yaml(file_path)
                if not data:
                    continue
                design = AnalysisDesign(**data)
            except Exception as exc:
                logger.warning(
                    "Skipping corrupt design file %s: %s",
                    file_path.name,
                    exc,
                )
                continue
            if status is None or design.status == status:
                designs.append(design)

        return designs

    def _next_id_number(self, theme_id: str) -> int:
        """Get next ID number using max-N+1 strategy to avoid collisions."""
        if not self._designs_dir.exists():
            return 1

        prefix = f"{theme_id}-H"
        max_n = 0

        for file_path in self._designs_dir.glob(f"{prefix}*_hypothesis.yaml"):
            stem = file_path.stem  # e.g., "FP-H01_hypothesis"
            id_part = stem.replace("_hypothesis", "")  # e.g., "FP-H01"
            try:
                n_str = id_part[len(prefix) :]  # e.g., "01"
                n = int(n_str)
                max_n = max(max_n, n)
            except (ValueError, IndexError):
                continue

        return max_n + 1
