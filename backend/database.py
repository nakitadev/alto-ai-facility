import datetime
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.extras import RealDictCursor
from backend.config import DATABASE_URL, DEFAULT_TIMEZONE

BANGKOK_TZ = ZoneInfo(DEFAULT_TIMEZONE)
UTC_TZ = ZoneInfo("UTC")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def query_db(query: str, params: tuple = None, fetchone: bool = False, fetchall: bool = True):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
            conn.commit()
            return None
    finally:
        conn.close()

import asyncio

async def query_db_async(query: str, params: tuple = None, fetchone: bool = False, fetchall: bool = True):
    """Non-blocking async execution of query_db on a worker thread for ASGI applications."""
    return await asyncio.to_thread(query_db, query, params, fetchone, fetchall)

async def execute_insert_async(query: str, params: tuple = None) -> int:
    """Non-blocking async execution of execute_insert on a worker thread for ASGI applications."""
    return await asyncio.to_thread(execute_insert, query, params)


def execute_insert(query: str, params: tuple = None) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            inserted_id = None
            try:
                inserted_id = cur.fetchone()[0]
            except Exception:
                pass
            conn.commit()
            return inserted_id
    finally:
        conn.close()

def get_simulated_time_bounds():
    """
    Inspects TimescaleDB to dynamically find the operational boundaries
    and facility current time in Bangkok time (UTC+7).
    Derives all parameters purely from the database without any hardcoded mock defaults.
    """
    try:
        row = query_db("SELECT MIN(time) as min_time, MAX(time) as max_time FROM sensor_readings;", fetchone=True)
        if not row or not row["min_time"]:
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

def get_registered_machines():
    try:
        return query_db("SELECT machine_name, machine_type, zone, floor, rated_power_kw, is_critical_24_7, description FROM machines ORDER BY machine_name;")
    except Exception:
        return []

async def get_simulated_time_bounds_async():
    """Non-blocking async time bounds lookup for ASGI endpoints."""
    return await asyncio.to_thread(get_simulated_time_bounds)

async def get_registered_machines_async():
    """Non-blocking async machine registry lookup for ASGI endpoints."""
    return await asyncio.to_thread(get_registered_machines)

