"""
Asynchronous LLM Cost & Token Usage Ledger.
Powered by SQLAlchemy 2.0 AsyncSession.
"""

import json
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy import select, func, insert
from backend.database import get_async_session
from backend.models import LLMCostLedger

# Estimated pricing per 1M tokens (USD)
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

async def record_llm_call_async(
    conversation_id: str,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    intent_detected: str = "ANALYTICAL",
    tools_called: List[str] = None
) -> int:
    """Non-blocking async cost ledger write using SQLAlchemy AsyncSession."""
    cost = calculate_cost(model_name, tokens_in, tokens_out)
    tools_str = json.dumps(tools_called or [])
    
    try:
        stmt = insert(LLMCostLedger).values(
            conversation_id=conversation_id,
            model_name=model_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=cost,
            latency_ms=latency_ms,
            intent_detected=intent_detected,
            tools_called=tools_str
        ).returning(LLMCostLedger.id)
        async with get_async_session() as session:
            result = await session.execute(stmt)
            call_id = result.scalar()
            await session.commit()
            return call_id or 0
    except Exception as e:
        print(f"Warning: Failed to record cost ledger: {e}")
        return 0

async def get_ledger_summary_async() -> Dict[str, Any]:
    """Non-blocking async cost ledger summary query using SQLAlchemy AsyncSession."""
    try:
        stmt_sum = select(
            func.count().label("total_calls"),
            func.coalesce(func.sum(LLMCostLedger.tokens_in), 0).label("total_tokens_in"),
            func.coalesce(func.sum(LLMCostLedger.tokens_out), 0).label("total_tokens_out"),
            func.coalesce(func.sum(LLMCostLedger.estimated_cost_usd), 0.0).label("total_cost_usd"),
            func.coalesce(func.avg(LLMCostLedger.latency_ms), 0.0).label("avg_latency_ms")
        )
        stmt_recent = select(LLMCostLedger).order_by(LLMCostLedger.timestamp.desc()).limit(20)

        async with get_async_session() as session:
            totals = (await session.execute(stmt_sum)).mappings().first()
            recent_res = await session.execute(stmt_recent)
            recent_calls = [m.to_dict() for m in recent_res.scalars().all()]

            tot_calls = int(totals["total_calls"]) if totals else 0
            tot_cost = float(totals["total_cost_usd"]) if totals else 0.0

            return {
                "summary": {
                    "total_calls": tot_calls,
                    "total_tokens_in": int(totals["total_tokens_in"]) if totals else 0,
                    "total_tokens_out": int(totals["total_tokens_out"]) if totals else 0,
                    "total_cost_usd": tot_cost,
                    "avg_latency_ms": round(float(totals["avg_latency_ms"]), 2) if totals else 0.0,
                    "projected_monthly_cost_usd": round(
                        (tot_cost / max(1, tot_calls)) * 1500, 2
                    )
                },
                "recent_calls": recent_calls
            }
    except Exception as e:
        return {"error": str(e), "summary": {"total_calls": 0, "total_cost_usd": 0.0}}
