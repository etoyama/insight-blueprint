"""Unit tests for skills/_shared/_atomic.py — atomic YAML / text write helpers."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from ruamel.yaml import YAML

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f) or {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAtomicWriteYaml:
    """Tests for atomic_write_yaml."""

    def test_atomic_write_yaml_basic(self, tmp_path: Path) -> None:
        """Normal write can be read back identically."""
        from skills._shared._atomic import atomic_write_yaml

        target = tmp_path / "data.yaml"
        payload = {"foo": "bar", "nums": [1, 2, 3]}
        atomic_write_yaml(target, payload)

        result = _read_yaml(target)
        assert result["foo"] == "bar"
        assert result["nums"] == [1, 2, 3]

    def test_atomic_write_preserves_existing_on_failure(self, tmp_path: Path) -> None:
        """If write fails mid-way, the pre-existing file is untouched."""
        from skills._shared._atomic import atomic_write_yaml

        target = tmp_path / "data.yaml"
        original = {"version": 1}
        atomic_write_yaml(target, original)

        # Monkey-patch YAML.dump to raise after being called
        from ruamel.yaml import YAML as RealYAML

        def _exploding_dump(self, data, stream=None, **kw):  # type: ignore[no-untyped-def]
            raise OSError("simulated disk failure")

        import unittest.mock as mock

        with mock.patch.object(RealYAML, "dump", _exploding_dump):
            with pytest.raises(OSError, match="simulated disk failure"):
                atomic_write_yaml(target, {"version": 2})

        # Original file must survive
        result = _read_yaml(target)
        assert result["version"] == 1

    def test_atomic_write_concurrent_processes(self, tmp_path: Path) -> None:
        """Two concurrent writers — one wins, file is never corrupted."""
        from skills._shared._atomic import atomic_write_yaml

        target = tmp_path / "shared.yaml"
        errors: list[Exception] = []

        def _writer(value: int) -> None:
            try:
                atomic_write_yaml(target, {"writer": value})
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_writer, args=(1,))
        t2 = threading.Thread(target=_writer, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Unexpected errors: {errors}"
        result = _read_yaml(target)
        assert result["writer"] in (1, 2), "File must contain a valid value"

    def test_atomic_write_creates_parent_dir(self, tmp_path: Path) -> None:
        """Parent directories that don't exist are auto-created."""
        from skills._shared._atomic import atomic_write_yaml

        target = tmp_path / "a" / "b" / "c" / "deep.yaml"
        atomic_write_yaml(target, {"deep": True})

        result = _read_yaml(target)
        assert result["deep"] is True


class TestAtomicWriteText:
    """Tests for atomic_write_text."""

    def test_atomic_write_text_basic(self, tmp_path: Path) -> None:
        """Normal text write can be read back identically."""
        from skills._shared._atomic import atomic_write_text

        target = tmp_path / "note.txt"
        atomic_write_text(target, "hello world\n")
        assert target.read_text(encoding="utf-8") == "hello world\n"


class TestMethodologyVocab:
    """Verify methodology_vocab.yaml is loadable and has 10 tags."""

    def test_vocab_has_10_tags(self) -> None:
        from ruamel.yaml import YAML as RealYAML

        vocab_path = (
            Path(__file__).resolve().parents[2]
            / ".insight"
            / "rules"
            / "methodology_vocab.yaml"
        )
        yaml = RealYAML(typ="safe")
        with vocab_path.open("r", encoding="utf-8") as f:
            data = yaml.load(f)
        tags = data["methodology_tags"]
        assert isinstance(tags, list)
        assert len(tags) == 10
        expected = {
            "correlation_analysis",
            "regression",
            "time_series",
            "classification",
            "clustering",
            "hypothesis_test",
            "descriptive",
            "segmentation",
            "causal_inference",
            "ab_test",
        }
        assert set(tags) == expected
