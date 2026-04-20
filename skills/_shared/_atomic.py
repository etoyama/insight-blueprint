"""Atomic YAML / text write helpers with file-lock protection.

Pattern adapted from ``src/insight_blueprint/storage/yaml_store.py``
(copied, not imported — CR-2 / CR-3 compliance).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from filelock import FileLock
from ruamel.yaml import YAML


def _make_yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


def atomic_write_yaml(path: Path, data: Any) -> None:
    """Write *data* to *path* as YAML, atomically.

    * tempfile is created in the **same directory** (cross-device rename
      avoidance).
    * ``filelock.FileLock`` serialises concurrent / cross-process writes.
    * Parent directories are created on demand.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lock = FileLock(str(path) + ".lock")
    with lock:
        yaml = _make_yaml()
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


def atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically (same guarantees as YAML variant)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lock = FileLock(str(path) + ".lock")
    with lock:
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
