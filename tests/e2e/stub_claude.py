#!/usr/bin/env python3
"""Deterministic stub replacement for ``claude`` CLI.

Reads an approval token, writes deterministic events.jsonl and copies
expected fixture outputs to the run directory. No randomness, no network.

Env var overrides (for integration testing):
  STUB_HASH_CHECK=mismatch     -- every design written as status=skipped,
                                  skip_reason=hash_mismatch (no fixture copy).
  STUB_BUDGET_EXCEEDED=1       -- emit partial events and exit 124 so the
                                  launcher maps the run to status=timeout.

Exit codes:
  0   -- all approved designs processed (normal / hash_mismatch paths)
  2   -- budget limit (not used in current scenarios)
  124 -- simulated budget/turn timeout (STUB_BUDGET_EXCEEDED)
  137 -- simulated kill (STUB_KILL_AFTER_DESIGNS)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from ruamel.yaml import YAML

# ---------------------------------------------------------------------------
# Fixed timestamp for determinism
# ---------------------------------------------------------------------------

FIXED_NOW = datetime.fromisoformat("2026-04-20T23:00:00+09:00")
FIXED_NOW_ISO = FIXED_NOW.isoformat()

yaml = YAML(typ="safe")


# ---------------------------------------------------------------------------
# Argument parsing (mirrors real claude CLI subset)
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="claude", description="Stub claude CLI")
    p.add_argument("-p", "--prompt", dest="prompt", nargs="?", default=None)
    p.add_argument("--approved-by", dest="approved_by", default=None)
    p.add_argument("--output-format", dest="output_format", default="text")
    p.add_argument("--include-hook-events", action="store_true")
    p.add_argument("--fallback-model", default=None)
    p.add_argument("--max-turns", type=int, default=200)
    p.add_argument("--max-budget-usd", type=float, default=10.0)
    p.add_argument("--allowedTools", default=None)
    p.add_argument("--permission-mode", default=None)
    p.add_argument("--resume", dest="resume_session", default=None)
    p.add_argument("--model", default=None)
    # Positional prompt (alternative to -p)
    p.add_argument("positional_prompt", nargs="?", default=None)
    return p


def _resolve_insight_root() -> Path:
    """Return the .insight directory root."""
    env_root = os.environ.get("INSIGHT_ROOT")
    if env_root:
        return Path(env_root) / ".insight"
    return Path(os.getcwd()) / ".insight"


def _fixtures_dir() -> Path:
    env_dir = os.environ.get("STUB_FIXTURES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent / "fixtures"


def _scenario() -> str:
    return os.environ.get("STUB_SCENARIO", "e2e_01")


def _kill_after() -> int | None:
    val = os.environ.get("STUB_KILL_AFTER_DESIGNS")
    if val is not None:
        return int(val)
    return None


def _hash_check_mode() -> str | None:
    """Return STUB_HASH_CHECK mode ('mismatch') or None."""
    val = os.environ.get("STUB_HASH_CHECK")
    if val == "mismatch":
        return "mismatch"
    return None


def _budget_exceeded() -> bool:
    """True when STUB_BUDGET_EXCEEDED is set to a truthy value."""
    val = os.environ.get("STUB_BUDGET_EXCEEDED", "")
    return val.lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------


def _load_token(insight_root: Path, token_id: str) -> dict:
    """Load approval token YAML."""
    token_path = insight_root / "premortem" / f"{token_id}.yaml"
    if not token_path.exists():
        print(f"Token not found: {token_path}", file=sys.stderr)
        sys.exit(1)
    with token_path.open("r", encoding="utf-8") as f:
        return yaml.load(f)


# ---------------------------------------------------------------------------
# Events writing
# ---------------------------------------------------------------------------


def _write_event(f, event: dict) -> None:
    """Write a single NDJSON event line."""
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
    f.flush()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    insight_root = _resolve_insight_root()
    fixtures = _fixtures_dir()
    scenario = _scenario()
    kill_after = _kill_after()
    hash_check = _hash_check_mode()
    budget_exceeded = _budget_exceeded()

    # Determine token_id from --approved-by, run.yaml (launcher-written), or
    # default to legacy mode. Real claude reads the token via Read tool while
    # following batch-prompt.md; the stub mirrors that by picking up
    # run.yaml.premortem_token the launcher wrote during Step 4 (init_run).
    token_id = args.approved_by
    if token_id is None:
        rd_env = os.environ.get("RUN_DIR")
        if rd_env:
            rd_path = Path(rd_env)
            if not rd_path.is_absolute():
                rd_path = Path(os.getcwd()) / rd_path
            candidate = rd_path / "run.yaml"
            if candidate.exists():
                with candidate.open("r", encoding="utf-8") as f:
                    existing = yaml.load(f) or {}
                tid = existing.get("premortem_token")
                if tid:
                    token_id = tid
    if token_id is None:
        # Phase A legacy mode, no token -- still produce output
        token_id = "NONE"

    # Determine run_id -- use RUN_DIR env if available
    run_dir_env = os.environ.get("RUN_DIR")
    if run_dir_env:
        run_dir = Path(run_dir_env)
        if not run_dir.is_absolute():
            run_dir = Path(os.getcwd()) / run_dir
        run_id = run_dir.name
    else:
        run_id = "20260420_230000"
        run_dir = insight_root / "runs" / run_id

    run_dir.mkdir(parents=True, exist_ok=True)

    # Session management
    session_id = f"STUB-SESSION-{token_id}-001"
    is_resume = args.resume_session is not None
    if is_resume:
        session_id = args.resume_session

    # Determine events file mode
    events_path = run_dir / "events.jsonl"
    file_mode = "a" if is_resume else "w"

    # Load approved designs from token
    approved_designs: list[dict] = []
    if token_id != "NONE":
        token_data = _load_token(insight_root, token_id)
        approved_designs = token_data.get("approved_designs", [])
    else:
        # Legacy mode: load all designs from fixtures
        designs_dir = fixtures / "designs"
        for yf in sorted(designs_dir.glob("*.yaml")):
            with yf.open("r", encoding="utf-8") as f:
                d = yaml.load(f)
            approved_designs.append({"design_id": d["id"]})

    # If resuming, figure out which designs were already done
    completed_ids: set[str] = set()
    if is_resume and events_path.exists():
        with events_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    if evt.get("type") == "tool_use" and "design_id" in evt:
                        completed_ids.add(evt["design_id"])
                except (json.JSONDecodeError, KeyError):
                    pass

    # Write events
    with events_path.open(file_mode, encoding="utf-8") as ef:
        # system/init event
        _write_event(
            ef,
            {
                "type": "system",
                "subtype": "init",
                "session_id": session_id,
                "timestamp": FIXED_NOW_ISO,
            },
        )

        designs_completed = 0
        expected_dir = fixtures / "expected" / scenario

        for entry in approved_designs:
            design_id = entry.get("design_id", "unknown")

            # Skip already-completed designs on resume
            if design_id in completed_ids:
                continue

            # Check kill threshold
            if kill_after is not None and designs_completed >= kill_after:
                # Write partial result before dying
                _write_event(
                    ef,
                    {
                        "type": "result",
                        "status": "interrupted",
                        "total_cost_usd": 0.41 * designs_completed,
                        "timestamp": FIXED_NOW_ISO,
                    },
                )
                ef.flush()
                return 137

            # Simulated budget/turn exhaustion — emit partial result and exit 124
            # so the launcher's Step 9 maps the run to status=timeout (AC-4).
            if budget_exceeded and designs_completed >= 1:
                _write_event(
                    ef,
                    {
                        "type": "result",
                        "status": "interrupted",
                        "subtype": "error_max_turns",
                        "total_cost_usd": 0.42 * designs_completed,
                        "timestamp": FIXED_NOW_ISO,
                    },
                )
                ef.flush()
                return 124

            # Hash mismatch simulation — write a skipped manifest for this
            # design (no fixture copy) so crash_recovery / history_query see
            # status=skipped, skip_reason=hash_mismatch (AC-3).
            if hash_check == "mismatch":
                dst_dir = run_dir / design_id
                dst_dir.mkdir(parents=True, exist_ok=True)
                skip_manifest = {
                    "design_id": design_id,
                    "run_id": run_id,
                    "status": "skipped",
                    "skip_reason": "hash_mismatch",
                    "design_hash": entry.get("design_hash", ""),
                    "started_at": FIXED_NOW_ISO,
                    "ended_at": FIXED_NOW_ISO,
                    "elapsed_min": 0.0,
                    "cost_usd": 0.0,
                    "api_retries": 0,
                    "error_category": None,
                    "methodology_tags": [],
                    "verdict": None,
                }
                skip_out = YAML()
                skip_out.preserve_quotes = True
                with (dst_dir / "manifest.yaml").open("w", encoding="utf-8") as mf:
                    skip_out.dump(skip_manifest, mf)

                _write_event(
                    ef,
                    {
                        "type": "tool_use",
                        "content_block": {
                            "tool": "batch_skip",
                            "design_id": design_id,
                        },
                        "design_id": design_id,
                        "skip_reason": "hash_mismatch",
                        "timestamp": FIXED_NOW_ISO,
                    },
                )
                designs_completed += 1
                continue

            # tool_use event for this design
            _write_event(
                ef,
                {
                    "type": "tool_use",
                    "content_block": {
                        "tool": "batch_execute",
                        "design_id": design_id,
                    },
                    "design_id": design_id,
                    "timestamp": FIXED_NOW_ISO,
                },
            )

            # Copy expected manifest from fixtures to run dir
            src_manifest = expected_dir / design_id / "manifest.yaml"
            dst_dir = run_dir / design_id
            dst_dir.mkdir(parents=True, exist_ok=True)

            if src_manifest.exists():
                shutil.copy2(str(src_manifest), str(dst_dir / "manifest.yaml"))

            # Copy journal if exists
            src_journal = expected_dir / design_id / "journal.yaml"
            if src_journal.exists():
                shutil.copy2(str(src_journal), str(dst_dir / "journal.yaml"))

            designs_completed += 1

        # Final result event
        _write_event(
            ef,
            {
                "type": "result",
                "status": "completed",
                "total_cost_usd": 1.23,
                "timestamp": FIXED_NOW_ISO,
            },
        )

    # Copy summary.md if exists
    src_summary = expected_dir / "summary.md"
    if src_summary.exists():
        shutil.copy2(str(src_summary), str(run_dir / "summary.md"))

    # Write/update run.yaml with session info and completion
    run_yaml_path = run_dir / "run.yaml"
    if run_yaml_path.exists():
        with run_yaml_path.open("r", encoding="utf-8") as f:
            run_data = yaml.load(f) or {}
    else:
        run_data = {
            "run_id": run_id,
            "started_at": FIXED_NOW_ISO,
            "automation_mode": "review",
            "premortem_token": token_id if token_id != "NONE" else None,
        }

    run_data["session_id"] = session_id
    run_data["ended_at"] = FIXED_NOW_ISO
    run_data["status"] = "completed"
    run_data["cost_total_usd"] = 1.23

    out_yaml = YAML()
    out_yaml.preserve_quotes = True
    with run_yaml_path.open("w", encoding="utf-8") as f:
        out_yaml.dump(run_data, f)

    return 0


if __name__ == "__main__":
    sys.exit(main())
