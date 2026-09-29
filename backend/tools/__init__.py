from backend.tools.sql_tools import (
    query_data_coverage,
    query_energy_aggregates,
    query_sensor_readings,
    query_ai_decisions,
    propose_control_action
)
from backend.tools.doc_tools import search_docs

BUILDING_TOOLS = [
    query_data_coverage,
    query_energy_aggregates,
    query_sensor_readings,
    query_ai_decisions,
    search_docs,
    propose_control_action
]

TOOL_MAP = {
    "query_data_coverage": query_data_coverage,
    "query_energy_aggregates": query_energy_aggregates,
    "query_sensor_readings": query_sensor_readings,
    "query_ai_decisions": query_ai_decisions,
    "search_docs": search_docs,
    "propose_control_action": propose_control_action
}

__all__ = [
    "query_data_coverage",
    "query_energy_aggregates",
    "query_sensor_readings",
    "query_ai_decisions",
    "propose_control_action",
    "search_docs",
    "BUILDING_TOOLS",
    "TOOL_MAP"
]
