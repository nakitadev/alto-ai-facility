import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import logfire
from backend.config import BACKEND_HOST, BACKEND_PORT, LOGFIRE_TOKEN, LOGFIRE_SERVICE_NAME

# Initialize Logfire Distributed Observability
logfire.configure(
    service_name=LOGFIRE_SERVICE_NAME,
    token=LOGFIRE_TOKEN,
    send_to_logfire='if-token-present',
    console=logfire.ConsoleOptions(min_log_level='info')
)

from backend.database import (
    get_session,
    get_simulated_time_bounds,
    get_registered_machines
)
from backend.models import PendingAction
from sqlalchemy import select, update, func
from backend.agent.loop import run_agent_loop, stream_agent_loop, clear_session_history
from backend.agent.cost_ledger import get_ledger_summary

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ASGI Lifespan Startup: Non-blocking health check
    time_bounds = await get_simulated_time_bounds()
    print(f"[ASGI Server Ready] TimescaleDB connected. Telemetry days: {time_bounds.get('days_available', 0)}")
    logfire.info("ASGI Server Ready with Logfire tracing", days_available=time_bounds.get('days_available', 0))
    yield
    print("[ASGI Server Shutdown] Graceful termination complete.")

app = FastAPI(
    title="Somchai Commercial HVAC Energy Assistant API",
    description="Backend ASGI API powering grounded AI reasoning, tool calls, and safety controls over TimescaleDB.",
    version="1.1.0",
    lifespan=lifespan
)

# Instrument FastAPI and PydanticAI with Logfire
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()

# Enable CORS for local Streamlit / Frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "somchai_control_session"

class ResetChatRequest(BaseModel):
    conversation_id: str

class ApprovalRequest(BaseModel):
    reviewer_name: str = "Somchai Thanakit"
    notes: Optional[str] = "Authorized via Facility Operations Console."

@app.get("/api/health")
async def health_check():
    """ASGI Non-blocking health check verifying TimescaleDB connectivity."""
    time_bounds = await get_simulated_time_bounds()
    return {
        "status": "healthy",
        "service": "AltoTech Energy Assistant (ASGI)",
        "database": time_bounds
    }

@app.get("/api/machines")
async def list_machines():
    """Returns registered building equipment asynchronously."""
    machines = await get_registered_machines()
    return {"machines": machines}

@app.get("/api/time_bounds")
async def time_bounds():
    """Returns active dataset temporal bounds asynchronously."""
    return await get_simulated_time_bounds()

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Standard ASGI endpoint executing Dual-Process System 1 + System 2 agent loop.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    result = await run_agent_loop(
        user_prompt=request.message,
        conversation_id=request.conversation_id
    )
    return result

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Native ASGI Server-Sent Events (SSE) streaming endpoint.
    Emits token deltas in real-time as the LLM generates reasoning and tool calls.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    return StreamingResponse(
        stream_agent_loop(
            user_prompt=request.message,
            conversation_id=request.conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/chat/reset")
async def reset_chat_endpoint(request: ResetChatRequest):
    """
    Clears the in-memory multi-turn message history for a given conversation_id.
    """
    clear_session_history(request.conversation_id)
    return {"status": "cleared", "conversation_id": request.conversation_id}

@app.get("/api/pending_actions")
async def list_pending_actions():
    """
    Returns pending machine control proposals awaiting operator authorization (Problem 3 Option A) using SQLAlchemy.
    """
    stmt = select(PendingAction).order_by(PendingAction.proposed_at.desc()).limit(50)
    async with get_session() as session:
        result = await session.execute(stmt)
        actions = [a.to_dict() for a in result.scalars().all()]
        return {"pending_actions": actions}

@app.post("/api/pending_actions/{action_id}/approve")
async def approve_action(action_id: int, req: ApprovalRequest):
    """
    Approves a proposed action asynchronously using SQLAlchemy. Writes audit signature to database.
    """
    async with get_session() as session:
        action = await session.get(PendingAction, action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Proposal not found.")
        
        stmt = (
            update(PendingAction)
            .where(PendingAction.id == action_id)
            .values(
                status="APPROVED",
                reviewed_by=req.reviewer_name,
                reviewed_at=func.now(),
                execution_notes=req.notes
            )
        )
        await session.execute(stmt)
        await session.commit()
    return {"status": "SUCCESS", "message": f"Proposal #{action_id} approved by {req.reviewer_name}."}

@app.post("/api/pending_actions/{action_id}/reject")
async def reject_action(action_id: int, req: ApprovalRequest):
    """
    Rejects a proposed action asynchronously using SQLAlchemy.
    """
    async with get_session() as session:
        action = await session.get(PendingAction, action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Proposal not found.")
        
        stmt = (
            update(PendingAction)
            .where(PendingAction.id == action_id)
            .values(
                status="REJECTED",
                reviewed_by=req.reviewer_name,
                reviewed_at=func.now(),
                execution_notes=req.notes
            )
        )
        await session.execute(stmt)
        await session.commit()
    return {"status": "SUCCESS", "message": f"Proposal #{action_id} rejected by {req.reviewer_name}."}

@app.get("/api/ledger")
async def get_ledger():
    """
    Returns comprehensive usage and cost analytics for Somchai's boss asynchronously.
    """
    return await get_ledger_summary()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)

