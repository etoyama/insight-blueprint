"""Approval token lifecycle: issue, verify, design_hash computation.

Tokens are written to ``{base_dir}/premortem/{token_id}.yaml``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

from skills._shared._atomic import atomic_write_yaml
from skills._shared.models import Token, TokenVerifyResult

JST = ZoneInfo("Asia/Tokyo")

# Default base_dir (production); tests override via parameter.
_DEFAULT_BASE_DIR = Path(".insight")


def _now_jst() -> datetime:
    return datetime.now(JST)


def issue(
    approved: list[dict],
    skipped: list[dict],
    approved_by: str,
    automation_mode: str,
    ttl_hours: int,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> str:
    """Issue an approval token and write it atomically.

    Returns the token_id (``YYYYMMDD_HHmmss`` JST format).
    """
    now = _now_jst()
    token_id = now.strftime("%Y%m%d_%H%M%S")
    created_at = now.isoformat()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat()

    # Build risk_summary from approved + skipped
    risk_summary: dict[str, int] = {}
    for entry in approved:
        level = entry.get("risk_at_approval", "unknown")
        risk_summary[level] = risk_summary.get(level, 0) + 1
    for entry in skipped:
        level = entry.get("risk_at_approval", "unknown")
        risk_summary[level] = risk_summary.get(level, 0) + 1

    token_data = {
        "token_id": token_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "approved_by": approved_by,
        "automation_mode": automation_mode,
        "risk_summary": risk_summary,
        "approved_designs": list(approved),
        "skipped_designs": list(skipped),
    }

    token_path = base_dir / "premortem" / f"{token_id}.yaml"
    atomic_write_yaml(token_path, token_data)

    return token_id


def _load_token(token_id: str, base_dir: Path) -> Token | None:
    """Load a token from YAML, returning None if not found."""
    token_path = base_dir / "premortem" / f"{token_id}.yaml"
    if not token_path.exists():
        return None

    yaml = YAML(typ="safe")
    with token_path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)

    return Token(
        token_id=data["token_id"],
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        approved_by=data["approved_by"],
        automation_mode=data["automation_mode"],
        approved_designs=data.get("approved_designs", []),
        skipped_designs=data.get("skipped_designs", []),
    )


def verify(
    token_id: str,
    now: datetime,
    base_dir: Path = _DEFAULT_BASE_DIR,
) -> TokenVerifyResult:
    """Verify a token's existence and TTL.

    Boundary rule: ``now <= expires_at`` means valid (boundary is valid).
    """
    token = _load_token(token_id, base_dir)
    if token is None:
        return TokenVerifyResult(ok=False, reason="not_found", token=None)

    expires_at = datetime.fromisoformat(token.expires_at)
    if now > expires_at:
        return TokenVerifyResult(ok=False, reason="expired", token=token)

    return TokenVerifyResult(ok=True, reason=None, token=token)


# ---------------------------------------------------------------------------
# Design hash canonicalization (FR-3.4)
# ---------------------------------------------------------------------------

# Fields included in the hash input.
_HASH_INCLUDE_FIELDS = (
    "hypothesis",
    "intent",
    "methodology",
    "source_ids",
    "metrics",
    "acceptance_criteria",
)

# Fields explicitly excluded (present in design dict but not hashed).
_HASH_EXCLUDE_FIELDS = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "status",
        "next_action",
        "review_history",
    }
)


def compute_design_hash(design: dict) -> str:
    """Compute a deterministic sha256 hash of a design's semantic fields.

    Canonicalization:
      1. Extract only _HASH_INCLUDE_FIELDS.
      2. Sort ``source_ids`` alphabetically.
      3. Use ``json.dumps(sort_keys=True, ensure_ascii=False,
         separators=(",", ":"))`` for deterministic serialisation.
      4. Return ``"sha256:" + hex_digest``.
    """
    canonical: dict = {}
    for field in _HASH_INCLUDE_FIELDS:
        value = design.get(field)
        if field == "source_ids" and isinstance(value, list):
            value = sorted(value)
        canonical[field] = value

    serialised = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    hex_digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    return f"sha256:{hex_digest}"


def verify_design_hash(token: Token, design_id: str, current_hash: str) -> bool:
    """Check whether *current_hash* matches the hash stored in *token* for *design_id*."""
    for entry in token.approved_designs:
        if entry.get("design_id") == design_id:
            return entry.get("design_hash") == current_hash
    return False
