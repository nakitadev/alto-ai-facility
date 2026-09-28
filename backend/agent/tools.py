import datetime
import time
import re
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, List
from backend.database import get_session
from backend.models import Machine, SensorReading, AIDecision, PendingAction
from sqlalchemy import select, func, cast, Date, Numeric, insert
from backend.rag.retriever import retriever
from backend.config import DEFAULT_TIMEZONE

BANGKOK_TZ = ZoneInfo(DEFAULT_TIMEZONE)
UTC_TZ = ZoneInfo("UTC")

_BASE_DATE_CACHE = None
_CACHE_TIME = 0.0

async def get_base_date() -> Optional[datetime.date]:
    """
    Dynamically anchors Day 1 to the actual earliest sensor reading in TimescaleDB.
    Enables arbitrary multi-week, monthly, or historical datasets without hardcoding.
    Refreshes cache periodically or upon database re-seeding.
    """
    global _BASE_DATE_CACHE, _CACHE_TIME
    now = time.time()
    if _BASE_DATE_CACHE and (now - _CACHE_TIME < 60.0):
        return _BASE_DATE_CACHE
    try:
        from backend.database import get_simulated_time_bounds
        bounds = await get_simulated_time_bounds()
        if bounds.get("has_data") and "min_bkk" in bounds and bounds["min_bkk"] != "N/A":
            date_str = bounds["min_bkk"].split(" ")[0]
            _BASE_DATE_CACHE = datetime.date.fromisoformat(date_str)
            _CACHE_TIME = now
            return _BASE_DATE_CACHE
    except Exception:
        pass
    return None

async def parse_bangkok_time(time_str: str) -> datetime.datetime:
    """
    Parses various date/time formats asynchronously and returns a UTC datetime.
    Supports:
      - 'Day N HH:MM' offsets from earliest database record
      - ISO-8601 formats and YYYY-MM-DD HH:MM:SS
    """
    time_str = time_str.strip()

    # Check for "Day N HH:MM" (derived from actual DB start)
    m_day = re.match(r"(?i)day\s*(\d+)(?:\s+(\d{1,2}):(\d{2}))?", time_str)
    if m_day:
        day_num = int(m_day.group(1))
        hour = int(m_day.group(2)) if m_day.group(2) else 0
        minute = int(m_day.group(3)) if m_day.group(3) else 0
        base_date = await get_base_date()
        if base_date:
            target_date = base_date + datetime.timedelta(days=day_num - 1)
            bkk_dt = datetime.datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=BANGKOK_TZ)
            return bkk_dt.astimezone(UTC_TZ)

    # Try standard ISO or standard format
    clean_str = time_str.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BANGKOK_TZ)
        return dt.astimezone(UTC_TZ)
    except Exception:
        # Fallback parsing YYYY-MM-DD HH:MM:SS
        parts = clean_str.split(" ")
        date_parts = [int(p) for p in parts[0].split("-")]
        hour, minute, second = 0, 0, 0
        if len(parts) > 1:
            time_parts = [int(p) for p in parts[1].split(":")]
            hour = time_parts[0]
            minute = time_parts[1]
            if len(time_parts) > 2:
                second = time_parts[2]
        bkk_dt = datetime.datetime(date_parts[0], date_parts[1], date_parts[2], hour, minute, second, tzinfo=BANGKOK_TZ)
        return bkk_dt.astimezone(UTC_TZ)

