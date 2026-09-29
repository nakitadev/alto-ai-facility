"""
Unit tests for backend/utils/timeutils.py.
Verifies Asia/Bangkok (UTC+7) <-> UTC conversions, Day offsets, office hours, and regex fallbacks.
"""

import pytest
import datetime
from backend.utils.timeutils import (
    BANGKOK_TZ,
    UTC_TZ,
    to_bangkok_time,
    to_utc_time,
    format_bangkok_iso,
    get_office_hours_bounds,
    parse_bangkok_time
)

def test_timezone_conversion_bangkok_to_utc():
    # 08:00 Bangkok is 01:00 UTC
    bkk_dt = datetime.datetime(2026, 9, 1, 8, 0, tzinfo=BANGKOK_TZ)
    utc_dt = to_utc_time(bkk_dt)
    assert utc_dt.hour == 1
    assert utc_dt.day == 1
    assert utc_dt.tzinfo == UTC_TZ

def test_timezone_conversion_utc_to_bangkok():
    # 17:00 UTC is 00:00 next day in Bangkok
    utc_dt = datetime.datetime(2026, 9, 1, 17, 0, tzinfo=UTC_TZ)
    bkk_dt = to_bangkok_time(utc_dt)
    assert bkk_dt.hour == 0
    assert bkk_dt.day == 2
    assert bkk_dt.tzinfo == BANGKOK_TZ

def test_office_hours_bounds():
    target = datetime.date(2026, 9, 5)
    start_utc, end_utc = get_office_hours_bounds(target)
    # 08:00 ICT -> 01:00 UTC
    assert start_utc.hour == 1
    # 18:00 ICT -> 11:00 UTC
    assert end_utc.hour == 11
    assert (end_utc - start_utc).total_seconds() == 10 * 3600

def test_format_bangkok_iso():
    dt = datetime.datetime(2026, 9, 1, 12, 30, tzinfo=BANGKOK_TZ)
    iso_str = format_bangkok_iso(dt)
    assert "2026-09-01T12:30:00+07:00" in iso_str

@pytest.mark.asyncio
async def test_parse_bangkok_time_iso_formats():
    # Standard ISO with offset
    dt1 = await parse_bangkok_time("2026-09-01T08:00:00+07:00")
    assert dt1.hour == 1  # 08:00 ICT -> 01:00 UTC

    # UTC with Z
    dt2 = await parse_bangkok_time("2026-09-01T01:00:00Z")
    assert dt2.hour == 1
    assert dt2.day == 1

@pytest.mark.asyncio
async def test_parse_bangkok_time_regex_fallback():
    # LLM quirks like without T or messy spacing
    dt = await parse_bangkok_time("2026-09-05 14:30")
    # Assumes Bangkok time when unspecified -> 14:30 ICT = 07:30 UTC
    assert dt.hour == 7
    assert dt.minute == 30

@pytest.mark.asyncio
async def test_parse_bangkok_time_invalid_raises():
    with pytest.raises(ValueError, match="Unable to parse timestamp"):
        await parse_bangkok_time("not-a-valid-date-string")
