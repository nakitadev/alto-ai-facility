"""
Unit tests for backend/system1/guard.py.
Verifies fast sub-500ms safety guard tripwires:
- Unmonitored sensors (humidity)
- Out-of-scope date requests (month comparison with 7 days data)
- Write action requests (turn off equipment)
- Normal analytical queries
"""

import pytest
from backend.system1.guard import system1_guard, get_machine_registry

@pytest.mark.asyncio
async def test_get_machine_registry():
    names, aliases = await get_machine_registry()
    assert len(names) > 0
    assert "AC-L1" in names
    assert "AC-S5" in names
    assert "FAN-01" in names
    assert "server room" in aliases or "lobby" in aliases

@pytest.mark.asyncio
async def test_guard_tripwire_humidity_unmonitored():
    res = await system1_guard.analyze_query("What is the humidity in the server room right now?")
    assert res["guard_triggered"] is True
    assert res["intent"] == "UNANSWERABLE_NO_SENSOR"
    resp = res["immediate_response"].lower()
    assert "humidity" in resp
    assert "not equipped" in resp or "no humidity" in resp

@pytest.mark.asyncio
async def test_guard_tripwire_out_of_range():
    res = await system1_guard.analyze_query("How does this month's energy compare with last month?")
    assert res["guard_triggered"] is True
    assert res["intent"] == "TEMPORAL_OUT_OF_RANGE"
    resp = res["immediate_response"].lower()
    assert "cannot provide" in resp or "not available" in resp or "telemetry" in resp

@pytest.mark.asyncio
async def test_guard_tripwire_write_command():
    res = await system1_guard.analyze_query("Turn off AC-L2 now.")
    assert res["guard_triggered"] is True
    assert res["intent"] == "WRITE_ACTION_PROPOSED"
    resp = res["immediate_response"].lower()
    assert "cannot" in resp or "authorization" in resp
    assert "proposal" in resp or "pending" in resp

@pytest.mark.asyncio
async def test_guard_analytical_passes_through():
    res = await system1_guard.analyze_query("What was the building total energy on day 2?")
    # Analytical query should not trigger a blocking refusal tripwire
    assert res["guard_triggered"] is False
    assert "energy" in res["intent"].lower() or res["intent"] in ["ANALYTICAL", "DATA_QUERY"]
