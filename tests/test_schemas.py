"""
Unit tests for backend/schemas.py.
Verifies Pydantic v2 contract constraints, validation errors, and defaults.
"""

import pytest
from pydantic import ValidationError
from backend.schemas import (
    ChatRequest,
    ChatResponse,
    EnergyAggregateInput,
    SensorReadingInput,
    AIDecisionInput,
    ProposeActionInput,
    ActionApprovalRequest,
    ModelOptionDTO,
    ModelsResponse
)

def test_chat_request_valid():
    req = ChatRequest(message="What is the energy consumption?", model="nvidia/nemotron-3.5-lightning:free")
    assert req.message == "What is the energy consumption?"
    assert req.conversation_id == "somchai_control_session"
    assert req.model == "nvidia/nemotron-3.5-lightning:free"

def test_models_response():
    resp = ModelsResponse(
        models=[
            ModelOptionDTO(
                id="inclusionai/ling-3.0-flash-sante:free",
                name="Ling 3.0 Flash",
                context_length="256k"
            )
        ],
        default="inclusionai/ling-3.0-flash-sante:free"
    )
    assert len(resp.models) == 1
    assert resp.models[0].supports_tools is True
    assert resp.default == "inclusionai/ling-3.0-flash-sante:free"

def test_chat_request_empty_invalid():
    with pytest.raises(ValidationError):
        ChatRequest(message="")

def test_sensor_reading_input_limit_bounds():
    # Limit must be between 1 and 50
    valid = SensorReadingInput(
        start_time="Day 1 00:00",
        end_time="Day 1 12:00",
        machine_name="AC-L1",
        limit=20
    )
    assert valid.limit == 20

    with pytest.raises(ValidationError):
        SensorReadingInput(
            start_time="Day 1 00:00",
            end_time="Day 1 12:00",
            machine_name="AC-L1",
            limit=100  # Exceeds max 50
        )

def test_propose_action_input():
    action = ProposeActionInput(
        machine_name="AC-L1",
        proposed_action="TURN OFF",
        reasoning="Night mode shutdown"
    )
    assert action.machine_name == "AC-L1"
    assert action.parameter_value == "N/A"

def test_chat_response():
    resp = ChatResponse(
        response="Total energy is 1200 kWh.",
        tokens_in=100,
        tokens_out=50,
        latency_ms=350.0
    )
    assert resp.response == "Total energy is 1200 kWh."
    assert resp.framework == "PydanticAI"
    assert resp.tokens_in == 100

def test_energy_aggregate_input():
    valid = EnergyAggregateInput(
        start_time="Day 1 00:00",
        end_time="Day 1 23:59",
        group_by="day"
    )
    assert valid.group_by == "day"

    with pytest.raises(ValidationError):
        EnergyAggregateInput(
            start_time="Day 1 00:00",
            end_time="Day 1 23:59",
            group_by="invalid_group"
        )

def test_ai_decision_input():
    valid = AIDecisionInput(
        start_time="Day 4 00:00",
        end_time="Day 7 23:59",
        limit=30
    )
    assert valid.limit == 30

    with pytest.raises(ValidationError):
        AIDecisionInput(
            start_time="Day 4 00:00",
            end_time="Day 7 23:59",
            limit=200  # Exceeds max 50
        )

def test_action_approval_request():
    appr = ActionApprovalRequest(
        action_id=1,
        approved=True,
        reviewer="Somchai Thanakit"
    )
    assert appr.action_id == 1
    assert appr.approved is True
