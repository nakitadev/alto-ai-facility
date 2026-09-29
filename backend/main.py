from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, func

import logfire
from backend.config import BACKEND_HOST, BACKEND_PORT, OPENROUTER_MODEL, FREE_OPENROUTER_MODELS
from backend.schemas import ChatRequest, ResetChatRequest, ApprovalRequest, ModelsResponse
from backend.database import (
    get_session,
    get_simulated_time_bounds,
    get_registered_machines
)
from backend.models import PendingAction
from backend.agent.core import FacilityAIClient
from backend.agent.sse_handler import SSEHandler
from backend.agent.cost_ledger import get_ledger_summary

def get_ai_client(request: Request) -> FacilityAIClient:
    """Dependency provider yielding the application-scoped FacilityAIClient instance."""
    return request.app.state.ai_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ASGI Lifespan Startup: Non-blocking health check & AI client connection pool initialization
    time_bounds = await get_simulated_time_bounds()
    ai_client = FacilityAIClient()
    await ai_client.start()
    app.state.ai_client = ai_client
    print(f"[ASGI Server Ready] TimescaleDB connected. Telemetry days: {time_bounds.get('days_available', 0)}")
    logfire.info("ASGI Server Ready with Logfire tracing", days_available=time_bounds.get('days_available', 0))
    yield
    await ai_client.close()
    print("[ASGI Server Shutdown] Graceful termination complete. AI client connection pool closed.")

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

@app.get("/api/models", response_model=ModelsResponse)
async def list_models():
    """Returns verified free OpenRouter models available for dynamic selection."""
    return {
        "models": FREE_OPENROUTER_MODELS,
        "default": OPENROUTER_MODEL
    }

@app.post("/api/chat")
@app.post("/api/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    client: FacilityAIClient = Depends(get_ai_client)
):
    """
    ASGI Server-Sent Events (SSE) streaming endpoint via FacilityAIClient.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    return StreamingResponse(
        client.chat_stream(
            user_prompt=request.message,
            conversation_id=request.conversation_id,
            model=request.model
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat/reset")
async def reset_chat_endpoint(
    request: ResetChatRequest,
    client: FacilityAIClient = Depends(get_ai_client)
):
    """
    Clears the in-memory multi-turn message history for a given conversation_id.
    """
    client.clear_session_history(request.conversation_id)
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

