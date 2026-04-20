#!/usr/bin/env bash
# launcher.sh -- Pre-processing wrapper for /batch-analysis
#
# Handles: config loading, crash recovery, token validation,
#          /premortem dispatch, claude execution, session_id extraction.
#
# Usage:
#   bash launcher.sh [--approved-by TOKEN]
#
# Exit codes:
#   0 -- normal completion
#   1 -- Phase B rejection, token expired, or unexpected error

set -euo pipefail

# ---------------------------------------------------------------------------
# Portable helpers (macOS + Linux)
# ---------------------------------------------------------------------------

_iso_now() {
    # ISO 8601 timestamp in JST (works on macOS and GNU date)
    if date --version >/dev/null 2>&1; then
        TZ=Asia/Tokyo date -Iseconds
    else
        TZ=Asia/Tokyo date +%Y-%m-%dT%H:%M:%S%z
    fi
}

_timestamp() {
    TZ=Asia/Tokyo date +%Y%m%d_%H%M%S
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

APPROVED_BY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --approved-by)
            APPROVED_BY="${2:-}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Override paths via env vars (used by integration tests)
INSIGHT_BASE_DIR="${INSIGHT_BASE_DIR:-.insight}"
INSIGHT_CONFIG_PATH="${INSIGHT_CONFIG_PATH:-${INSIGHT_BASE_DIR}/config.yaml}"

# ---------------------------------------------------------------------------
# Step 1: Config loading
# ---------------------------------------------------------------------------

read_config() {
    python3 -c "
import sys
sys.path.insert(0, '.')
from skills._shared.config_loader import load_premortem_config
from pathlib import Path
cfg = load_premortem_config(Path('${INSIGHT_CONFIG_PATH}'))
print(f'AUTOMATION={cfg.automation}')
print(f'APPROVED_BY_REQUIRED={str(cfg.approved_by_required).lower()}')
print(f'BATCH_MAX_TURNS={cfg.max_turns}')
print(f'BATCH_MAX_BUDGET_USD={cfg.max_budget_usd}')
print(f'TOKEN_TTL_HOURS={cfg.token_ttl_hours}')
"
}

eval "$(read_config)"
export BATCH_MAX_TURNS="${BATCH_MAX_TURNS:-200}"
export BATCH_MAX_BUDGET_USD="${BATCH_MAX_BUDGET_USD:-10}"

# ---------------------------------------------------------------------------
# Step 2: Crash recovery
# ---------------------------------------------------------------------------

RESUME_SESSION_ID=""
RESUME_RUN_DIR=""

check_crash_recovery() {
    local result
    result=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from skills._shared.crash_recovery import detect_incomplete, unfinished_designs
from skills._shared.token_manager import verify
from skills._shared.models import RunRef
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from ruamel.yaml import YAML

base_dir = Path('${INSIGHT_BASE_DIR}')
refs = detect_incomplete(base_dir=base_dir)
if not refs:
    print(json.dumps({'has_incomplete': False}))
    sys.exit(0)

latest = refs[0]
yaml = YAML(typ='safe')
run_path = Path(latest.run_yaml_path)
with run_path.open('r') as f:
    run_data = yaml.load(f)

token_id = run_data.get('premortem_token')
session_id = run_data.get('session_id')

if not token_id or not session_id:
    print(json.dumps({'has_incomplete': True, 'token_valid': False, 'run_id': latest.run_id}))
    sys.exit(0)

now = datetime.now(ZoneInfo('Asia/Tokyo'))
vr = verify(token_id, now, base_dir=base_dir)
unfinished = unfinished_designs(latest, base_dir=base_dir)

print(json.dumps({
    'has_incomplete': True,
    'token_valid': vr.ok,
    'run_id': latest.run_id,
    'session_id': session_id,
    'token_id': token_id,
    'unfinished_count': len(unfinished)
}))
" 2>/dev/null) || true

    if [ -z "$result" ]; then
        return
    fi

    local has_incomplete
    has_incomplete=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_incomplete', False))")

    if [ "$has_incomplete" = "True" ]; then
        local run_id session_id token_valid
        run_id=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))")
        session_id=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
        token_valid=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token_valid', False))")

        echo "Detected incomplete run: $run_id" >&2

        if [ "$token_valid" = "True" ] && [ -n "$session_id" ]; then
            RESUME_SESSION_ID="$session_id"
            RESUME_RUN_DIR=".insight/runs/$run_id"
            echo "Will resume session: $session_id" >&2
        else
            echo "Token expired or no session_id, finalizing incomplete run: $run_id" >&2
            python3 -c "
