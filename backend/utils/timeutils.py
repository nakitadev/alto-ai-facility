"""
Timezone and date conversion utilities for Bangkok Commercial Tower.
Handles Asia/Bangkok (UTC+7) facility local time and UTC database timestamps.
"""

import re
import time
import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
from backend.config import DEFAULT_TIMEZONE

BANGKOK_TZ = ZoneInfo(DEFAULT_TIMEZONE)
UTC_TZ = ZoneInfo("UTC")

_BASE_DATE_CACHE = None
_CACHE_TIME = 0.0

async def get_base_date() -> Optional[datetime.date]:
    """
    Dynamically anchors Day 1 to the actual earliest sensor reading in TimescaleDB.
    Enables arbitrary multi-week, monthly, or historical datasets without hardcoding.
    """
    global _BASE_DATE_CACHE, _CACHE_TIME
    now = time.time()
    if _BASE_DATE_CACHE and (now - _CACHE_TIME < 60.0):
        return _BASE_DATE_CACHE
    try:
        from backend.database import get_simulated_time_bounds
        bounds = await get_simulated_time_bounds()
        if bounds.get("has_data") and "min_bkk" in bounds and bounds["min_bkk"] != "N/A":
            date_str = bounds["min_bkk"].split(" ")[0]
            _BASE_DATE_CACHE = datetime.date.fromisoformat(date_str)
            _CACHE_TIME = now
            return _BASE_DATE_CACHE
    except Exception:
        pass
    return None

def to_bangkok_time(dt: datetime.datetime) -> datetime.datetime:
    """Converts any datetime to Asia/Bangkok (UTC+7)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(BANGKOK_TZ)

def to_utc_time(dt: datetime.datetime) -> datetime.datetime:
    """Converts any datetime to UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BANGKOK_TZ)
    return dt.astimezone(UTC_TZ)

def format_bangkok_iso(dt: datetime.datetime) -> str:
    """Formats datetime as ISO-8601 string anchored in Bangkok timezone."""
    return to_bangkok_time(dt).isoformat()

def get_office_hours_bounds(target_date: datetime.date) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Returns UTC bounds for Bangkok commercial office hours (08:00 - 18:00 ICT)
    on the given calendar date.
    """
    start_bkk = datetime.datetime(target_date.year, target_date.month, target_date.day, 8, 0, tzinfo=BANGKOK_TZ)
    end_bkk = datetime.datetime(target_date.year, target_date.month, target_date.day, 18, 0, tzinfo=BANGKOK_TZ)
    return start_bkk.astimezone(UTC_TZ), end_bkk.astimezone(UTC_TZ)

async def parse_bangkok_time(time_str: str) -> datetime.datetime:
    """
    Parses various date/time formats asynchronously and returns a UTC datetime.
    Supports:
      - 'Day N HH:MM' offsets from earliest database record
      - ISO-8601 formats and YYYY-MM-DD HH:MM:SS
      - LLM variations with irregular timezone suffixes (+00+07, Z, etc.)
    """
    time_str = time_str.strip()

    # Check for "Day N HH:MM" (derived from actual DB start)
    m_day = re.match(r"(?i)day\s*(\d+)(?:\s+(\d{1,2}):(\d{2}))?", time_str)
    if m_day:
        day_num = int(m_day.group(1))
        hour = int(m_day.group(2)) if m_day.group(2) else 0
        minute = int(m_day.group(3)) if m_day.group(3) else 0
        base_date = await get_base_date() or datetime.date(2026, 9, 1)
        target_date = base_date + datetime.timedelta(days=day_num - 1)
        bkk_dt = datetime.datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=BANGKOK_TZ)
        return bkk_dt.astimezone(UTC_TZ)

    # Try standard ISO or standard format
    clean_str = time_str.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BANGKOK_TZ)
        return dt.astimezone(UTC_TZ)
    except Exception:
        pass

    # Robust regex fallback parsing: handles YYYY-MM-DD, HH:MM:SS, and irregular offsets
    m_date = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?)?", time_str)
    if m_date:
        y, mo, d = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
        h = int(m_date.group(4)) if m_date.group(4) else 0
        mi = int(m_date.group(5)) if m_date.group(5) else 0
        s = int(m_date.group(6)) if m_date.group(6) else 0

        # If explicitly UTC (and not Bangkok +07)
        if "Z" in time_str or ("+00" in time_str and "+07" not in time_str):
            return datetime.datetime(y, mo, d, h, mi, s, tzinfo=UTC_TZ)
        else:
            bkk_dt = datetime.datetime(y, mo, d, h, mi, s, tzinfo=BANGKOK_TZ)
            return bkk_dt.astimezone(UTC_TZ)

    raise ValueError(f"Unable to parse timestamp: {time_str}")
