#!/usr/bin/env python3
"""
Seed script for AltoTech AI Engineer Technical Assessment.
Generates 7 days of realistic 5-minute telemetry for 12 machines,
plus 8 to 12 AI decisions per day on days 4 to 7.
Powered purely by asyncpg (zero synchronous database drivers).
"""

import os
import random
import datetime
import asyncio
from zoneinfo import ZoneInfo
import asyncpg

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
UTC_TZ = ZoneInfo("UTC")

# 7-day calendar window: Day 1 (Monday) to Day 7 (Sunday)
BASE_DATE = datetime.date(2026, 9, 1)

MACHINES = [
    {"name": "AC-L1", "type": "Large AC", "zone": "Zone A (Lobby & Ground)", "floor": "Ground", "power": 45.0, "critical": False, "desc": "Main cooling for Zone A atrium and lobby"},
    {"name": "AC-L2", "type": "Large AC", "zone": "Zone B (Floors 1–3)", "floor": "Floors 1-3", "power": 45.0, "critical": False, "desc": "Main cooling for Zone B tenant floors"},
    {"name": "AC-L3", "type": "Large AC", "zone": "Zone C (Floors 4–6)", "floor": "Floors 4-6", "power": 45.0, "critical": False, "desc": "Main cooling for Zone C tenant floors"},
    {"name": "AC-S1", "type": "Small AC", "zone": "Floor 1 Office", "floor": "Floor 1", "power": 12.0, "critical": False, "desc": "Floor 1 tenant office split AC"},
    {"name": "AC-S2", "type": "Small AC", "zone": "Floor 2 Office", "floor": "Floor 2", "power": 12.0, "critical": False, "desc": "Floor 2 tenant office split AC"},
    {"name": "AC-S3", "type": "Small AC", "zone": "Floor 3 Meeting Rooms", "floor": "Floor 3", "power": 10.0, "critical": False, "desc": "Floor 3 shared conference & meeting rooms"},
    {"name": "AC-S4", "type": "Small AC", "zone": "Floor 5 Executive", "floor": "Floor 5", "power": 10.0, "critical": False, "desc": "Floor 5 executive suites"},
    {"name": "AC-S5", "type": "Small AC", "zone": "Server Room (24/7)", "floor": "Floor 6", "power": 15.0, "critical": True, "desc": "Critical server room & data center unit (24/7 operation)"},
    {"name": "FAN-01", "type": "Ventilation", "zone": "Basement Parking", "floor": "Basement", "power": 5.5, "critical": True, "desc": "Basement parking continuous exhaust ventilation"},
    {"name": "FAN-02", "type": "Ventilation", "zone": "Ground Floor", "floor": "Ground", "power": 3.5, "critical": False, "desc": "Ground floor circulation fan"},
    {"name": "FAN-03", "type": "Ventilation", "zone": "Floors 1–3", "floor": "Floors 1-3", "power": 4.0, "critical": False, "desc": "Floors 1-3 fresh air ventilation"},
    {"name": "FAN-04", "type": "Ventilation", "zone": "Floors 4–6", "floor": "Floors 4-6", "power": 4.0, "critical": False, "desc": "Floors 4-6 fresh air ventilation"},
]

async def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
        if clean_url.startswith("postgres://"):
            clean_url = clean_url.replace("postgres://", "postgresql://", 1)
        return await asyncpg.connect(clean_url)
    
    return await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "building_db"),
    )

