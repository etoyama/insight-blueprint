"""Tests for skills/_shared/token_manager.py.

Unit-09: issue (5 cases)
Unit-10: verify (4 cases)
Unit-11: compute_design_hash basic (3 cases)
Unit-12: canonicalization idempotency (10 cases)
Unit-13: verify_design_hash + auto mode (3+1 cases)
Unit-14: atomic dir create (2 cases)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from ruamel.yaml import YAML

JST = ZoneInfo("Asia/Tokyo")


def _make_design_entry(
    design_id: str = "DES-001",
    risk_at_approval: str = "low",
    design_hash: str = "sha256:abc123",
    est_min: float = 18.0,
) -> dict:
    """Helper: build an approved/skipped design dict as token_manager expects."""
    return {
        "design_id": design_id,
        "design_hash": design_hash,
        "risk_at_approval": risk_at_approval,
        "est_min": est_min,
    }


def _make_skipped_entry(
    design_id: str = "DES-099",
    risk_at_approval: str = "hard_block",
    reason: str = "source not registered",
) -> dict:
    return {
        "design_id": design_id,
        "risk_at_approval": risk_at_approval,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Unit-09: TestTokenManagerIssue
# ---------------------------------------------------------------------------


class TestTokenManagerIssue:
    """Unit-09: issue() creates correct YAML token file."""

    def test_issue_writes_file_with_required_fields(self, tmp_path: Path) -> None:
        """t1: Normal issue with 1 approved + 1 skipped creates token file."""
        from skills._shared.token_manager import issue

        approved = [_make_design_entry()]
        skipped = [_make_skipped_entry()]

        token_id = issue(
            approved=approved,
            skipped=skipped,
            approved_by="human",
            automation_mode="review",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        token_path = tmp_path / "premortem" / f"{token_id}.yaml"
        assert token_path.exists()

        yaml = YAML(typ="safe")
        data = yaml.load(token_path)
        assert data["token_id"] == token_id
        assert "created_at" in data
        assert "expires_at" in data
        assert data["approved_by"] == "human"
        assert data["automation_mode"] == "review"
        assert "risk_summary" in data
        assert len(data["approved_designs"]) == 1
        assert len(data["skipped_designs"]) == 1

    def test_issue_token_id_format_jst(self, tmp_path: Path) -> None:
        """t2: token_id is YYYYMMDD_HHmmss format in JST."""
        from skills._shared.token_manager import issue

        token_id = issue(
            approved=[],
            skipped=[],
            approved_by="human",
            automation_mode="manual",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        # Validate format: YYYYMMDD_HHmmss
        assert len(token_id) == 15
        assert token_id[8] == "_"
        # Parse back to verify it's valid datetime
        dt = datetime.strptime(token_id, "%Y%m%d_%H%M%S")
        assert dt is not None

    def test_issue_expires_at_offset_by_ttl(self, tmp_path: Path) -> None:
        """t3: created_at + ttl_hours == expires_at."""
        from skills._shared.token_manager import issue

        token_id = issue(
            approved=[],
            skipped=[],
            approved_by="human",
            automation_mode="review",
            ttl_hours=12,
            base_dir=tmp_path,
        )

        token_path = tmp_path / "premortem" / f"{token_id}.yaml"
        yaml = YAML(typ="safe")
        data = yaml.load(token_path)

        created = datetime.fromisoformat(data["created_at"])
        expires = datetime.fromisoformat(data["expires_at"])
        assert expires - created == timedelta(hours=12)

    def test_issue_empty_approved_and_skipped(self, tmp_path: Path) -> None:
        """t4: Empty approved/skipped still issues successfully."""
        from skills._shared.token_manager import issue

        token_id = issue(
            approved=[],
            skipped=[],
            approved_by="human",
            automation_mode="manual",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        token_path = tmp_path / "premortem" / f"{token_id}.yaml"
        assert token_path.exists()
        yaml = YAML(typ="safe")
        data = yaml.load(token_path)
        assert data["approved_designs"] == []
        assert data["skipped_designs"] == []

    def test_issue_auto_mode_approved_by_auto(self, tmp_path: Path) -> None:
        """t5: automation_mode='auto' writes approved_by='auto'."""
        from skills._shared.token_manager import issue

        token_id = issue(
            approved=[_make_design_entry()],
            skipped=[],
            approved_by="auto",
            automation_mode="auto",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        token_path = tmp_path / "premortem" / f"{token_id}.yaml"
        yaml = YAML(typ="safe")
        data = yaml.load(token_path)
        assert data["approved_by"] == "auto"


# ---------------------------------------------------------------------------
# Unit-10: TestTokenManagerVerify
# ---------------------------------------------------------------------------


class TestTokenManagerVerify:
    """Unit-10: verify() TTL validation."""

    def _write_token(
        self,
        tmp_path: Path,
        token_id: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        """Write a minimal token YAML for verification tests."""
        yaml = YAML()
        data = {
            "token_id": token_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "approved_by": "human",
            "automation_mode": "review",
            "risk_summary": {},
            "approved_designs": [],
            "skipped_designs": [],
        }
        premortem_dir = tmp_path / "premortem"
        premortem_dir.mkdir(parents=True, exist_ok=True)
        with (premortem_dir / f"{token_id}.yaml").open("w") as f:
            yaml.dump(data, f)

    def test_verify_nonexistent_token_not_found(self, tmp_path: Path) -> None:
        """t1: Non-existent token -> ok=False, reason='not_found', token=None."""
        from skills._shared.token_manager import verify

        result = verify("nonexistent_token", datetime.now(JST), base_dir=tmp_path)
        assert result.ok is False
        assert result.reason == "not_found"
        assert result.token is None

    def test_verify_within_ttl_ok(self, tmp_path: Path) -> None:
        """t2: Token within TTL -> ok=True, reason=None, token loaded."""
        from skills._shared.token_manager import verify

        now = datetime.now(JST)
        token_id = "20260418_183015"
        self._write_token(
            tmp_path, token_id, now - timedelta(hours=1), now + timedelta(hours=23)
        )

        result = verify(token_id, now, base_dir=tmp_path)
        assert result.ok is True
        assert result.reason is None
        assert result.token is not None
        assert result.token.token_id == token_id

    def test_verify_expired_returns_error(self, tmp_path: Path) -> None:
        """t3: Expired token -> ok=False, reason='expired', token loaded."""
        from skills._shared.token_manager import verify

        now = datetime.now(JST)
        token_id = "20260417_183015"
        self._write_token(
            tmp_path, token_id, now - timedelta(hours=25), now - timedelta(hours=1)
        )

        result = verify(token_id, now, base_dir=tmp_path)
        assert result.ok is False
        assert result.reason == "expired"
        assert result.token is not None

    def test_verify_exact_expiry_boundary_is_valid(self, tmp_path: Path) -> None:
        """t4: expires_at == now -> valid (< strict comparison means NOT expired)."""
        from skills._shared.token_manager import verify

        now = datetime.now(JST)
        token_id = "20260418_183000"
        self._write_token(tmp_path, token_id, now - timedelta(hours=24), now)

        # now < expires_at is False when equal => but spec says boundary is valid
        # "期限切れ判定は now < expires_at 厳密比較で判定（境界でも有効とする）"
        # This means: token is valid when now < expires_at is True.
        # When now == expires_at, now < expires_at is False, so... BUT spec says "boundary is valid".
        # Re-reading: "境界でも有効とする" => at boundary, treat as valid.
        # So we need now <= expires_at for validity.
        result = verify(token_id, now, base_dir=tmp_path)
        assert result.ok is True
        assert result.reason is None


# ---------------------------------------------------------------------------
# Unit-14: TestTokenManagerAtomicDir
# ---------------------------------------------------------------------------


class TestTokenManagerAtomicDir:
    """Unit-14: .insight/premortem/ atomic directory creation."""

    def test_directory_missing_created_before_write(self, tmp_path: Path) -> None:
        """t1: premortem/ doesn't exist -> issue creates it."""
        from skills._shared.token_manager import issue

        premortem_dir = tmp_path / "premortem"
        assert not premortem_dir.exists()

        token_id = issue(
            approved=[],
            skipped=[],
            approved_by="human",
            automation_mode="manual",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        assert premortem_dir.exists()
        assert (premortem_dir / f"{token_id}.yaml").exists()

    def test_directory_exists_reused(self, tmp_path: Path) -> None:
        """t2: premortem/ already exists -> issue succeeds."""
        from skills._shared.token_manager import issue

        premortem_dir = tmp_path / "premortem"
        premortem_dir.mkdir(parents=True)

        token_id = issue(
            approved=[_make_design_entry()],
            skipped=[],
            approved_by="human",
            automation_mode="review",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        assert (premortem_dir / f"{token_id}.yaml").exists()


# ---------------------------------------------------------------------------
# Helper: canonical design dict for hash tests
# ---------------------------------------------------------------------------


def _base_design() -> dict:
    """A minimal design dict with all hash-relevant fields."""
    return {
        "id": "DES-001",
        "hypothesis": "Sales correlate with time slots",
        "intent": "exploratory",
        "methodology": "correlation analysis",
        "source_ids": ["sales_raw", "time_slots"],
        "metrics": [{"name": "r_squared", "threshold": 0.7}],
        "acceptance_criteria": [{"type": "threshold", "value": 0.05}],
        "status": "analyzing",
        "next_action": {"type": "batch_execute"},
        "created_at": "2026-04-18T10:00:00+09:00",
        "updated_at": "2026-04-18T12:00:00+09:00",
        "review_history": [{"reviewer": "human", "date": "2026-04-17"}],
    }


# ---------------------------------------------------------------------------
# Unit-11: TestComputeDesignHashBasic
# ---------------------------------------------------------------------------


class TestComputeDesignHashBasic:
    """Unit-11: compute_design_hash basic properties."""

    def test_same_content_same_hash(self) -> None:
        """t1: Identical content produces identical hash."""
        from skills._shared.token_manager import compute_design_hash

        d1 = _base_design()
        d2 = _base_design()
        assert compute_design_hash(d1) == compute_design_hash(d2)

    def test_hash_has_sha256_prefix(self) -> None:
        """t2: Hash starts with 'sha256:'."""
        from skills._shared.token_manager import compute_design_hash

        h = compute_design_hash(_base_design())
        assert h.startswith("sha256:")

    def test_hash_hex_part_is_64_chars(self) -> None:
        """t3: Hex portion is exactly 64 characters."""
        from skills._shared.token_manager import compute_design_hash

        h = compute_design_hash(_base_design())
        hex_part = h.removeprefix("sha256:")
        assert len(hex_part) == 64
        # Validate it's valid hex
        int(hex_part, 16)


# ---------------------------------------------------------------------------
# Unit-12: TestComputeDesignHashCanonicalization
# ---------------------------------------------------------------------------


class TestComputeDesignHashCanonicalization:
    """Unit-12: canonicalization idempotency (10 cases)."""

    def _hash(self, design: dict) -> str:
        from skills._shared.token_manager import compute_design_hash

        return compute_design_hash(design)

    def test_hash_excludes_id_field(self) -> None:
        """t1: Different id -> same hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["id"] = "DES-999"
        assert self._hash(d1) == self._hash(d2)

    def test_hash_excludes_created_at(self) -> None:
        """t2: Different created_at -> same hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["created_at"] = "2020-01-01T00:00:00+09:00"
        assert self._hash(d1) == self._hash(d2)

    def test_hash_excludes_updated_at(self) -> None:
        """t3: Different updated_at -> same hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["updated_at"] = "2099-12-31T23:59:59+09:00"
        assert self._hash(d1) == self._hash(d2)

    def test_hash_excludes_status(self) -> None:
        """t4: Different status -> same hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["status"] = "supported"
        assert self._hash(d1) == self._hash(d2)

    def test_hash_excludes_next_action(self) -> None:
        """t5: Different next_action -> same hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["next_action"] = {"type": "manual_review"}
        assert self._hash(d1) == self._hash(d2)

    def test_hash_excludes_review_history(self) -> None:
        """t6: Different review_history -> same hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["review_history"] = []
        assert self._hash(d1) == self._hash(d2)

    def test_hash_source_ids_order_insensitive(self) -> None:
        """t7: source_ids in different order -> same hash (sorted)."""
        d1 = _base_design()
        d2 = _base_design()
        d2["source_ids"] = ["time_slots", "sales_raw"]  # reversed
        assert self._hash(d1) == self._hash(d2)

    def test_hash_metrics_key_order_insensitive(self) -> None:
        """t8: metrics dict with different key order -> same hash."""
        d1 = _base_design()
        d1["metrics"] = [{"name": "r_squared", "threshold": 0.7}]
        d2 = _base_design()
        d2["metrics"] = [{"threshold": 0.7, "name": "r_squared"}]
        assert self._hash(d1) == self._hash(d2)

    def test_hash_changes_on_methodology_change(self) -> None:
        """t9: methodology change -> different hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["methodology"] = "regression analysis"
        assert self._hash(d1) != self._hash(d2)

    def test_hash_changes_on_hypothesis_change(self) -> None:
        """t10: hypothesis change -> different hash."""
        d1 = _base_design()
        d2 = _base_design()
        d2["hypothesis"] = "Something completely different"
        assert self._hash(d1) != self._hash(d2)


# ---------------------------------------------------------------------------
# Unit-13: TestTokenManagerHashVerify + Auto Mode
# ---------------------------------------------------------------------------


class TestTokenManagerHashVerify:
    """Unit-13: verify_design_hash checks."""

    def test_matching_hash_returns_true(self) -> None:
        """t1: Matching hash -> True."""
        from skills._shared.models import Token
        from skills._shared.token_manager import verify_design_hash

        token = Token(
            token_id="20260418_183015",
            created_at="2026-04-18T18:30:15+09:00",
            expires_at="2026-04-19T18:30:15+09:00",
            approved_by="human",
            automation_mode="review",
            approved_designs=[
                {
                    "design_id": "DES-042",
                    "design_hash": "sha256:abc123",
                    "risk_at_approval": "low",
                    "est_min": 18.0,
                }
            ],
            skipped_designs=[],
        )
        assert verify_design_hash(token, "DES-042", "sha256:abc123") is True

    def test_mismatched_hash_returns_false(self) -> None:
        """t2: Mismatched hash -> False."""
        from skills._shared.models import Token
        from skills._shared.token_manager import verify_design_hash

        token = Token(
            token_id="20260418_183015",
            created_at="2026-04-18T18:30:15+09:00",
            expires_at="2026-04-19T18:30:15+09:00",
            approved_by="human",
            automation_mode="review",
            approved_designs=[
                {
                    "design_id": "DES-042",
                    "design_hash": "sha256:abc123",
                    "risk_at_approval": "low",
                    "est_min": 18.0,
                }
            ],
            skipped_designs=[],
        )
        assert verify_design_hash(token, "DES-042", "sha256:different") is False

    def test_design_not_in_token_returns_false(self) -> None:
        """t3: design_id not in token -> False."""
        from skills._shared.models import Token
        from skills._shared.token_manager import verify_design_hash

        token = Token(
            token_id="20260418_183015",
            created_at="2026-04-18T18:30:15+09:00",
            expires_at="2026-04-19T18:30:15+09:00",
            approved_by="human",
            automation_mode="review",
            approved_designs=[],
            skipped_designs=[],
        )
        assert verify_design_hash(token, "DES-999", "sha256:abc") is False


class TestTokenManagerAutoMode:
    """Unit-13 additional: auto mode distribution in issue()."""

    def test_issue_auto_mode_includes_high_in_approved(self, tmp_path: Path) -> None:
        """Auto mode: HIGH design is in approved_designs, not in skipped."""
        from skills._shared.token_manager import issue

        approved = [_make_design_entry(design_id="DES-042", risk_at_approval="high")]
        skipped: list[dict] = []

        token_id = issue(
            approved=approved,
            skipped=skipped,
            approved_by="auto",
            automation_mode="auto",
            ttl_hours=24,
            base_dir=tmp_path,
        )

        token_path = tmp_path / "premortem" / f"{token_id}.yaml"
        yaml = YAML(typ="safe")
        data = yaml.load(token_path)

        assert len(data["approved_designs"]) == 1
        assert data["approved_designs"][0]["design_id"] == "DES-042"
        assert data["approved_designs"][0]["risk_at_approval"] == "high"
        assert len(data["skipped_designs"]) == 0
