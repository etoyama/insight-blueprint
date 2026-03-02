"""Data transformation pipeline lineage tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd  # type: ignore[import-not-found]


@dataclass(frozen=True)
class StepRecord:
    """Recorded transformation step (immutable Value Object)."""

    step_number: int
    reason: str
    rows_before: int
    rows_after: int
    rows_delta: int
    timestamp: datetime
    function_name: str


class LineageSession:
    """Lineage tracking session. One instance per pipeline."""

    def __init__(
        self,
        name: str = "default",
        *,
        design_id: str | None = None,
    ) -> None:
        self._name = name
        self._design_id = design_id
        self._job_name = f"{name}_{uuid4().hex[:8]}"
        self._steps: list[StepRecord] = []

    @property
    def name(self) -> str:
        """Session name."""
        return self._name

    @property
    def design_id(self) -> str | None:
        """Associated AnalysisDesign ID."""
        return self._design_id

    @property
    def job_name(self) -> str:
        """Unique job name."""
        return self._job_name

    @property
    def steps(self) -> tuple[StepRecord, ...]:
        """Read-only view of recorded steps."""
        return tuple(self._steps)

    def record(self, record: StepRecord) -> None:
        """Record a transformation step."""
        self._steps.append(record)

    def next_step_number(self) -> int:
        """Return the next step number."""
        return len(self._steps) + 1


def tracked_pipe(
    fn: Callable[[pd.DataFrame], pd.DataFrame],
    *,
    reason: str,
    session: LineageSession,
) -> Callable[[pd.DataFrame], pd.DataFrame]:
    """Wrap a pipe function and record row count changes."""

    def wrapper(df: pd.DataFrame) -> pd.DataFrame:
        rows_before = len(df)
        result = fn(df)
        rows_after = len(result)

        record = StepRecord(
            step_number=session.next_step_number(),
            reason=reason,
            rows_before=rows_before,
            rows_after=rows_after,
            rows_delta=rows_after - rows_before,
            timestamp=datetime.now(UTC),
            function_name=getattr(fn, "__name__", "<lambda>"),
        )
        session.record(record)
        return result

    return wrapper
