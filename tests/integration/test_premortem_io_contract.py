"""Integration tests for /premortem I/O write-prohibition contract -- Integ-03, 29.

Verifies that ``/premortem`` does NOT write to forbidden directories
and does NOT use sqlite3 at runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.conftest import (
    build_premortem_payload,
    collect_mtimes,
    run_premortem_cli,
)

# =========================================================================
# Integ-03: Write-prohibition contract
# =========================================================================


class TestPremortemWriteContract:
    """Integ-03: /premortem writes ONLY to .insight/premortem/."""

    @pytest.fixture(autouse=True)
    def _setup(
        self,
        insight_root_with_history: Path,
        sample_designs: list[dict],
        config_review_a: Path,
    ) -> None:
        self.insight_root = insight_root_with_history
        self.base_dir = self.insight_root
        self.cwd = self.insight_root.parent
        self.payload = build_premortem_payload(sample_designs)
        self.cli_args = [
            "--queued",
            "--yes",
            "--mode",
            "auto",
            "--base-dir",
            str(self.base_dir),
        ]

    def test_no_writes_to_designs_dir(self) -> None:
        """No files in .insight/designs/ are modified."""
        designs_dir = self.insight_root / "designs"
        before = collect_mtimes(designs_dir)
        run_premortem_cli(self.cli_args, self.payload, cwd=self.cwd)
        after = collect_mtimes(designs_dir)
        assert before == after, f"designs/ was modified: {set(after) - set(before)}"

    def test_no_writes_to_runs_dir(self) -> None:
        """No files in .insight/runs/ are modified."""
        runs_dir = self.insight_root / "runs"
        before = collect_mtimes(runs_dir)
        run_premortem_cli(self.cli_args, self.payload, cwd=self.cwd)
        after = collect_mtimes(runs_dir)
        assert before == after, f"runs/ was modified: {set(after) - set(before)}"

    def test_no_writes_to_catalog_dir(self) -> None:
        """No files in .insight/catalog/ are modified."""
        catalog_dir = self.insight_root / "catalog"
        before = collect_mtimes(catalog_dir)
        run_premortem_cli(self.cli_args, self.payload, cwd=self.cwd)
        after = collect_mtimes(catalog_dir)
        assert before == after, f"catalog/ was modified: {set(after) - set(before)}"

    def test_writes_only_to_premortem_dir(self) -> None:
        """The only directory with new files is .insight/premortem/."""
        # Collect before state for all directories
        before_designs = collect_mtimes(self.insight_root / "designs")
        before_runs = collect_mtimes(self.insight_root / "runs")
        before_catalog = collect_mtimes(self.insight_root / "catalog")
        before_rules = collect_mtimes(self.insight_root / "rules")

        run_premortem_cli(self.cli_args, self.payload, cwd=self.cwd)

        assert before_designs == collect_mtimes(self.insight_root / "designs")
        assert before_runs == collect_mtimes(self.insight_root / "runs")
        assert before_catalog == collect_mtimes(self.insight_root / "catalog")
        assert before_rules == collect_mtimes(self.insight_root / "rules")

        # premortem dir should have new files
        premortem_tokens = list((self.insight_root / "premortem").glob("*.yaml"))
        assert len(premortem_tokens) >= 1

    def test_mcp_tools_read_only_called(self) -> None:
        """cli.py does not import/use any MCP write tools directly.

        The CLI receives all data via stdin JSON -- it doesn't call MCP tools
        at all. We verify by checking that the cli module doesn't import
        any MCP write function.
        """
        # Static check: grep cli.py for MCP write tool names
        cli_path = (
            Path(__file__).resolve().parents[2] / "skills" / "premortem" / "cli.py"
        )
        content = cli_path.read_text()
        write_tools = [
            "update_analysis_design",
            "transition_design_status",
            "catalog_add_source",
            "catalog_update_source",
            "knowledge_store",
            "knowledge_update",
            "design_create",
            "design_update",
        ]
        for tool in write_tools:
            assert tool not in content, f"cli.py references write tool: {tool}"


# =========================================================================
# Integ-29: SQLite connect prohibition
# =========================================================================


class TestPremortemNoSqliteRuntime:
    """Integ-29: /premortem code does not use sqlite3.connect for data access.

    The prohibition is about using sqlite3 as a data store for history_query
    or any premortem logic.  Third-party libraries (e.g. ``filelock``) may
    import sqlite3 internally -- that is acceptable.
    """

    def test_premortem_source_no_sqlite_import(self) -> None:
        """Static scan: no ``import sqlite3`` or ``sqlite3.connect`` in
        premortem and _shared source files (excluding _atomic.py which uses
        filelock, a third-party that internally uses sqlite3).
        """
        project_root = Path(__file__).resolve().parents[2]
        scan_dirs = [
            project_root / "skills" / "premortem",
            project_root / "skills" / "_shared",
        ]

        violations: list[str] = []
        for scan_dir in scan_dirs:
            for py_file in sorted(scan_dir.rglob("*.py")):
                content = py_file.read_text()
                rel = py_file.relative_to(project_root)
                if "import sqlite3" in content or "sqlite3.connect" in content:
                    violations.append(str(rel))

        assert violations == [], (
            f"sqlite3 usage found in premortem source files: {violations}"
        )

    def test_history_query_uses_yaml_not_sqlite(self) -> None:
        """history_query.py must use glob + YAML, not sqlite3 import/connect."""
        project_root = Path(__file__).resolve().parents[2]
        hq_path = project_root / "skills" / "premortem" / "lib" / "history_query.py"
        content = hq_path.read_text()

        assert "import sqlite3" not in content, (
            "history_query.py must not import sqlite3"
        )
        assert "sqlite3.connect" not in content, (
            "history_query.py must not call sqlite3.connect"
        )
        assert "glob" in content, "history_query.py should use glob for manifest scan"