async def seed_database(seed_val: int = None):
    if seed_val is None:
        seed_val = int(os.getenv("SEED_VALUE", "42"))
    random.seed(seed_val)
    print(f"Seeding database with random seed: {seed_val}")
    
    conn = await get_db_connection()
    
    print("Executing schema...")
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        await conn.execute(f.read())

    print("Seeding machines table...")
    machine_rows = [
        (m["name"], m["type"], m["zone"], m["floor"], m["power"], m["critical"], m["desc"])
        for m in MACHINES
    ]
    await conn.executemany("""
        INSERT INTO machines (machine_name, machine_type, zone, floor, rated_power_kw, is_critical_24_7, description)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (machine_name) DO UPDATE SET
            machine_type = EXCLUDED.machine_type,
            zone = EXCLUDED.zone,
            floor = EXCLUDED.floor,
            rated_power_kw = EXCLUDED.rated_power_kw,
            is_critical_24_7 = EXCLUDED.is_critical_24_7,
            description = EXCLUDED.description;
    """, machine_rows)

    print("Cleaning existing readings and decisions...")
    await conn.execute("TRUNCATE sensor_readings CASCADE; TRUNCATE ai_decisions CASCADE;")

    print("Generating 7 days of 5-minute telemetry (24,192 rows)...")
    readings = []
    
    for day_idx in range(1, 8):
        day_date = BASE_DATE + datetime.timedelta(days=day_idx - 1)
        is_ai_day = (day_idx >= 4)  # Days 4 to 7 are AI control; 1 to 3 are manual
        
        # 288 5-minute steps per day
        for step in range(288):
            minute_of_day = step * 5
            hour = minute_of_day // 60
            minute = minute_of_day % 60
            
            bkk_dt = datetime.datetime(day_date.year, day_date.month, day_date.day, hour, minute, tzinfo=BANGKOK_TZ)
            utc_dt = bkk_dt.astimezone(UTC_TZ)
            
            # Base outdoor temperature profile in Bangkok: min 27°C at night, up to 34.5°C peak at 13:00-14:30
            ambient_factor = -1.0 * ((hour - 14) / 10.0) ** 2 + 1.0  # Peak around 14:00
            outdoor_temp = 27.0 + max(0.0, ambient_factor) * 7.5 + random.uniform(-0.3, 0.3)
            
            for m in MACHINES:
                m_name = m["name"]
                m_type = m["type"]
                rated = m["power"]
                is_fan = (m_type == "Ventilation")
                
                # Determine operational status based on time & mode
                status = "OFF"
                
                if m_name == "AC-S5":
                    # Server room runs 24/7 always
                    status = "ON"
                elif m_name == "FAN-01":
                    # Basement parking fan runs 24/7 always
                    status = "ON"
                elif 0 <= hour < 6:
                    # Overnight: everything off except critical
                    status = "OFF"
                elif is_ai_day:
                    # AI control logic (Days 4-7)
                    if m_name in ["AC-L1", "AC-L2"]:
                        # Pre-cool at 06:00, run during business hours, shutdown at 19:00 (AC-L1 stays in night mode relaxed until 22:00)
                        if 6 <= hour < 19:
                            status = "ON"
                        elif m_name == "AC-L1" and 19 <= hour < 22:
                            status = "ON"
                        else:
                            status = "OFF"
                    elif m_name == "AC-L3":
                        # Floor 4-6 AC: runs 08:00 to 19:00
                        status = "ON" if 8 <= hour < 19 else "OFF"
                    elif m_name in ["AC-S1", "AC-S2"]:
                        # Offices: 08:00 to 18:30
                        status = "ON" if (8 <= hour < 18 or (hour == 18 and minute <= 30)) else "OFF"
                    elif m_name == "AC-S3":
                        # Meeting rooms: AI shuts off during lunch/vacancy (14:30 to 16:00)
                        if 8 <= hour < 14 or (hour == 14 and minute < 30):
                            status = "ON"
                        elif 14 <= hour < 16:
                            status = "OFF"  # Specific scenario for Question 5: empty meeting rooms
                        elif 16 <= hour < 19:
                            status = "ON"
                        else:
                            status = "OFF"
                    elif m_name == "AC-S4":
                        # Executive: 08:30 to 19:00
                        status = "ON" if (8 <= hour < 19) else "OFF"
                    elif is_fan:
                        # Ventilation fans FAN-02, 03, 04: run 06:00 to 19:00
                        status = "ON" if 6 <= hour < 19 else "OFF"
                else:
                    # Manual baseline (Days 1-3): looser schedules, machines left on overnight or started earlier
                    if m_name in ["AC-L1", "AC-L2", "AC-L3"]:
                        status = "ON" if 6 <= hour < 22 else "OFF"
                    elif m_name in ["AC-S1", "AC-S2", "AC-S4"]:
                        status = "ON" if 7 <= hour < 21 else "OFF"
                    elif m_name == "AC-S3":
                        status = "ON" if 8 <= hour < 20 else "OFF"
                    elif is_fan:
                        status = "ON" if 6 <= hour < 21 else "OFF"

                # Calculate sensor telemetry based on status
                temp = None
                setpoint = None
                speed = None
                
                if is_fan:
                    if status == "ON":
                        if m_name == "FAN-01":
                            speed = 40.0 if (hour >= 22 or hour < 6) else 75.0
                        else:
                            speed = 60.0
                        power_kw = round(rated * (speed / 100.0) ** 2, 2)
                    else:
                        speed = 0.0
                        power_kw = 0.0
                else:
                    # Air conditioner
                    if status == "ON":
                        if is_ai_day:
                            if m_name == "AC-L1":
                                if 6 <= hour < 9 or (hour == 9 and minute < 30):
                                    setpoint = 25.0
                                elif 9 <= hour < 17 or (hour == 17 and minute < 30):
                                    setpoint = 24.0
                                elif 17 <= hour < 22:
                                    setpoint = 25.0
                                else:
                                    setpoint = 27.0
                            elif m_name == "AC-S5":
                                setpoint = 21.0
                            else:
                                setpoint = 24.5
                        else:
                            setpoint = 22.0 if m_name != "AC-S5" else 21.0
                        
                        # Power modulation based on outdoor temperature difference and occupancy
                        delta_t = max(1.0, outdoor_temp - setpoint)
                        load_pct = min(1.0, 0.45 + (delta_t / 18.0) + random.uniform(-0.05, 0.05))
                        power_kw = round(rated * max(0.30, min(0.80, load_pct)), 2)
                        
                        # Zone temperature varies around setpoint (22-27°C)
                        if m_name == "AC-S5":
                            temp = round(21.2 + random.uniform(-0.3, 0.3), 2)
                        elif m_name == "AC-L1":
                            if 8 <= hour < 18:
                                temp = round(24.2 + random.uniform(-0.4, 0.4), 2)
                            elif hour >= 22:
                                temp = round(26.8 + random.uniform(-0.3, 0.4), 2)
                            else:
                                temp = round(25.0 + random.uniform(-0.3, 0.3), 2)
                        else:
                            temp = round(setpoint + random.uniform(-0.5, 0.6), 2)
                    else:
                        power_kw = 0.0
                        setpoint = None
                        temp = round(27.0 + random.uniform(0.0, 1.5), 2) if hour >= 18 or hour < 6 else round(25.5 + random.uniform(-0.5, 0.5), 2)
                
                readings.append((utc_dt, m_name, status, power_kw, temp, setpoint, speed))

    print(f"Inserting {len(readings)} sensor reading records via asyncpg copy...")
    await conn.copy_records_to_table(
        "sensor_readings",
        records=readings,
        columns=["time", "machine_name", "status", "power_kw", "temperature", "setpoint", "speed"]
    )

    print("Generating AI decisions for days 4 to 7...")
    decisions = []
    
    for day_idx in range(4, 8):
        day_date = BASE_DATE + datetime.timedelta(days=day_idx - 1)
        
        def bkk_time(h, m):
            return datetime.datetime(day_date.year, day_date.month, day_date.day, h, m, tzinfo=BANGKOK_TZ).astimezone(UTC_TZ)

        decisions.append((bkk_time(6, 0), "AC-L1", "TURN ON", "ON", "Building opening, pre-cool zones A and B"))
        decisions.append((bkk_time(6, 0), "AC-L2", "TURN ON", "ON", "Building opening, pre-cool zones A and B"))
        decisions.append((bkk_time(6, 0), "FAN-02", "TURN ON", "ON", "Morning startup ventilation for Ground Floor"))
        decisions.append((bkk_time(6, 0), "FAN-03", "TURN ON", "ON", "Morning startup ventilation for Floors 1–3"))
        decisions.append((bkk_time(9, 30), "AC-L1", "SET TEMP", "24°C", "25°C to 24°C, outdoor temp rising to 34°C"))
        decisions.append((bkk_time(14, 30), "AC-S3", "TURN OFF", "OFF", "Meeting rooms empty, no occupancy detected"))
        decisions.append((bkk_time(16, 0), "AC-S3", "TURN ON", "ON", "Pre-cooling for scheduled afternoon meeting"))
        decisions.append((bkk_time(17, 30), "AC-L1", "SET TEMP", "25°C", "Solar load abating, restoring standard setpoint"))
        decisions.append((bkk_time(18, 30), "AC-S1", "TURN OFF", "OFF", "Tenant office hours ended, floor empty"))
        decisions.append((bkk_time(18, 30), "AC-S2", "TURN OFF", "OFF", "Tenant office hours ended, floor empty"))
        decisions.append((bkk_time(19, 0), "AC-L2", "TURN OFF", "OFF", "Evening shutdown, upper zones vacant"))
        decisions.append((bkk_time(19, 0), "AC-L3", "TURN OFF", "OFF", "Evening shutdown, upper zones vacant"))
        decisions.append((bkk_time(19, 0), "FAN-02", "TURN OFF", "OFF", "Evening shutdown"))
        decisions.append((bkk_time(19, 0), "FAN-03", "TURN OFF", "OFF", "Evening shutdown"))
        decisions.append((bkk_time(19, 0), "FAN-04", "TURN OFF", "OFF", "Evening shutdown"))
        decisions.append((bkk_time(22, 0), "AC-L1", "SET TEMP", "27°C", "Relaxed to 27°C, lobby night mode"))

    d6_date = BASE_DATE + datetime.timedelta(days=5)
    d7_date = BASE_DATE + datetime.timedelta(days=6)
    d6_2330 = datetime.datetime(d6_date.year, d6_date.month, d6_date.day, 23, 30, tzinfo=BANGKOK_TZ).astimezone(UTC_TZ)
    d7_0200 = datetime.datetime(d7_date.year, d7_date.month, d7_date.day, 2, 0, tzinfo=BANGKOK_TZ).astimezone(UTC_TZ)
    
    decisions.append((d6_2330, "AC-S4", "TURN OFF", "OFF", "Executive floor sweep confirmed empty, auxiliary power turned off"))
    decisions.append((d7_0200, "FAN-01", "SET TEMP", "40%", "Basement air quality optimal, speed sustained at baseline 40%"))

    print(f"Inserting {len(decisions)} AI decision audit records...")
    await conn.executemany("""
        INSERT INTO ai_decisions (timestamp, machine_name, action, parameter_value, reason)
        VALUES ($1, $2, $3, $4, $5);
    """, decisions)

    await conn.execute("""
        INSERT INTO pending_actions (machine_name, proposed_action, parameter_value, reasoning, status)
        VALUES ('AC-L2', 'TURN OFF', 'OFF', 'Operator requested immediate shutdown; pending human confirmation.', 'PENDING')
        ON CONFLICT DO NOTHING;
    """)

    await conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    import sys
    seed_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(seed_database(seed_arg))