import sys
sys.path.insert(0, '.')
from pathlib import Path
from skills._shared.crash_recovery import detect_incomplete, unfinished_designs, finalize_incomplete
base_dir = Path('${INSIGHT_BASE_DIR}')
refs = detect_incomplete(base_dir=base_dir)
if refs:
    latest = refs[0]
    unfinished = unfinished_designs(latest, base_dir=base_dir)
    if unfinished:
        finalize_incomplete(latest.run_id, unfinished, 'token_expired_or_crashed', base_dir=base_dir)
" 2>/dev/null || true
        fi
    fi
}

check_crash_recovery

# ---------------------------------------------------------------------------
# Step 3: --approved-by validation (Phase A / Phase B)
# ---------------------------------------------------------------------------

if [ -z "$APPROVED_BY" ]; then
    if [ "$APPROVED_BY_REQUIRED" = "true" ]; then
        echo "--approved-by is required; run /premortem first" >&2
        exit 1
    else
        echo "WARNING: running without /premortem approval (Phase A transitional)" >&2
        AUTOMATION_MODE="legacy"
        TOKEN_ID=""
    fi
else
    # Validate token TTL
    token_check=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from pathlib import Path
from skills._shared.token_manager import verify
from datetime import datetime
from zoneinfo import ZoneInfo
base_dir = Path('${INSIGHT_BASE_DIR}')
now = datetime.now(ZoneInfo('Asia/Tokyo'))
result = verify('$APPROVED_BY', now, base_dir=base_dir)
print(json.dumps({'ok': result.ok, 'reason': result.reason}))
" 2>/dev/null) || true

    if [ -z "$token_check" ]; then
        echo "Failed to verify token" >&2
        exit 1
    fi

    token_ok=$(echo "$token_check" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok', False))")
    token_reason=$(echo "$token_check" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reason',''))")

    if [ "$token_ok" != "True" ]; then
        if [ "$token_reason" = "expired" ]; then
            echo "Token expired: $APPROVED_BY" >&2
        elif [ "$token_reason" = "not_found" ]; then
            echo "Token not found: $APPROVED_BY" >&2
        else
            echo "Token verification failed: $token_reason" >&2
        fi
        exit 1
    fi

    AUTOMATION_MODE="$AUTOMATION"
    TOKEN_ID="$APPROVED_BY"
fi

# ---------------------------------------------------------------------------
# Step 4: Setup RUN_DIR and init run.yaml
# ---------------------------------------------------------------------------

if [ -n "$RESUME_SESSION_ID" ] && [ -n "$RESUME_RUN_DIR" ]; then
    RUN_DIR="$RESUME_RUN_DIR"
else
    RUN_DIR="${INSIGHT_BASE_DIR}/runs/$(_timestamp)"
    mkdir -p "$RUN_DIR"

    python3 -c "
import sys
sys.path.insert(0, '.')
from pathlib import Path
from skills._shared.manifest_writer import init_run
init_run(
    run_id='$(basename "$RUN_DIR")',
    session_id=None,
    automation_mode='${AUTOMATION_MODE:-review}',
    token_id='${TOKEN_ID}' if '${TOKEN_ID}' else None,
    base_dir=Path('${INSIGHT_BASE_DIR}'),
)
" 2>/dev/null || echo "WARNING: failed to init run.yaml" >&2
fi

export RUN_DIR

# ---------------------------------------------------------------------------
# Step 5: Execute claude
# ---------------------------------------------------------------------------

CLAUDE_SKILL_DIR="$SCRIPT_DIR"

if [ -n "$RESUME_SESSION_ID" ]; then
    echo "Resuming session: $RESUME_SESSION_ID" >&2
    claude -p "$(cat "${CLAUDE_SKILL_DIR}/references/batch-prompt.md")" \
        --model sonnet \
        --output-format stream-json \
        --include-hook-events \
        --fallback-model sonnet \
        --max-turns "${BATCH_MAX_TURNS}" \
        --resume "$RESUME_SESSION_ID" \
        --allowedTools "mcp__insight-blueprint__list_analysis_designs,mcp__insight-blueprint__get_analysis_design,mcp__insight-blueprint__get_table_schema,mcp__insight-blueprint__update_analysis_design,mcp__insight-blueprint__transition_design_status,mcp__insight-blueprint__search_catalog,mcp__context7__resolve-library-id,mcp__context7__query-docs,Read,Write,Bash,Glob,Grep" \
        --permission-mode bypassPermissions \
        --max-budget-usd "${BATCH_MAX_BUDGET_USD}" \
        >> "$RUN_DIR/events.jsonl" 2>&1 || true
else
    claude -p "$(cat "${CLAUDE_SKILL_DIR}/references/batch-prompt.md")" \
        --model sonnet \
        --output-format stream-json \
        --include-hook-events \
        --fallback-model sonnet \
        --max-turns "${BATCH_MAX_TURNS}" \
        --allowedTools "mcp__insight-blueprint__list_analysis_designs,mcp__insight-blueprint__get_analysis_design,mcp__insight-blueprint__get_table_schema,mcp__insight-blueprint__update_analysis_design,mcp__insight-blueprint__transition_design_status,mcp__insight-blueprint__search_catalog,mcp__context7__resolve-library-id,mcp__context7__query-docs,Read,Write,Bash,Glob,Grep" \
        --permission-mode bypassPermissions \
        --max-budget-usd "${BATCH_MAX_BUDGET_USD}" \
        > "$RUN_DIR/events.jsonl" 2>&1 || true
fi

# ---------------------------------------------------------------------------
# Step 7: Extract session_id from events.jsonl
# ---------------------------------------------------------------------------

if [ -f "$RUN_DIR/events.jsonl" ]; then
    SESSION_ID=""

    # Try to extract from first system/init event
    if command -v jq >/dev/null 2>&1; then
        SESSION_ID=$(jq -r 'select(.type=="system" and .subtype=="init") | .session_id' "$RUN_DIR/events.jsonl" 2>/dev/null | head -1) || true
    fi

    # Fallback: try second-to-last line if last line is corrupted
    if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
        echo "WARNING: Could not extract session_id from first init event, trying fallback" >&2
        if command -v jq >/dev/null 2>&1; then
            # Read line by line, find the first valid system/init
            while IFS= read -r line; do
                local_sid=$(echo "$line" | jq -r 'select(.type=="system" and .subtype=="init") | .session_id' 2>/dev/null) || true
                if [ -n "$local_sid" ] && [ "$local_sid" != "null" ]; then
                    SESSION_ID="$local_sid"
                    break
                fi
            done < "$RUN_DIR/events.jsonl"
        fi
    fi

    if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        python3 -c "
import sys
sys.path.insert(0, '.')
from pathlib import Path
from skills._shared.manifest_writer import update_run_session_id
update_run_session_id('$(basename "$RUN_DIR")', '$SESSION_ID', base_dir=Path('${INSIGHT_BASE_DIR}'))
" 2>/dev/null || echo "WARNING: failed to update session_id in run.yaml" >&2
    fi
fi

# ---------------------------------------------------------------------------
# Step 8: Auto mode HIGH warning
# ---------------------------------------------------------------------------

if [ "${AUTOMATION_MODE:-}" = "auto" ] && [ -n "$TOKEN_ID" ]; then
    has_high=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from pathlib import Path
from skills._shared.token_manager import verify
from datetime import datetime
from zoneinfo import ZoneInfo
base_dir = Path('${INSIGHT_BASE_DIR}')
now = datetime.now(ZoneInfo('Asia/Tokyo'))
result = verify('$TOKEN_ID', now, base_dir=base_dir)
if result.ok and result.token:
    for d in result.token.approved_designs:
        if d.get('risk_at_approval') == 'high':
            print('yes')
            sys.exit(0)
print('no')
" 2>/dev/null) || true

    if [ "$has_high" = "yes" ]; then
        echo "" >> "$RUN_DIR/summary.md" 2>/dev/null || true
        echo "WARNING: HIGH risk executed without human approval" >> "$RUN_DIR/summary.md" 2>/dev/null || true
    fi
fi

echo "Batch execution complete. Run directory: $RUN_DIR" >&2
exit 0
