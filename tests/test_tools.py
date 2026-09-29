"""
Unit tests for backend/tools/sql_tools.py and backend/tools/doc_tools.py.
Verifies bounded execution, parameter validations, and output structure.
"""

import pytest
from backend.tools import (
    BUILDING_TOOLS,
    TOOL_MAP,
    query_data_coverage,
    query_energy_aggregates,
    query_sensor_readings,
    query_ai_decisions,
    propose_control_action,
    search_docs
)

def test_building_tools_registry():
    assert len(BUILDING_TOOLS) >= 6
    assert "query_data_coverage" in TOOL_MAP
    assert "query_energy_aggregates" in TOOL_MAP
    assert "query_sensor_readings" in TOOL_MAP
    assert "query_ai_decisions" in TOOL_MAP
    assert "search_docs" in TOOL_MAP
    assert "propose_control_action" in TOOL_MAP

@pytest.mark.asyncio
async def test_query_data_coverage():
    res = await query_data_coverage()
    assert "has_data" in res
    assert "days_available" in res
    assert "monitored_metrics" in res
    assert "unmonitored_metrics" in res
    assert "humidity" in res["unmonitored_metrics"]
    assert res["days_available"] >= 1

@pytest.mark.asyncio
async def test_query_energy_aggregates_bounded():
    # Test day 1 total energy
    res = await query_energy_aggregates("Day 1 00:00", "Day 1 23:59")
    assert "total_energy_kwh" in res
    assert res["total_energy_kwh"] > 0
    assert "avg_power_kw" in res
    assert "samples_analyzed" in res

@pytest.mark.asyncio
async def test_query_sensor_readings_bounded():
    res = await query_sensor_readings("AC-L1", "Day 1 10:00", "Day 1 11:00")
    assert res["machine_name"] == "AC-L1"
    assert "avg_temperature_c" in res
    assert res["reading_count"] > 0

@pytest.mark.asyncio
async def test_search_docs_tool():
    res = await search_docs("comfort temperature")
    assert "results_found" in res
    assert res["results_found"] > 0
    assert "chunks" in res

@pytest.mark.asyncio
async def test_propose_control_action():
    res = await propose_control_action(
        machine_name="AC-S2",
        proposed_action="SET TEMP",
        reasoning="Test proposal for office comfort adjustment",
        parameter_value="25°C"
    )
    assert res["status"] in ["PENDING_CONFIRMATION", "PROPOSED"]
    assert "proposal_id" in res
    assert res["proposal_id"] is not None

@pytest.mark.asyncio
async def test_query_ai_decisions():
    res = await query_ai_decisions("Day 4 00:00", "Day 7 23:59", machine_name="AC-S3")
    assert "decision_count" in res
    assert "decisions" in res
    assert isinstance(res["decisions"], list)
