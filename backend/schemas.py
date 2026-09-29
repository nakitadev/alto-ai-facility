"""
Pydantic v2 schemas defining clean contracts for API requests/responses,
tool arguments, and telemetry data transfer objects (DTOs).
Decouples external data exchange from internal SQLAlchemy ORM entities.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# 1. API Contracts
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    """Input payload for user chat requests."""
    message: str = Field(..., min_length=1, description="Operator user query or command")
    conversation_id: Optional[str] = Field("somchai_control_session", description="Session identifier for multi-turn history tracking")
    model: Optional[str] = Field(None, description="OpenRouter free model identifier")

class ModelOptionDTO(BaseModel):
    """Available OpenRouter free model specification."""
    id: str
    name: str
    context_length: str
    supports_tools: bool = True

class ModelsResponse(BaseModel):
    """List of available free OpenRouter models and default selection."""
    models: List[ModelOptionDTO]
    default: str

class ResetChatRequest(BaseModel):
    """Payload to reset a conversation history."""
    conversation_id: str

class ApprovalRequest(BaseModel):
    """Payload to approve a pending control action."""
    reviewer_name: str = Field("Somchai Thanakit", description="Operator name")
    notes: Optional[str] = Field("Authorized via Facility Operations Console.", description="Reviewer notes")

class ChatResponse(BaseModel):
    """Complete response payload for non-streaming /api/chat endpoint."""
    response: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    system1_latency_ms: Optional[float] = None
    guard_tripwire: Optional[str] = None
    system_one_provider: Optional[str] = None
    framework: str = "PydanticAI"

class ActionApprovalRequest(BaseModel):
    """Operator approval/rejection payload for pending control actions."""
    action_id: int = Field(..., ge=1, description="ID of the pending action")
    approved: bool = Field(..., description="True to approve, False to reject")
    reviewer: str = Field("Operator Somchai", description="Name of the authorizing operator")
    notes: Optional[str] = Field(None, description="Optional audit notes or rationale")

class ActionApprovalResponse(BaseModel):
    """Response returned upon reviewing a pending action."""
    status: str
    action_id: int
    review_status: Literal["APPROVED", "REJECTED"]
    reviewed_at: str

# ---------------------------------------------------------
# 2. Tool Input & Output Contracts (Bounded Tool Contracts)
# ---------------------------------------------------------

class EnergyAggregateInput(BaseModel):
    start_time: str = Field(..., description="Start of window (e.g. 'Day 2 00:00' or ISO timestamp)")
    end_time: str = Field(..., description="End of window (e.g. 'Day 2 23:59' or ISO timestamp)")
    machine_name: Optional[str] = Field(None, description="Specific machine or None for building total")
    group_by: Literal["total", "day", "machine"] = Field("total", description="Aggregation granularity")

class EnergyAggregateOutput(BaseModel):
    start_time: str
    end_time: str
    machine_name: Optional[str] = None
    total_kwh: float
    daily_avg_kwh: Optional[float] = None
    group_by: str
    series: List[Dict[str, Any]] = Field(default_factory=list)

class SensorReadingInput(BaseModel):
    start_time: str
    end_time: str
    machine_name: str
    metric: Literal["power", "temperature", "setpoint", "speed", "ANY"] = Field("ANY")
    limit: int = Field(20, ge=1, le=50)

class SensorReadingOutput(BaseModel):
    machine_name: str
    period: str
    record_count: int
    summary: Dict[str, Any]
    readings: List[Dict[str, Any]]

class AIDecisionInput(BaseModel):
    start_time: str
    end_time: str
    machine_name: Optional[str] = None
    limit: int = Field(20, ge=1, le=50)

class AIDecisionOutput(BaseModel):
    period: str
    decision_count: int
    decisions: List[Dict[str, Any]]

class ProposeActionInput(BaseModel):
    machine_name: str
    proposed_action: str
    reasoning: str
    parameter_value: str = "N/A"

class ProposeActionOutput(BaseModel):
    status: Literal["PROPOSED", "ERROR"]
    pending_action_id: Optional[int] = None
    message: str
    action_details: Optional[Dict[str, Any]] = None

class DocSearchInput(BaseModel):
    query: str
    document_filter: str = "all"

class DocSearchOutput(BaseModel):
    query: str
    results_found: int
    chunks: List[Dict[str, Any]]

class DataCoverageOutput(BaseModel):
    has_data: bool
    days_available: int
    min_bkk: str
    max_bkk: str
    current_time_bkk: str
    monitored_metrics: List[str]
    machine_count: int
    machines: List[str]

# ---------------------------------------------------------
# 3. Telemetry DTOs
# ---------------------------------------------------------

class MachineDTO(BaseModel):
    machine_name: str
    machine_type: str
    zone: str
    floor: Optional[str] = None
    rated_power_kw: float
    is_critical_24_7: bool
    description: Optional[str] = None

class PendingActionDTO(BaseModel):
    id: int
    proposed_at: str
    machine_name: str
    proposed_action: str
    parameter_value: Optional[str] = None
    reasoning: str
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    execution_notes: Optional[str] = None
