"""
Asynchronous Database Layer for AltoTech AI Engineer Assessment.
Powered purely by SQLAlchemy 2.0 AsyncEngine and asyncpg.
Zero synchronous blocking drivers or legacy shims.
"""

from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.config import DATABASE_URL, DEFAULT_TIMEZONE
from backend.models import Machine, SensorReading

BANGKOK_TZ = ZoneInfo(DEFAULT_TIMEZONE)
UTC_TZ = ZoneInfo("UTC")

def _format_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

DB_URL = _format_db_url(DATABASE_URL)

# SQLAlchemy Async Engine with Connection Pooling
engine = create_async_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session Factory
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional asynchronous SQLAlchemy session context."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

# ---------------------------------------------------------
# Native SQLAlchemy Query Execution Helpers
# ---------------------------------------------------------
async def fetch_all(stmt) -> List[Dict[str, Any]]:
    """Executes a SQLAlchemy select statement and returns rows as dictionaries."""
    async with get_session() as session:
        result = await session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

async def fetch_one(stmt) -> Optional[Dict[str, Any]]:
    """Executes a SQLAlchemy select statement and returns a single row dictionary."""
    async with get_session() as session:
        result = await session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

async def execute_stmt(stmt, commit: bool = True) -> Any:
    """Executes an insert/update/delete statement."""
    async with get_session() as session:
        result = await session.execute(stmt)
        if commit:
            await session.commit()
        return result

# ---------------------------------------------------------
# Dynamic Operational Bounds & Machine Registry
# ---------------------------------------------------------
async def get_simulated_time_bounds() -> Dict[str, Any]:
    """
    Asynchronously inspects TimescaleDB using SQLAlchemy to dynamically find
    the operational boundaries and facility current time in Bangkok time (UTC+7).
    """
    try:
        stmt = select(
            func.min(SensorReading.time).label("min_time"),
            func.max(SensorReading.time).label("max_time")
        )
        row = await fetch_one(stmt)
        if not row or not row.get("min_time"):
            return {
                "has_data": False,
                "error": "No sensor readings found in database.",
                "min_bkk": "N/A",
                "max_bkk": "N/A",
                "simulated_now_bkk": "N/A",
                "current_time_bkk": "N/A",
                "days_available": 0
            }
        
        min_bkk = row["min_time"].astimezone(BANGKOK_TZ)
        max_bkk = row["max_time"].astimezone(BANGKOK_TZ)
        time_str = max_bkk.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        return {
            "has_data": True,
            "min_utc": row["min_time"].isoformat(),
            "max_utc": row["max_time"].isoformat(),
            "min_bkk": min_bkk.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "max_bkk": max_bkk.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "simulated_now_bkk": time_str,
            "current_time_bkk": time_str,
            "days_available": (max_bkk.date() - min_bkk.date()).days + 1
        }
    except Exception as e:
        return {
            "has_data": False,
            "error": str(e),
            "min_bkk": "N/A",
            "max_bkk": "N/A",
            "simulated_now_bkk": "N/A",
            "current_time_bkk": "N/A",
            "days_available": 0
        }

async def get_registered_machines() -> List[Dict[str, Any]]:
    """Asynchronously queries registered machines using SQLAlchemy."""
    stmt = select(Machine).order_by(Machine.machine_name)
    async with get_session() as session:
        result = await session.execute(stmt)
        machines = result.scalars().all()
        return [m.to_dict() for m in machines]
