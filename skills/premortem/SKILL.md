---
name: premortem
description: |
  Pre-flight risk evaluation and approval token issuance for batch analysis designs.
  Evaluates queued designs against history-based extrapolation and static thresholds,
  then issues an approval token for /batch-analysis --approved-by.
  Triggers: "premortem", "事前チェック", "batch の承認", "リスク判定",
  "pre-flight check", "run premortem".
  Chains to: /batch-analysis --approved-by TOKEN
  evaluate-only (write-prohibition contract, AC-1.5).
disable-model-invocation: true
argument-hint: "[--queued | --design <id> | --all] [--yes] [--mode manual|review|auto]"
---

# /premortem -- Pre-flight Risk Evaluation

Standalone skill that scans queued (or specified) analysis designs, runs a
deterministic risk decision tree (HARD_BLOCK / HIGH / MEDIUM / LOW / SKIP),
and issues an approval token consumed by `/batch-analysis --approved-by TOKEN`.

## When to Use

- Before launching `/batch-analysis` to validate the queue
- When you want to check risk levels of designs without executing them
- As an automated gate in review / auto mode dispatched by the launcher

## When NOT to Use

- Creating or editing designs (-> /analysis-design)
- Executing batch analysis (-> /batch-analysis)
- Reviewing completed results (-> /analysis-reflection)

## Workflow

1. **Parse arguments** -- Claude Code invokes `skills/premortem/cli.py` via
   Python subprocess. The CLI expects design data as JSON on stdin (Claude Code
   reads MCP tools and pipes the result).

2. **Collect design data** (Claude Code responsibility, before invoking cli.py):
   - Call `list_analysis_designs()` and filter `next_action.type == "batch_execute"`
     (or use `--design <id>` / `--all` to select differently)
   - For each design: `get_analysis_design(id)`, `get_table_schema(source_id)`,
     `search_catalog(source_id)` to build `source_checks_map`
   - Pipe the JSON payload to cli.py stdin

3. **Risk evaluation** (cli.py, pure decision engine):
   - For each design: `history_query.query()` + `risk_evaluator.evaluate()`
   - Render 1-line-per-design table to stdout
   - Apply mode logic (manual/review/auto) to decide approved vs skipped

4. **Interactive gate** (manual mode or review+HIGH):
   - Display `[s]kip / [e]dit / [a]bort / [c]ontinue` per HIGH design
   - HARD_BLOCK: `[c]ontinue` is NOT offered

5. **Token issuance**:
   - `token_manager.issue()` writes `.insight/premortem/{TIMESTAMP}.yaml`
   - stdout final line: `Launch with: /batch-analysis --approved-by {token_id}`

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Token issued successfully, batch may proceed |
| 2 | review mode + HIGH detected, batch should stop |
| 1 | Unexpected error (config invalid, I/O failure, etc.) |

## Writing Contract (AC-1.5)

During `/premortem` execution, the following paths are NEVER written to:

- `notebook.py` / marimo session JSON
- `.insight/designs/*.yaml` / `.insight/designs/*_journal.yaml`
- `.insight/runs/*/*/manifest.yaml` / `.insight/runs/*/run.yaml`
- `.insight/catalog/**`

Only `.insight/premortem/` receives writes (approval token).

## Language Rules

- Respond to users in Japanese
- Code, IDs, tool names, and YAML fields stay in English
