"""Integration tests for token security -- Integ-25.

Verifies that token YAML files contain no sensitive information.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.integration.conftest import (
    build_premortem_payload,
    run_premortem_cli,
)

yaml = YAML(typ="safe")

# Known API key / secret patterns
_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI / Anthropic key
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),  # GitHub token
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API key
    re.compile(r"ya29\.[0-9A-Za-z\-_]+"),  # Google OAuth
    re.compile(r"xox[bpras]-[0-9a-zA-Z\-]+"),  # Slack token
]

# Exhaustive allowed top-level keys in token YAML
_ALLOWED_TOKEN_KEYS = {
    "token_id",
    "created_at",
    "expires_at",
    "approved_by",
    "automation_mode",
    "risk_summary",
    "approved_designs",
    "skipped_designs",
}


def _create_token_file(insight_root: Path) -> Path:
    """Run premortem in auto mode to generate a token, return path."""
    designs = [
        {
            "id": "DES-SEC",
            "hypothesis": "security test",
            "intent": "exploratory",
            "methodology": "test",
            "source_ids": ["sec_src"],
            "metrics": [{"name": "m1", "target": "> 0"}],
            "acceptance_criteria": [{"condition": "m1 > 0", "action": "supports"}],
            "status": "analyzing",
            "next_action": {"type": "batch_execute"},
        }
    ]
    payload = build_premortem_payload(designs, {"DES-SEC": {"estimated_rows": 100_000}})
    run_premortem_cli(
        ["--queued", "--yes", "--mode", "auto", "--base-dir", str(insight_root)],
        payload,
        cwd=insight_root.parent,
    )
    tokens = list((insight_root / "premortem").glob("*.yaml"))
    assert len(tokens) >= 1
    return tokens[0]


def _flatten_yaml_values(data: object) -> list[str]:
    """Recursively extract all string values from nested dict/list."""
    values: list[str] = []
    if isinstance(data, dict):
        for v in data.values():
            values.extend(_flatten_yaml_values(v))
    elif isinstance(data, list):
        for item in data:
            values.extend(_flatten_yaml_values(item))
    elif isinstance(data, str):
        values.append(data)
    return values


# =========================================================================
# Integ-25: Token security
# =========================================================================


class TestTokenSecurity:
    """Integ-25: token YAML contains no sensitive information."""

    @pytest.fixture(autouse=True)
    def _setup(self, insight_root: Path, config_review_a: Path) -> None:
        self.insight_root = insight_root
        self.token_path = _create_token_file(insight_root)
        with self.token_path.open("r") as f:
            self.token_data = yaml.load(f)

    def test_token_fields_exhaustive_list(self) -> None:
        """Token YAML top-level keys are exactly the allowed set."""
        actual_keys = set(self.token_data.keys())
        unexpected = actual_keys - _ALLOWED_TOKEN_KEYS
        assert not unexpected, f"Unexpected token keys: {unexpected}"

    def test_token_no_api_key_patterns(self) -> None:
        """No API key patterns found in any token field value."""
        all_values = _flatten_yaml_values(self.token_data)
        for value in all_values:
            for pattern in _SECRET_PATTERNS:
                assert not pattern.search(value), (
                    f"API key pattern {pattern.pattern} found in token value: {value}"
                )

    def test_token_no_env_var_leakage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Injected env var values do not appear in token."""
        # Inject fake credentials into env
        fake_creds = {
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "OPENAI_API_KEY": "sk-test1234567890abcdefghij",
            "DATABASE_PASSWORD": "super_secret_db_pass_12345",
        }
        for k, v in fake_creds.items():
            monkeypatch.setenv(k, v)

        # Re-create token with env vars set
        token_path = _create_token_file(self.insight_root)
        with token_path.open("r") as f:
            data = yaml.load(f)

        all_values = _flatten_yaml_values(data)
        token_text = " ".join(all_values)

        for env_name, env_value in fake_creds.items():
            assert env_value not in token_text, (
                f"Env var {env_name} value leaked into token"
            )

    def test_design_hash_is_content_hash_not_secret(self) -> None:
        """design_hash follows sha256:XXXX format."""
        for entry in self.token_data.get("approved_designs", []):
            dh = entry.get("design_hash", "")
            assert dh.startswith("sha256:"), f"Invalid hash prefix: {dh}"
            hex_part = dh[len("sha256:") :]
            assert len(hex_part) == 64, f"Hash hex part wrong length: {len(hex_part)}"
            assert all(c in "0123456789abcdef" for c in hex_part), (
                f"Non-hex chars in hash: {hex_part}"
            )
