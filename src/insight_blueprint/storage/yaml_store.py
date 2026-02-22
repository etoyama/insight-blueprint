"""Atomic YAML I/O using ruamel.yaml."""

import os
import tempfile
from pathlib import Path

from ruamel.yaml import YAML


def _make_yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


def read_yaml(path: Path) -> dict:
    """Read YAML file, return {} if file does not exist."""
    if not path.exists():
        return {}
    yaml = _make_yaml()
    with path.open("r", encoding="utf-8") as f:
        result = yaml.load(f)
    return result if result is not None else {}


def write_yaml(path: Path, data: dict) -> None:
    """Write data to YAML atomically (tempfile + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = _make_yaml()
    # temp file must be in SAME directory as target for atomic os.replace
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