# Tool 1: Energy Aggregates (Async with SQLAlchemy)
async def query_energy_aggregates(start_time: str, end_time: str, machine_name: Optional[str] = None, group_by: str = "total") -> Dict[str, Any]:
    """
    Calculates deterministic electrical energy in kWh = SUM(power_kw * 5/60).
    Aggregates by total, by day, or by machine in Bangkok time using SQLAlchemy expressions.
    """
    start_utc = await parse_bangkok_time(start_time)
    end_utc = await parse_bangkok_time(end_time)

    kwh_expr = func.round(cast(func.sum(SensorReading.power_kw * 5.0 / 60.0), Numeric), 2)
    avg_power_expr = func.round(cast(func.avg(SensorReading.power_kw), Numeric), 2)
    peak_power_expr = func.round(cast(func.max(SensorReading.power_kw), Numeric), 2)

    async with get_session() as session:
        if group_by == "machine":
            stmt = (
                select(
                    SensorReading.machine_name,
                    kwh_expr.label("total_kwh"),
                    avg_power_expr.label("avg_power_kw"),
                    peak_power_expr.label("peak_power_kw"),
                    func.count().label("reading_count")
                )
                .where(SensorReading.time >= start_utc, SensorReading.time <= end_utc)
            )
            if machine_name:
                stmt = stmt.where(SensorReading.machine_name == machine_name)

            stmt = stmt.group_by(SensorReading.machine_name).order_by(kwh_expr.desc()).limit(50)
            result = await session.execute(stmt)
            rows = [dict(r) for r in result.mappings().all()]

            top_machine = rows[0]["machine_name"] if rows else None
            top_kwh = float(rows[0]["total_kwh"]) if rows else 0.0
            return {
                "period": f"{start_time} to {end_time}",
                "group_by": "machine",
                "top_consumer": {"machine_name": top_machine, "energy_kwh": top_kwh},
                "machines": [{
                    "machine_name": r["machine_name"],
                    "total_kwh": float(r["total_kwh"]) if r["total_kwh"] is not None else 0.0,
                    "avg_power_kw": float(r["avg_power_kw"]) if r["avg_power_kw"] is not None else 0.0,
                    "peak_power_kw": float(r["peak_power_kw"]) if r["peak_power_kw"] is not None else 0.0,
                    "reading_count": int(r["reading_count"])
                } for r in rows]
            }

        elif group_by == "day":
            bkk_date_col = cast(func.timezone("Asia/Bangkok", SensorReading.time), Date).label("bangkok_date")
            stmt = (
                select(
                    bkk_date_col,
                    kwh_expr.label("total_kwh"),
                    func.count(func.distinct(SensorReading.machine_name)).label("active_machines")
                )
                .where(SensorReading.time >= start_utc, SensorReading.time <= end_utc)
            )
            if machine_name:
                stmt = stmt.where(SensorReading.machine_name == machine_name)

            stmt = stmt.group_by(bkk_date_col).order_by(bkk_date_col.asc()).limit(30)
            result = await session.execute(stmt)
            rows = [dict(r) for r in result.mappings().all()]
            base_date = await get_base_date()
            return {
                "period": f"{start_time} to {end_time}",
                "group_by": "day",
                "daily_kwh": [{
                    "date": str(r["bangkok_date"]),
                    "kwh": float(r["total_kwh"]) if r["total_kwh"] is not None else 0.0,
                    "day_number": (r["bangkok_date"] - base_date).days + 1 if base_date else None
                } for r in rows]
            }

        else: # Total aggregate
            stmt = (
                select(
                    kwh_expr.label("total_kwh"),
                    avg_power_expr.label("avg_power_kw"),
                    peak_power_expr.label("max_power_kw"),
                    func.count().label("total_samples")
                )
                .where(SensorReading.time >= start_utc, SensorReading.time <= end_utc)
            )
            if machine_name:
                stmt = stmt.where(SensorReading.machine_name == machine_name)

            result = await session.execute(stmt)
            row = result.mappings().first()
            return {
                "start_time_bkk": start_time,
                "end_time_bkk": end_time,
                "machine_filter": machine_name or "ALL",
                "total_energy_kwh": float(row["total_kwh"]) if row and row["total_kwh"] is not None else 0.0,
                "avg_power_kw": float(row["avg_power_kw"]) if row and row["avg_power_kw"] is not None else 0.0,
                "samples_analyzed": int(row["total_samples"]) if row else 0
            }

