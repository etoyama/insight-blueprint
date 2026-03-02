"""Tests for insight_blueprint.lineage.tracker module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from insight_blueprint.lineage.tracker import LineageSession, StepRecord, tracked_pipe

# ---------------------------------------------------------------------------
# StepRecord
# ---------------------------------------------------------------------------


class TestStepRecord:
    """StepRecord is a frozen dataclass (Value Object)."""

    def test_create_step_record(self) -> None:
        ts = datetime.now(UTC)
        rec = StepRecord(
            step_number=1,
            reason="filter nulls",
            rows_before=100,
            rows_after=95,
            rows_delta=-5,
            timestamp=ts,
            function_name="drop_nulls",
        )
        assert rec.step_number == 1
        assert rec.reason == "filter nulls"
        assert rec.rows_before == 100
        assert rec.rows_after == 95
        assert rec.rows_delta == -5
        assert rec.timestamp == ts
        assert rec.function_name == "drop_nulls"

    def test_frozen(self) -> None:
        rec = StepRecord(
            step_number=1,
            reason="test",
            rows_before=10,
            rows_after=10,
            rows_delta=0,
            timestamp=datetime.now(UTC),
            function_name="noop",
        )
        with pytest.raises(FrozenInstanceError):
            rec.step_number = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LineageSession
# ---------------------------------------------------------------------------


class TestLineageSession:
    """LineageSession manages step records for a pipeline."""

    def test_default_name(self) -> None:
        session = LineageSession()
        assert session.name == "default"

    def test_custom_name(self) -> None:
        session = LineageSession(name="sales_pipeline")
        assert session.name == "sales_pipeline"

    def test_design_id_default_none(self) -> None:
        session = LineageSession()
        assert session.design_id is None

    def test_design_id_set(self) -> None:
        session = LineageSession(name="test", design_id="FP-H01")
        assert session.design_id == "FP-H01"

    def test_job_name_contains_session_name(self) -> None:
        session = LineageSession(name="my_pipeline")
        assert session.job_name.startswith("my_pipeline_")

    def test_job_name_unique(self) -> None:
        s1 = LineageSession(name="same")
        s2 = LineageSession(name="same")
        assert s1.job_name != s2.job_name

    def test_steps_empty_initially(self) -> None:
        session = LineageSession()
        assert session.steps == ()

    def test_steps_returns_tuple(self) -> None:
        session = LineageSession()
        assert isinstance(session.steps, tuple)

    def test_record_adds_step(self) -> None:
        session = LineageSession()
        rec = StepRecord(
            step_number=1,
            reason="test",
            rows_before=10,
            rows_after=8,
            rows_delta=-2,
            timestamp=datetime.now(UTC),
            function_name="fn",
        )
        session.record(rec)
        assert len(session.steps) == 1
        assert session.steps[0] is rec

    def test_next_step_number_starts_at_one(self) -> None:
        session = LineageSession()
        assert session.next_step_number() == 1

    def test_next_step_number_increments(self) -> None:
        session = LineageSession()
        session.record(StepRecord(1, "a", 10, 10, 0, datetime.now(UTC), "fn"))
        assert session.next_step_number() == 2
        session.record(StepRecord(2, "b", 10, 5, -5, datetime.now(UTC), "fn"))
        assert session.next_step_number() == 3


# ---------------------------------------------------------------------------
# tracked_pipe
# ---------------------------------------------------------------------------


class TestTrackedPipe:
    """tracked_pipe wraps functions and records row changes."""

    @pytest.fixture()
    def session(self) -> LineageSession:
        return LineageSession(name="test_session")

    def test_returns_transformed_result(self, session: LineageSession) -> None:
        data = list(range(10))

        def double_items(items: list) -> list:
            return [x * 2 for x in items]

        wrapped = tracked_pipe(double_items, reason="double", session=session)
        result = wrapped(data)
        assert result == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    def test_records_row_change(self, session: LineageSession) -> None:
        data = list(range(10))

        def remove_odds(items: list) -> list:
            return [x for x in items if x % 2 == 0]

        wrapped = tracked_pipe(remove_odds, reason="keep evens", session=session)
        wrapped(data)

        assert len(session.steps) == 1
        step = session.steps[0]
        assert step.rows_before == 10
        assert step.rows_after == 5
        assert step.rows_delta == -5
        assert step.reason == "keep evens"

    def test_step_number_sequential(self, session: LineageSession) -> None:
        data = list(range(20))

        def halve(items: list) -> list:
            return items[: len(items) // 2]

        result = tracked_pipe(halve, reason="first half", session=session)(data)
        result = tracked_pipe(halve, reason="second half", session=session)(result)

        assert session.steps[0].step_number == 1
        assert session.steps[1].step_number == 2

    def test_delta_positive(self, session: LineageSession) -> None:
        data = [1, 2, 3]

        def expand(items: list) -> list:
            return items + items

        tracked_pipe(expand, reason="expand", session=session)(data)
        assert session.steps[0].rows_delta == 3

    def test_delta_zero(self, session: LineageSession) -> None:
        data = [1, 2, 3]

        def identity(items: list) -> list:
            return list(items)

        tracked_pipe(identity, reason="noop", session=session)(data)
        assert session.steps[0].rows_delta == 0

    def test_function_name_named_function(self, session: LineageSession) -> None:
        def my_transform(items: list) -> list:
            return items

        tracked_pipe(my_transform, reason="test", session=session)([1])
        assert session.steps[0].function_name == "my_transform"

    def test_function_name_lambda(self, session: LineageSession) -> None:
        tracked_pipe(lambda x: x, reason="test", session=session)([1])
        assert session.steps[0].function_name == "<lambda>"

    def test_timestamp_is_utc(self, session: LineageSession) -> None:
        tracked_pipe(lambda x: x, reason="test", session=session)([1])
        assert session.steps[0].timestamp.tzinfo is not None
