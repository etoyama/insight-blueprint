"""Assertion helper utilities for E2E tests.

Functions return True on success, raise AssertionError on failure with
a unified diff written to stderr.
"""

from __future__ import annotations

import json
import sys
from difflib import unified_diff
from pathlib import Path

from ruamel.yaml import YAML

_yaml = YAML(typ="safe")


def load_yaml(path: str | Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Expected file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = _yaml.load(f)
    return data if isinstance(data, dict) else {}


def deep_diff(actual: dict, expected: dict, label: str = "") -> str:
    """Compute a unified diff between two dicts (YAML-serialised)."""
    yaml_out = YAML()
    yaml_out.default_flow_style = False

    import io

    buf_a = io.StringIO()
    buf_e = io.StringIO()
    yaml_out.dump(actual, buf_a)
    yaml_out.dump(expected, buf_e)

    a_lines = buf_a.getvalue().splitlines(keepends=True)
    e_lines = buf_e.getvalue().splitlines(keepends=True)

    diff = list(
        unified_diff(
            e_lines, a_lines, fromfile=f"expected/{label}", tofile=f"actual/{label}"
        )
    )
    return "".join(diff)


def assert_file_exists(path: str | Path, msg: str = "") -> None:
    """Assert that a file exists."""
    p = Path(path)
    if not p.exists():
        raise AssertionError(f"File not found: {p}" + (f" -- {msg}" if msg else ""))


def assert_field_equals(data: dict, field: str, expected, msg: str = "") -> None:
    """Assert that data[field] equals expected."""
    actual = data.get(field)
    if actual != expected:
        detail = f"Field '{field}': expected={expected!r}, actual={actual!r}"
        if msg:
            detail = f"{msg}: {detail}"
        print(detail, file=sys.stderr)
        raise AssertionError(detail)


def assert_yaml_matches_expected(
    actual_path: str | Path,
    expected_path: str | Path,
    fields: list[str] | None = None,
) -> None:
    """Assert that specific fields in actual YAML match expected YAML.

    If fields is None, all fields in expected are checked.
    """
    actual = load_yaml(actual_path)
    expected = load_yaml(expected_path)

    check_fields = fields if fields else list(expected.keys())
    mismatches: list[str] = []

    for field in check_fields:
        if field not in expected:
            continue
        exp_val = expected[field]
        act_val = actual.get(field)
        if act_val != exp_val:
            mismatches.append(f"  {field}: expected={exp_val!r}, actual={act_val!r}")

    if mismatches:
        diff_str = deep_diff(actual, expected, label=str(actual_path))
        print(diff_str, file=sys.stderr)
        msg = f"YAML mismatch in {actual_path}:\n" + "\n".join(mismatches)
        raise AssertionError(msg)


def assert_ndjson_valid(path: str | Path) -> list[dict]:
    """Assert that a file contains valid NDJSON. Returns parsed events."""
    path = Path(path)
    assert_file_exists(path, "events.jsonl missing")
    events: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise AssertionError(f"Invalid JSON at line {i} of {path}: {e}")
    return events


def grep_events(events: list[dict], **kwargs) -> list[dict]:
    """Filter events by matching all key-value pairs in kwargs."""
    results: list[dict] = []
    for evt in events:
        if all(evt.get(k) == v for k, v in kwargs.items()):
            results.append(evt)
    return results
