"""Unit-08: PremortemConfig — config defaults and partial override tests."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML


class TestPremortemConfigDefaults:
    """Verify load_premortem_config returns correct defaults."""

    def test_defaults_when_no_config_file(self, tmp_path: Path) -> None:
        """config.yaml does not exist -> all defaults applied."""
        from skills._shared.config_loader import load_premortem_config

        cfg = load_premortem_config(tmp_path / "nonexistent.yaml")

        assert cfg.time_high_min == 120
        assert cfg.time_medium_min == 45
        assert cfg.history_min_samples == 3
        assert cfg.buffer == 1.3
        assert cfg.success_rate_high_threshold == 0.6
        assert cfg.static_rows_high == 10_000_000
        assert cfg.token_ttl_hours == 24
        assert cfg.automation == "review"
        assert cfg.approved_by_required is False
        assert cfg.max_turns == 200
        assert cfg.max_budget_usd == 10

    def test_partial_override(self, tmp_path: Path) -> None:
        """Only premortem.time_high_min overridden -> rest are defaults."""
        from skills._shared.config_loader import load_premortem_config

        config_path = tmp_path / "config.yaml"
        yaml = YAML()
        yaml.dump({"premortem": {"time_high_min": 180}}, config_path)

        cfg = load_premortem_config(config_path)

        assert cfg.time_high_min == 180
        # All others remain default
        assert cfg.time_medium_min == 45
        assert cfg.history_min_samples == 3
        assert cfg.buffer == 1.3
        assert cfg.success_rate_high_threshold == 0.6
        assert cfg.static_rows_high == 10_000_000
        assert cfg.token_ttl_hours == 24
        assert cfg.automation == "review"
        assert cfg.approved_by_required is False
        assert cfg.max_turns == 200
        assert cfg.max_budget_usd == 10

    def test_batch_automation_default_review(self, tmp_path: Path) -> None:
        """batch: section absent -> automation defaults to 'review'."""
        from skills._shared.config_loader import load_premortem_config

        config_path = tmp_path / "config.yaml"
        yaml = YAML()
        yaml.dump({"schema_version": 1}, config_path)

        cfg = load_premortem_config(config_path)
        assert cfg.automation == "review"

    def test_approved_by_required_default_false(self, tmp_path: Path) -> None:
        """batch.approved_by_required absent -> defaults to False (Phase A)."""
        from skills._shared.config_loader import load_premortem_config

        config_path = tmp_path / "config.yaml"
        yaml = YAML()
        yaml.dump({"batch": {"automation": "manual"}}, config_path)

        cfg = load_premortem_config(config_path)
        assert cfg.approved_by_required is False
        assert cfg.automation == "manual"
