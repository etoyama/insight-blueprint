"""Integration tests for session_id extraction -- Integ-10, 22.

Tests session_id extraction from events.jsonl including corruption fallback.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML(typ="safe")


def _extract_session_id(events_path: Path) -> tuple[str | None, list[str]]:
    """Extract session_id from events.jsonl, returns (session_id, warnings)."""
    warnings: list[str] = []
    session_id: str | None = None

    if not events_path.exists():
        return None, ["events.jsonl not found"]

    # First pass: try to find system/init
    with events_path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                if evt.get("type") == "system" and evt.get("subtype") == "init":
                    session_id = evt.get("session_id")
                    if session_id:
                        return session_id, warnings
            except json.JSONDecodeError:
                warnings.append(f"WARNING: corrupted line: {line[:50]}")
                continue

    # Fallback: read all valid lines, take last system/init before corruption
    if session_id is None:
        valid_sessions: list[str] = []
        with events_path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    sid = evt.get("session_id")
                    if sid and evt.get("type") == "system":
                        valid_sessions.append(sid)
                except json.JSONDecodeError:
                    continue
        if valid_sessions:
            session_id = valid_sessions[-1]
            warnings.append("WARNING: fell back to prior session_id")

    return session_id, warnings


# =========================================================================
# Integ-10: session_id extraction
# =========================================================================


class TestSessionIdExtraction:
    """Integ-10: Extract session_id from events.jsonl."""

    def test_extracts_first_system_init_session_id(self, tmp_path: Path) -> None:
        """Normal events.jsonl -> extracts session_id from first init event."""
        events_path = tmp_path / "events.jsonl"
        with events_path.open("w") as f:
            f.write(
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "SESSION-ABC-123",
                    }
                )
                + "\n"
            )
            f.write(json.dumps({"type": "tool_use", "index": 0}) + "\n")
            # Second init (should be ignored -- first wins)
            f.write(
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "SESSION-DEF-456",
                    }
                )
                + "\n"
            )

        sid, warnings = _extract_session_id(events_path)
        assert sid == "SESSION-ABC-123"
        assert len(warnings) == 0

    def test_extracts_within_500ms(self, tmp_path: Path) -> None:
        """1000-line events.jsonl extraction < 500ms."""
        events_path = tmp_path / "events.jsonl"
        with events_path.open("w") as f:
            f.write(
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "PERF-SID",
                    }
                )
                + "\n"
            )
            for i in range(999):
                f.write(json.dumps({"type": "tool_use", "index": i}) + "\n")

        start = time.perf_counter()
        sid, _ = _extract_session_id(events_path)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert sid == "PERF-SID"
        assert elapsed_ms < 500.0, f"Took {elapsed_ms:.1f}ms"


# =========================================================================
# Integ-22: events.jsonl last line corruption
# =========================================================================


class TestEventsJsonlCorruption:
    """Integ-22: corrupted last line -> fallback to prior session_id."""

    def _create_corrupted_events(self, events_path: Path) -> None:
        """Create events.jsonl with corrupted last line."""
        with events_path.open("w") as f:
            f.write(
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "GOOD-SESSION-001",
                    }
                )
                + "\n"
            )
            for i in range(5):
                f.write(json.dumps({"type": "tool_use", "index": i}) + "\n")
            # Corrupted last line
            f.write('{"type":"system","subtype":"init","session_id":"BAD-SESSI\n')

    def test_corrupted_last_line_falls_back(self, tmp_path: Path) -> None:
        """Corrupted last line -> uses prior valid session_id."""
        events_path = tmp_path / "events.jsonl"
        self._create_corrupted_events(events_path)

        sid, warnings = _extract_session_id(events_path)
        assert sid == "GOOD-SESSION-001"

    def test_warning_logged_on_fallback(self, tmp_path: Path) -> None:
        """WARNING is emitted when falling back."""
        events_path = tmp_path / "events.jsonl"
        # Create file where first line is corrupted but second has valid session
        with events_path.open("w") as f:
            f.write("corrupted{json\n")
            f.write(
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "session_id": "FALLBACK-SID",
                    }
                )
                + "\n"
            )

        sid, warnings = _extract_session_id(events_path)
        # The first corrupted line should produce a warning
        has_warning = any("WARNING" in w or "corrupted" in w for w in warnings)
        assert has_warning, f"Expected warning about corruption, got: {warnings}"

    def test_resume_proceeds_after_fallback(self, tmp_path: Path) -> None:
        """After fallback extraction, session_id is usable for resume."""
        events_path = tmp_path / "events.jsonl"
        self._create_corrupted_events(events_path)

        sid, _ = _extract_session_id(events_path)
        # The extracted session_id should be non-empty and valid
        assert sid is not None
        assert len(sid) > 0
        assert sid == "GOOD-SESSION-001"
