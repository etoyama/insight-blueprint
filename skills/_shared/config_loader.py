"""Load PremortemConfig from .insight/config.yaml with default merging."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from skills._shared.models import PremortemConfig

# Mapping: config YAML key -> PremortemConfig field name
_PREMORTEM_KEY_MAP: dict[str, str] = {
    "time_high_min": "time_high_min",
    "time_medium_min": "time_medium_min",
    "history_min_samples": "history_min_samples",
    "history_extrapolation_buffer": "buffer",
    "success_rate_high_threshold": "success_rate_high_threshold",
    "static_rows_high": "static_rows_high",
    "token_ttl_hours": "token_ttl_hours",
}

_BATCH_KEY_MAP: dict[str, str] = {
    "automation": "automation",
    "approved_by_required": "approved_by_required",
    "max_turns": "max_turns",
    "max_budget_usd": "max_budget_usd",
}


def load_premortem_config(path: Path) -> PremortemConfig:
    """Load config from *path*, merging with defaults.

    If the file does not exist or relevant sections are absent,
    ``PremortemConfig()`` defaults are used.
    """
    path = Path(path)
    if not path.exists():
        return PremortemConfig()

    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.load(f)

    if not isinstance(raw, dict):
        return PremortemConfig()

    overrides: dict[str, object] = {}

    # premortem section
    premortem_section = raw.get("premortem")
    if isinstance(premortem_section, dict):
        for yaml_key, field_name in _PREMORTEM_KEY_MAP.items():
            if yaml_key in premortem_section:
                overrides[field_name] = premortem_section[yaml_key]

    # batch section
    batch_section = raw.get("batch")
    if isinstance(batch_section, dict):
        for yaml_key, field_name in _BATCH_KEY_MAP.items():
            if yaml_key in batch_section:
                overrides[field_name] = batch_section[yaml_key]

    return PremortemConfig(**overrides)  # type: ignore[arg-type]
