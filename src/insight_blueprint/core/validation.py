"""Shared validation utilities for core services."""

from __future__ import annotations

import re

SAFE_ID_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")


def validate_id(value: str, name: str = "id") -> None:
    """Raise ValueError if *value* contains characters outside [a-zA-Z0-9_-]."""
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid {name} '{value}': must match [a-zA-Z0-9_-]+")
