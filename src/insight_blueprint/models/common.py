"""Shared timezone utilities."""

from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def now_jst() -> datetime:
    """Return current datetime in JST timezone."""
    return datetime.now(tz=JST)
