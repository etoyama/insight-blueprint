#!/usr/bin/env bash
# E2E-02: Crash recovery next-day resume
# 1st run: STUB_KILL_AFTER_DESIGNS=1 -> exit 137 after DES-A
# 2nd run: resume -> completes DES-B
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Setup
eval "$(uv run python3 tests/e2e/harness/setup.py --scenario e2e_02)"

teardown() { uv run python3 tests/e2e/harness/teardown.py 2>/dev/null || true; }
trap teardown EXIT

# Premortem: issue token for DES-A and DES-B only (no HIGH)
DESIGNS_JSON=$(uv run python3 -c "
import json
from pathlib import Path
from ruamel.yaml import YAML
yaml = YAML(typ='safe')
designs = []
sc_map = {}
for f in sorted(Path('$INSIGHT_ROOT/.insight/designs').glob('*.yaml')):
    d = yaml.load(f.open('r'))
    if not isinstance(d, dict): continue
    did = d.get('id', '')
    if did == 'DES-C': continue
    designs.append(d)
    rows = 1500000 if did == 'DES-A' else 800000
    sc_map[did] = {'source_registered': True, 'location_ok': True, 'allowlist_ok': True, 'estimated_rows': rows}
print(json.dumps({'designs': designs, 'source_checks_map': sc_map}))
")

echo "$DESIGNS_JSON" | uv run python3 -m skills.premortem.cli \
    --queued --yes --mode review \
    --base-dir "$INSIGHT_ROOT/.insight" \
    --config "$INSIGHT_ROOT/.insight/config.yaml" \
    > /dev/null 2>&1

TOKEN=$(ls -t "$INSIGHT_ROOT/.insight/premortem/"*.yaml 2>/dev/null | head -1 | xargs -I{} uv run python3 -c "
from ruamel.yaml import YAML
yaml = YAML(typ='safe')
with open('{}', 'r') as f: t = yaml.load(f)
print(t['token_id'])
")

# 1st run: kill after 1 design (simulates crash)
export STUB_KILL_AFTER_DESIGNS=1
export STUB_SCENARIO=e2e_02
bash "$PROJECT_ROOT/skills/batch-analysis/launcher.sh" --approved-by "$TOKEN" || true

# 2nd run: resume (unset kill, launcher detects incomplete)
unset STUB_KILL_AFTER_DESIGNS
bash "$PROJECT_ROOT/skills/batch-analysis/launcher.sh" --approved-by "$TOKEN"

# Assertions
uv run python3 tests/e2e/assertions/e2e_02_assert.py

echo "E2E-02: PASSED"