# Tool 2: Sensor Readings Statistics (Async with SQLAlchemy)
async def query_sensor_readings(machine_name: str, start_time: str, end_time: str, metric: str = "temperature", aggregate: str = "avg") -> Dict[str, Any]:
    """
    Queries sensor readings (temperature, power, setpoint, speed) for a machine.
    Returns statistical aggregates via SQLAlchemy to keep token budget bounded.
    """
    start_utc = await parse_bangkok_time(start_time)
    end_utc = await parse_bangkok_time(end_time)

    stmt = (
        select(
            SensorReading.machine_name,
            func.round(cast(func.avg(SensorReading.temperature), Numeric), 2).label("avg_temperature_c"),
            func.round(cast(func.min(SensorReading.temperature), Numeric), 2).label("min_temperature_c"),
            func.round(cast(func.max(SensorReading.temperature), Numeric), 2).label("max_temperature_c"),
            func.round(cast(func.avg(SensorReading.setpoint), Numeric), 2).label("avg_setpoint_c"),
            func.round(cast(func.avg(SensorReading.power_kw), Numeric), 2).label("avg_power_kw"),
            func.round(cast(func.avg(SensorReading.speed), Numeric), 2).label("avg_speed_pct"),
            func.count().label("reading_count")
        )
        .where(SensorReading.machine_name == machine_name)
        .where(SensorReading.time >= start_utc, SensorReading.time <= end_utc)
        .group_by(SensorReading.machine_name)
    )
    async with get_session() as session:
        result = await session.execute(stmt)
        row = result.mappings().first()
        if not row or row["reading_count"] == 0:
            return {
                "machine_name": machine_name,
                "message": f"No sensor records found for {machine_name} in requested interval."
            }

        return {
            "machine_name": machine_name,
            "period": f"{start_time} to {end_time}",
            "avg_temperature_c": float(row["avg_temperature_c"]) if row["avg_temperature_c"] is not None else None,
            "min_temperature_c": float(row["min_temperature_c"]) if row["min_temperature_c"] is not None else None,
            "max_temperature_c": float(row["max_temperature_c"]) if row["max_temperature_c"] is not None else None,
            "avg_setpoint_c": float(row["avg_setpoint_c"]) if row["avg_setpoint_c"] is not None else None,
            "avg_power_kw": float(row["avg_power_kw"]) if row["avg_power_kw"] is not None else 0.0,
            "reading_count": int(row["reading_count"])
        }

# Tool 3: AI Decisions Log (Async with SQLAlchemy)
async def query_ai_decisions(start_time: str, end_time: str, machine_name: Optional[str] = None, action: str = "ANY", limit: int = 20) -> Dict[str, Any]:
    """
    Queries logged actions taken by the building AI in Days 4–7 using SQLAlchemy.
    """
    start_utc = await parse_bangkok_time(start_time)
    end_utc = await parse_bangkok_time(end_time)

    bkk_time_col = func.timezone("Asia/Bangkok", AIDecision.timestamp).label("time_bkk")
    stmt = (
        select(
            AIDecision.id,
            bkk_time_col,
            AIDecision.machine_name,
            AIDecision.action,
            AIDecision.parameter_value,
            AIDecision.reason
        )
        .where(AIDecision.timestamp >= start_utc, AIDecision.timestamp <= end_utc)
    )
    if machine_name:
        stmt = stmt.where(AIDecision.machine_name == machine_name)
    if action != "ANY":
        stmt = stmt.where(AIDecision.action == action)

    stmt = stmt.order_by(AIDecision.timestamp.asc()).limit(min(limit, 50))

    async with get_session() as session:
        result = await session.execute(stmt)
        rows = [dict(r) for r in result.mappings().all()]
        decisions = []
        for r in rows:
            decisions.append({
                "time_bangkok": str(r["time_bkk"]),
                "machine_name": r["machine_name"],
                "action": r["action"],
                "parameter": r["parameter_value"],
                "reason": r["reason"]
            })

        return {
            "period": f"{start_time} to {end_time}",
            "decision_count": len(decisions),
            "decisions": decisions
        }

# Tool 4: Search Documents (Async)
async def search_docs(query: str, document_filter: str = "all") -> Dict[str, Any]:
    """
    Retrieves policy rules, schedules, comfort bands, and maintenance notes from docs/.
    """
    chunks = retriever.search(query=query, doc_filter=document_filter, top_k=3)
    return {
        "query": query,
        "results_found": len(chunks),
        "chunks": chunks
    }

