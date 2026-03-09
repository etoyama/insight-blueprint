"""Tests for scripts/verify_wheel.py (FR-3.1, FR-3.2)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.verify_wheel import verify_wheel


def _create_mock_wheel(
    tmp_path: Path,
    *,
    include_index_html: bool = True,
    include_js: bool = True,
    include_py_typed: bool = True,
) -> Path:
    """Create a mock .whl file (ZIP) with configurable contents."""
    whl_path = tmp_path / "insight_blueprint-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(whl_path, "w") as zf:
        # Always include a Python file (baseline)
        zf.writestr("insight_blueprint/__init__.py", "__version__ = '0.1.0'")

        if include_index_html:
            zf.writestr(
                "insight_blueprint/static/index.html",
                "<html><body>Hello</body></html>",
            )

        if include_js:
            zf.writestr(
                "insight_blueprint/static/assets/main.abc123.js",
                "console.log('hello');",
            )

        if include_py_typed:
            zf.writestr("insight_blueprint/py.typed", "")

    return whl_path


class TestVerifyWheel:
    """Tests for wheel content verification."""

    def test_verify_valid_wheel(self, tmp_path: Path) -> None:
        """A wheel with all required files should pass verification."""
        whl_path = _create_mock_wheel(tmp_path)
        ok, messages = verify_wheel(whl_path)
        assert ok is True
        assert len(messages) > 0  # Should have success messages

    def test_verify_missing_index_html(self, tmp_path: Path) -> None:
        """A wheel without index.html should fail verification."""
        whl_path = _create_mock_wheel(tmp_path, include_index_html=False)
        ok, messages = verify_wheel(whl_path)
        assert ok is False
        assert any("index.html" in msg for msg in messages)

    def test_verify_missing_js_assets(self, tmp_path: Path) -> None:
        """A wheel without .js files in static/assets/ should fail verification."""
        whl_path = _create_mock_wheel(tmp_path, include_js=False)
        ok, messages = verify_wheel(whl_path)
        assert ok is False
        assert any(".js" in msg for msg in messages)

    def test_verify_missing_py_typed(self, tmp_path: Path) -> None:
        """A wheel without py.typed should fail verification."""
        whl_path = _create_mock_wheel(tmp_path, include_py_typed=False)
        ok, messages = verify_wheel(whl_path)
        assert ok is False
        assert any("py.typed" in msg for msg in messages)
