import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BACKEND_HOST, BACKEND_PORT
from backend.database import (
    get_simulated_time_bounds,
    get_registered_machines,
    query_db,
    execute_insert
)
from backend.agent.loop import run_agent_loop
from backend.agent.cost_ledger import get_ledger_summary

app = FastAPI(
    title="Somchai Commercial HVAC Energy Assistant API",
    description="Backend API powering grounded AI reasoning, tool calls, and safety controls over TimescaleDB.",
    version="1.0.0"
)

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

class ApprovalRequest(BaseModel):
    reviewer_name: str = "Somchai Thanakit"
    notes: Optional[str] = "Authorized via Facility Operations Console."

@app.get("/api/health")
def health_check():
    time_bounds = get_simulated_time_bounds()
    return {
        "status": "healthy",
        "service": "AltoTech Energy Assistant",
        "database": time_bounds
    }

@app.get("/api/machines")
def list_machines():
    return {"machines": get_registered_machines()}

@app.get("/api/time_bounds")
def time_bounds():
    return get_simulated_time_bounds()

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    result = run_agent_loop(
        user_prompt=request.message,
        conversation_id=request.conversation_id
    )
    return result

@app.get("/api/pending_actions")
def list_pending_actions():
    """
    Returns pending machine control proposals awaiting operator authorization (Problem 3 Option A).
    """
    actions = query_db("""
        SELECT id, proposed_at, machine_name, proposed_action, parameter_value, reasoning, status, reviewed_by, reviewed_at
        FROM pending_actions
        ORDER BY proposed_at DESC
        LIMIT 50;
    """)
    return {"pending_actions": [dict(a) for a in actions]}

@app.post("/api/pending_actions/{action_id}/approve")
def approve_action(action_id: int, req: ApprovalRequest):
    """
    Approves a proposed action. Writes audit signature to database.
    """
    action = query_db("SELECT id, status FROM pending_actions WHERE id = %s", (action_id,), fetchone=True)
    if not action:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    
    execute_insert(
        """
        UPDATE pending_actions 
        SET status = 'APPROVED', reviewed_by = %s, reviewed_at = NOW(), execution_notes = %s
        WHERE id = %s;
        """,
        (req.reviewer_name, req.notes, action_id)
    )
    return {"status": "SUCCESS", "message": f"Proposal #{action_id} approved by {req.reviewer_name}."}

@app.post("/api/pending_actions/{action_id}/reject")
def reject_action(action_id: int, req: ApprovalRequest):
    """
    Rejects a proposed action.
    """
    action = query_db("SELECT id, status FROM pending_actions WHERE id = %s", (action_id,), fetchone=True)
    if not action:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    
    execute_insert(
        """
        UPDATE pending_actions 
        SET status = 'REJECTED', reviewed_by = %s, reviewed_at = NOW(), execution_notes = %s
        WHERE id = %s;
        """,
        (req.reviewer_name, req.notes, action_id)
    )
    return {"status": "SUCCESS", "message": f"Proposal #{action_id} rejected by {req.reviewer_name}."}

@app.get("/api/ledger")
def get_ledger():
    """
    Returns comprehensive usage and cost analytics for Somchai's boss.
    """
    return get_ledger_summary()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