# Tool 5: Propose Action (Problem 3 Option A - Async with SQLAlchemy)
async def propose_control_action(machine_name: str, proposed_action: str, reasoning: str, parameter_value: str = "N/A") -> Dict[str, Any]:
    """
    Creates an unexecuted proposal in pending_actions requiring operator confirmation using SQLAlchemy.
    """
    clean_machine = machine_name.strip()
    try:
        from backend.system1.guard import get_machine_registry
        known_machines, aliases = await get_machine_registry()
        matched = False
        for m in known_machines:
            if m.lower() in clean_machine.lower():
                clean_machine = m
                matched = True
                break
        if not matched:
            for alias, target in aliases.items():
                if alias in clean_machine.lower():
                    clean_machine = target
                    matched = True
                    break
        if not matched and known_machines:
            for km in known_machines:
                if km[:2].lower() in clean_machine.lower():
                    clean_machine = km
                    matched = True
                    break
            if not matched:
                clean_machine = known_machines[0]
    except Exception:
        clean_machine = clean_machine[:64]

    stmt = (
        insert(PendingAction)
        .values(
            machine_name=clean_machine,
            proposed_action=str(proposed_action).strip(),
            parameter_value=str(parameter_value).strip(),
            reasoning=str(reasoning).strip(),
            status="PENDING"
        )
        .returning(PendingAction.id)
    )

    async with get_session() as session:
        result = await session.execute(stmt)
        proposal_id = result.scalar()
        await session.commit()

    return {
        "proposal_id": proposal_id,
        "machine_name": clean_machine,
        "proposed_action": proposed_action,
        "parameter_value": parameter_value,
        "status": "PENDING_CONFIRMATION",
        "message": f"Proposal #{proposal_id} logged for {clean_machine}. Awaiting Somchai's authorization."
    }


# Tool Registry for OpenAI / OpenRouter function calling
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_energy_aggregates",
            "description": "Calculates total or daily energy consumption in kWh = sum(power_kw * 5/60) across machines or zones for a Bangkok time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "Start time in Bangkok time (e.g., 'Day 2 00:00' or 'YYYY-MM-DD HH:MM')."},
                    "end_time": {"type": "string", "description": "End time in Bangkok time (e.g., 'Day 2 23:59' or 'YYYY-MM-DD HH:MM')."},
                    "machine_name": {"type": "string", "description": "Optional machine identifier (e.g., 'AC-L1'). Omit for whole building."},
                    "group_by": {"type": "string", "enum": ["total", "day", "machine"], "description": "Granularity of aggregation."}
                },
                "required": ["start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_sensor_readings",
            "description": "Queries statistical summary of machine sensor readings (temperature, power, setpoint, fan speed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "machine_name": {"type": "string", "description": "Machine identifier (e.g. 'AC-L1', 'AC-S5')."},
                    "start_time": {"type": "string", "description": "Start Bangkok time (e.g. 'Day 5 08:00')."},
                    "end_time": {"type": "string", "description": "End Bangkok time (e.g. 'Day 5 18:00')."},
                    "metric": {"type": "string", "enum": ["temperature", "power_kw", "setpoint", "speed", "all"], "default": "temperature"}
                },
                "required": ["machine_name", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_ai_decisions",
            "description": "Searches the log of automated actions taken (TURN ON, TURN OFF, SET TEMP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "Start time in Bangkok time (e.g. 'Day 6 22:00')."},
                    "end_time": {"type": "string", "description": "End time in Bangkok time (e.g. 'Day 7 06:00')."},
                    "machine_name": {"type": "string", "description": "Optional machine filter."},
                    "action": {"type": "string", "enum": ["TURN ON", "TURN OFF", "SET TEMP", "ANY"], "default": "ANY"}
                },
                "required": ["start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Searches facility operator manual, AI control policy, building schedule, and maintenance logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords or search question (e.g. 'AC-S3 turn off rule' or 'overnight schedule')."},
                    "document_filter": {"type": "string", "enum": ["all", "ai_control_policy", "operator_manual", "building_schedule", "maintenance_log"], "default": "all"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_control_action",
            "description": "Proposes an HVAC control action requiring human confirmation (Problem 3 Option A). Assistant cannot directly execute writes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "machine_name": {"type": "string", "description": "Machine to control."},
                    "proposed_action": {"type": "string", "enum": ["TURN OFF", "TURN ON", "SET TEMP"]},
                    "parameter_value": {"type": "string", "description": "Optional parameter (e.g. '24°C')."},
                    "reasoning": {"type": "string", "description": "Why this action is recommended."}
                },
                "required": ["machine_name", "proposed_action", "reasoning"]
            }
        }
    }
]

TOOL_MAP = {
    "query_energy_aggregates": query_energy_aggregates,
    "query_sensor_readings": query_sensor_readings,
    "query_ai_decisions": query_ai_decisions,
    "search_docs": search_docs,
    "propose_control_action": propose_control_action
}
