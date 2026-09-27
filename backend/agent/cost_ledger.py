import json
from typing import Dict, Any, List
from backend.database import query_db, execute_insert

# Estimated pricing per 1M tokens (USD)
# For OpenRouter free tier or standard models
MODEL_PRICING = {
    "nvidia/nemotron-3-ultra:free": {"input": 0.0, "output": 0.0},
    "google/gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-3.5-haiku": {"input": 0.80, "output": 4.00},
    "default": {"input": 0.20, "output": 0.80}
}

def calculate_cost(model_name: str, tokens_in: int, tokens_out: int) -> float:
    """
    Dynamically computes cost. Automatically identifies free-tier endpoints,
    System 1 micro-judgments, and matching commercial model families.
    """
    m_lower = model_name.lower()
    if ":free" in m_lower or "free" in m_lower or "local" in m_lower or "calibrated" in m_lower:
        return 0.0
    if "typesafe" in m_lower or "jev" in m_lower:
        return 0.00005

    pricing = MODEL_PRICING.get(model_name)
    if not pricing:
        for k, v in MODEL_PRICING.items():
            if k in model_name:
                pricing = v
                break
    pricing = pricing or MODEL_PRICING["default"]
    cost = (tokens_in / 1_000_000.0 * pricing["input"]) + (tokens_out / 1_000_000.0 * pricing["output"])
    return round(cost, 6)

def record_llm_call(
    conversation_id: str,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    intent_detected: str = "ANALYTICAL",
    tools_called: List[str] = None
) -> int:
    cost = calculate_cost(model_name, tokens_in, tokens_out)
    tools_str = json.dumps(tools_called or [])
    
    try:
        call_id = execute_insert(
            """
            INSERT INTO llm_cost_ledger (conversation_id, model_name, tokens_in, tokens_out, estimated_cost_usd, latency_ms, intent_detected, tools_called)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (conversation_id, model_name, tokens_in, tokens_out, cost, latency_ms, intent_detected, tools_str)
        )
        return call_id
    except Exception as e:
        print(f"Warning: Failed to record cost ledger: {e}")
        return 0

def get_ledger_summary() -> Dict[str, Any]:
    try:
        totals = query_db("""
            SELECT 
                COUNT(*) as total_calls,
                COALESCE(SUM(tokens_in), 0) as total_tokens_in,
                COALESCE(SUM(tokens_out), 0) as total_tokens_out,
                COALESCE(SUM(estimated_cost_usd), 0.0) as total_cost_usd,
                COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms
            FROM llm_cost_ledger;
        """, fetchone=True)

        recent_calls = query_db("""
            SELECT id, timestamp, conversation_id, model_name, tokens_in, tokens_out, estimated_cost_usd, latency_ms, intent_detected, tools_called
            FROM llm_cost_ledger
            ORDER BY timestamp DESC
            LIMIT 20;
        """)

        return {
            "summary": {
                "total_calls": int(totals["total_calls"]),
                "total_tokens_in": int(totals["total_tokens_in"]),
                "total_tokens_out": int(totals["total_tokens_out"]),
                "total_cost_usd": float(totals["total_cost_usd"]),
                "avg_latency_ms": round(float(totals["avg_latency_ms"]), 2),
                # Projected monthly cost based on 50 questions/day (1,500/month)
                "projected_monthly_cost_usd": round(
                    (float(totals["total_cost_usd"]) / max(1, int(totals["total_calls"]))) * 1500, 2
                )
            },
            "recent_calls": [dict(r) for r in recent_calls]
        }
    except Exception as e:
        return {"error": str(e), "summary": {"total_calls": 0, "total_cost_usd": 0.0}}

import asyncio

async def record_llm_call_async(
    conversation_id: str,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    intent_detected: str = "ANALYTICAL",
    tools_called: List[str] = None
) -> int:
    """Non-blocking async cost ledger write for ASGI applications."""
    return await asyncio.to_thread(
        record_llm_call,
        conversation_id,
        model_name,
        tokens_in,
        tokens_out,
        latency_ms,
        intent_detected,
        tools_called
    )

async def get_ledger_summary_async() -> Dict[str, Any]:
    """Non-blocking async cost ledger summary query for ASGI endpoints."""
    return await asyncio.to_thread(get_ledger_summary)

