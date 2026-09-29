from typing import Dict, Any, Optional
from sqlalchemy import select, func, cast, Date, Numeric, insert

from backend.database import get_session
from backend.models import SensorReading, AIDecision, PendingAction
from backend.utils.timeutils import parse_bangkok_time, get_base_date

# Tool 0: Telemetry Coverage & Freshness Check (Grounding & Boundary Tool)
async def query_data_coverage(machine_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Inspects available telemetry date ranges, sensor freshness, and monitored metrics.
    Use this tool when answering questions about data availability, date boundaries,
    staleness/freshness of current readings, or unmonitored metrics like humidity.
    """
    from backend.database import get_simulated_time_bounds, get_registered_machines
    bounds = await get_simulated_time_bounds()
    machines = await get_registered_machines()

    latest_reading = None
    if bounds.get("has_data") and bounds.get("max_bkk"):
        latest_reading = {
            "latest_reading_bkk": bounds["max_bkk"],
            "simulated_current_time_bkk": bounds.get("current_time_bkk") or bounds.get("simulated_now_bkk")
        }

    return {
        "has_data": bounds.get("has_data", False),
        "days_available": bounds.get("days_available", 0),
        "min_bkk": bounds.get("min_bkk", "N/A"),
        "max_bkk": bounds.get("max_bkk", "N/A"),
        "latest_sensor_reading": latest_reading,
        "monitored_metrics": ["power_kw (kW)", "temperature (°C)", "setpoint (°C)", "speed (%)", "status (ON/OFF)"],
        "unmonitored_metrics": ["humidity", "co2", "air_quality", "pressure", "water_flow"],
        "machine_count": len(machines),
        "target_machine": machine_name or "ALL_FACILITY_MACHINES"
    }

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
