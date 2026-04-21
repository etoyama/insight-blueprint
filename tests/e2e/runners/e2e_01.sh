#!/usr/bin/env bash
# E2E-01: Overnight happy path (3 designs, mixed risk)
# Runs: setup -> premortem -> token -> batch-analysis -> assert -> teardown
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Setup -- source exports from setup.py
eval "$(uv run python3 tests/e2e/harness/setup.py --scenario e2e_01)"

# Teardown trap (always runs)
teardown() { uv run python3 tests/e2e/harness/teardown.py 2>/dev/null || true; }
trap teardown EXIT

# Prepare premortem input: pipe design data + source checks as JSON
DESIGNS_JSON=$(uv run python3 -c "
import json
from pathlib import Path
from ruamel.yaml import YAML
yaml = YAML(typ='safe')
designs = []
sc_map = {}
designs_dir = Path('$INSIGHT_ROOT/.insight/designs')
for f in sorted(designs_dir.glob('*.yaml')):
    d = yaml.load(f.open('r'))
    if not isinstance(d, dict): continue
    designs.append(d)
    did = d.get('id', '')
    # DES-C has >10M rows (HIGH), others are normal
    rows = 15000000 if did == 'DES-C' else 1500000 if did == 'DES-A' else 800000
    sc_map[did] = {'source_registered': True, 'location_ok': True, 'allowlist_ok': True, 'estimated_rows': rows}
print(json.dumps({'designs': designs, 'source_checks_map': sc_map}))
")

# Run /premortem in review+yes mode: HIGH (DES-C) -> exit 2
PREMORTEM_EXIT=0
echo "$DESIGNS_JSON" | uv run python3 -m skills.premortem.cli \
    --queued --yes --mode review \
    --base-dir "$INSIGHT_ROOT/.insight" \
    --config "$INSIGHT_ROOT/.insight/config.yaml" \
    > /tmp/e2e_01_premortem.stdout 2>&1 || PREMORTEM_EXIT=$?

if [ "$PREMORTEM_EXIT" -ne 2 ]; then
    echo "FAIL: premortem should exit 2 (HIGH detected), got $PREMORTEM_EXIT" >&2
    cat /tmp/e2e_01_premortem.stdout >&2
    exit 1
fi

# Re-run premortem without DES-C (simulate skip): filter out HIGH
DESIGNS_JSON_NO_HIGH=$(uv run python3 -c "
import json
from pathlib import Path
from ruamel.yaml import YAML
yaml = YAML(typ='safe')
designs = []
sc_map = {}
designs_dir = Path('$INSIGHT_ROOT/.insight/designs')
for f in sorted(designs_dir.glob('*.yaml')):
    d = yaml.load(f.open('r'))
    if not isinstance(d, dict): continue
    did = d.get('id', '')
    if did == 'DES-C': continue  # skip HIGH
    designs.append(d)
    rows = 1500000 if did == 'DES-A' else 800000
    sc_map[did] = {'source_registered': True, 'location_ok': True, 'allowlist_ok': True, 'estimated_rows': rows}
# Add DES-C as skipped context
print(json.dumps({'designs': designs, 'source_checks_map': sc_map}))
")

echo "$DESIGNS_JSON_NO_HIGH" | uv run python3 -m skills.premortem.cli \
    --queued --yes --mode review \
    --base-dir "$INSIGHT_ROOT/.insight" \
    --config "$INSIGHT_ROOT/.insight/config.yaml" \
    > /tmp/e2e_01_premortem2.stdout 2>&1

# Extract token_id from the most recent premortem YAML
TOKEN=$(ls -t "$INSIGHT_ROOT/.insight/premortem/"*.yaml 2>/dev/null | head -1 | xargs -I{} uv run python3 -c "
from ruamel.yaml import YAML
yaml = YAML(typ='safe')
with open('{}', 'r') as f: t = yaml.load(f)
print(t['token_id'])
")

# Add DES-C as skipped in the token (manually patch for complete E2E)
uv run python3 -c "
from ruamel.yaml import YAML
from pathlib import Path
yaml = YAML()
yaml.preserve_quotes = True
tp = Path('$INSIGHT_ROOT/.insight/premortem/${TOKEN}.yaml')
with tp.open('r') as f: t = yaml.load(f)
if not t.get('skipped_designs'): t['skipped_designs'] = []
t['skipped_designs'].append({'design_id': 'DES-C', 'risk_at_approval': 'high', 'reason': 'static_rows > 10M, no history'})
if not t.get('risk_summary'): t['risk_summary'] = {}
t['risk_summary']['high'] = t['risk_summary'].get('high', 0) + 1
with tp.open('w') as f: yaml.dump(t, f)
"

# Run /batch-analysis via launcher.sh with stub claude on PATH
export STUB_SCENARIO=e2e_01
bash "$PROJECT_ROOT/skills/batch-analysis/launcher.sh" --approved-by "$TOKEN"

# Assertions
uv run python3 tests/e2e/assertions/e2e_01_assert.py

echo "E2E-01: PASSED"
