#!/usr/bin/env bash
# E2E-03: Phase A -> Phase B migration
# Phase A: approved_by_required=false, no --approved-by -> warning + run
# Phase B: approved_by_required=true, no --approved-by -> exit 1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Setup
eval "$(uv run python3 tests/e2e/harness/setup.py --scenario e2e_03)"

teardown() { uv run python3 tests/e2e/harness/teardown.py 2>/dev/null || true; }
trap teardown EXIT

# Phase A: config has approved_by_required=false (default from setup)
export STUB_SCENARIO=e2e_03
PHASE_A_EXIT=0
bash "$PROJECT_ROOT/skills/batch-analysis/launcher.sh" 2>/tmp/e2e_03_phase_a.stderr || PHASE_A_EXIT=$?

# Phase B: swap config to approved_by_required=true
cp "$PROJECT_ROOT/tests/e2e/fixtures/config/review_phase_b.yaml" \
   "$INSIGHT_ROOT/.insight/config.yaml"

PHASE_B_EXIT=0
bash "$PROJECT_ROOT/skills/batch-analysis/launcher.sh" 2>/tmp/e2e_03_phase_b.stderr || PHASE_B_EXIT=$?

# Export exit codes for assertion script
export E2E_03_PHASE_A_EXIT="$PHASE_A_EXIT"
export E2E_03_PHASE_B_EXIT="$PHASE_B_EXIT"

# Assertions
uv run python3 tests/e2e/assertions/e2e_03_assert.py

echo "E2E-03: PASSED"
