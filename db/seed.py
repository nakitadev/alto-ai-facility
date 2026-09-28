#!/usr/bin/env python3
"""
Seed script for AltoTech AI Engineer Technical Assessment.
Generates 7 days of realistic 5-minute telemetry for 12 machines,
plus 8 to 12 AI decisions per day on days 4 to 7.
"""

import os
import random
import datetime
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.extras import execute_batch

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

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "building_db"),
    )

def seed_database(seed_val: int = None):
    # Dynamic random seed for reproducible or arbitrary re-seeded assessments
    if seed_val is None:
        seed_val = int(os.getenv("SEED_VALUE", "42"))
    random.seed(seed_val)
    print(f"Seeding database with random seed: {seed_val}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Executing schema...")
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        cur.execute(f.read())
    conn.commit()

    print("Seeding machines table...")
    for m in MACHINES:
        cur.execute("""
            INSERT INTO machines (machine_name, machine_type, zone, floor, rated_power_kw, is_critical_24_7, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (machine_name) DO UPDATE SET
                machine_type = EXCLUDED.machine_type,
                zone = EXCLUDED.zone,
                floor = EXCLUDED.floor,
                rated_power_kw = EXCLUDED.rated_power_kw,
                is_critical_24_7 = EXCLUDED.is_critical_24_7,
                description = EXCLUDED.description;
        """, (m["name"], m["type"], m["zone"], m["floor"], m["power"], m["critical"], m["desc"]))
    conn.commit()

    print("Cleaning existing readings and decisions...")
    cur.execute("TRUNCATE sensor_readings CASCADE;")
    cur.execute("TRUNCATE ai_decisions CASCADE;")
    conn.commit()

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
                    # 00:00 - 06:00: Minimal only (AC-S5, FAN-01)
                    status = "OFF"
                elif 6 <= hour < 8:
                    # 06:00 - 08:00: Large ACs startup, fans turn on
                    if m_name in ["AC-L1", "AC-L2", "AC-L3", "FAN-02", "FAN-03", "FAN-04"]:
                        status = "ON"
                    else:
                        status = "OFF"
                elif 8 <= hour < 18:
                    # 08:00 - 18:00: Peak hours
                    status = "ON"
                    # In AI period, AC-S3 (meeting rooms) is turned off at 14:30-16:00 due to zero occupancy
                    if is_ai_day and m_name == "AC-S3" and (14 * 60 + 30 <= minute_of_day < 16 * 60):
                        status = "OFF"
                elif 18 <= hour < 22:
                    # 18:00 - 22:00: Evening wind-down
                    if not is_ai_day:
                        # In manual days 1-3, all machines run until 22:00
                        status = "ON"
                    else:
                        # In AI control days: small ACs and upper fans shut down gradually
                        if m_name in ["AC-S1", "AC-S2", "AC-S4"]:
                            status = "OFF"
                        elif hour >= 19 and m_name in ["AC-L2", "AC-L3", "FAN-02", "FAN-03", "FAN-04"]:
                            status = "OFF"
                        else:
                            status = "ON"
                else: # 22:00 - 24:00
                    # Night mode: AC-L1 (lobby), AC-S5, FAN-01
                    if m_name in ["AC-L1", "AC-S5", "FAN-01"]:
                        status = "ON"
                    else:
                        status = "OFF"

                # Calculate power, temperature, setpoint, speed
                if is_fan:
                    temp = None
                    setpoint = None
                    if status == "ON":
                        # Fans: 40-70% of rated, speed 40-80%
                        if not is_ai_day:
                            speed = 75.0 + random.uniform(-2.0, 2.0)
                            power_pct = 0.65 + random.uniform(-0.03, 0.03)
                        else:
                            # AI modulates fan speed based on load
                            speed = 50.0 if hour < 8 or hour >= 18 else 65.0 + random.uniform(-3.0, 3.0)
                            power_pct = (speed / 100.0) * 0.75
                        
                        power_kw = round(rated * power_pct, 2)
                        speed = round(speed, 1)
                    else:
                        speed = 0.0
                        power_kw = 0.0
                else:
                    # AC Unit
                    speed = None
                    if status == "ON":
                        # Setpoint logic
                        if not is_ai_day:
                            # Manual days: static 25.0°C setpoint
                            setpoint = 25.0
                            # Power load: 55-75% of rated in manual days
                            load_pct = 0.60 + (0.15 if 10 <= hour <= 16 else 0.0) + random.uniform(-0.04, 0.04)
                        else:
                            # AI days: dynamic setpoints
                            if m_name == "AC-L1" and hour >= 22:
                                setpoint = 27.0  # Lobby night mode relaxation
                            elif m_name in ["AC-L1", "AC-L2"] and (9 * 60 + 30 <= minute_of_day <= 15 * 60) and outdoor_temp > 33.0:
                                setpoint = 24.0  # Outdoor temp compensation
                            elif m_name == "AC-S5":
                                setpoint = 21.0  # Server room constant
                            else:
                                setpoint = 24.5
                            
                            # AI efficiency optimization: 15% lower power than manual
                            base_load = 0.48 + (0.12 if 10 <= hour <= 16 else 0.0)
                            load_pct = base_load + random.uniform(-0.03, 0.03)
                        
                        # Power in kW
                        power_kw = round(rated * max(0.30, min(0.80, load_pct)), 2)
                        
                        # Zone temperature varies around setpoint (22-27°C)
                        if m_name == "AC-S5":
                            temp = round(21.2 + random.uniform(-0.3, 0.3), 2)
                        elif m_name == "AC-L1":
                            # Lobby temp (Question 6 checks average lobby temp during office hours 08:00-18:00 on Day 5)
                            if 8 <= hour < 18:
                                # Target around 24.2°C during Day 5 office hours
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

    print(f"Inserting {len(readings)} sensor reading records...")
    execute_batch(cur, """
        INSERT INTO sensor_readings (time, machine_name, status, power_kw, temperature, setpoint, speed)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, readings, page_size=2000)
    conn.commit()

    print("Generating AI decisions for days 4 to 7...")
    decisions = []
    
    for day_idx in range(4, 8):
        day_date = BASE_DATE + datetime.timedelta(days=day_idx - 1)
        
        # Helper to construct UTC timestamp from BKK hour and minute
        def bkk_time(h, m):
            return datetime.datetime(day_date.year, day_date.month, day_date.day, h, m, tzinfo=BANGKOK_TZ).astimezone(UTC_TZ)

        # Standard daily decisions required by Appendix A:
        # 1. 06:00: TURN ON AC-L1, AC-L2
        decisions.append((bkk_time(6, 0), "AC-L1", "TURN ON", "ON", "Building opening, pre-cool zones A and B"))
        decisions.append((bkk_time(6, 0), "AC-L2", "TURN ON", "ON", "Building opening, pre-cool zones A and B"))
        # 2. 06:00: TURN ON ventilation fans
        decisions.append((bkk_time(6, 0), "FAN-02", "TURN ON", "ON", "Morning startup ventilation for Ground Floor"))
        decisions.append((bkk_time(6, 0), "FAN-03", "TURN ON", "ON", "Morning startup ventilation for Floors 1–3"))
        # 3. 09:30: SET TEMP AC-L1 25°C to 24°C, outdoor temp rising to 34°C
        decisions.append((bkk_time(9, 30), "AC-L1", "SET TEMP", "24°C", "25°C to 24°C, outdoor temp rising to 34°C"))
        # 4. 14:30: TURN OFF AC-S3 Meeting rooms empty, no occupancy detected
        decisions.append((bkk_time(14, 30), "AC-S3", "TURN OFF", "OFF", "Meeting rooms empty, no occupancy detected"))
        # 5. 16:00: TURN ON AC-S3 Pre-cooling for scheduled meeting
        decisions.append((bkk_time(16, 0), "AC-S3", "TURN ON", "ON", "Pre-cooling for scheduled afternoon meeting"))
        # 6. 17:30: SET TEMP AC-L1 24°C to 25°C, solar load reducing
        decisions.append((bkk_time(17, 30), "AC-L1", "SET TEMP", "25°C", "Solar load abating, restoring standard setpoint"))
        # 7. 18:30: TURN OFF AC-S1, AC-S2
        decisions.append((bkk_time(18, 30), "AC-S1", "TURN OFF", "OFF", "Tenant office hours ended, floor empty"))
        decisions.append((bkk_time(18, 30), "AC-S2", "TURN OFF", "OFF", "Tenant office hours ended, floor empty"))
        # 8. 19:00: TURN OFF AC-L2, AC-L3, FAN-02..04 Evening shutdown
        decisions.append((bkk_time(19, 0), "AC-L2", "TURN OFF", "OFF", "Evening shutdown, upper zones vacant"))
        decisions.append((bkk_time(19, 0), "AC-L3", "TURN OFF", "OFF", "Evening shutdown, upper zones vacant"))
        decisions.append((bkk_time(19, 0), "FAN-02", "TURN OFF", "OFF", "Evening shutdown"))
        decisions.append((bkk_time(19, 0), "FAN-03", "TURN OFF", "OFF", "Evening shutdown"))
        decisions.append((bkk_time(19, 0), "FAN-04", "TURN OFF", "OFF", "Evening shutdown"))
        # 9. 22:00: SET TEMP AC-L1 Relaxed to 27°C, lobby night mode
        decisions.append((bkk_time(22, 0), "AC-L1", "SET TEMP", "27°C", "Relaxed to 27°C, lobby night mode"))

    # Specific decisions for Question 4: Between 22:00 on Day 6 and 06:00 on Day 7:
    # 22:00 Day 6: AC-L1 SET TEMP 27°C (already included above at day 6 22:00)
    # Add night inspection decision at 23:30 Day 6 and 02:00 Day 7:
    d6_date = BASE_DATE + datetime.timedelta(days=5)
    d7_date = BASE_DATE + datetime.timedelta(days=6)
    d6_2330 = datetime.datetime(d6_date.year, d6_date.month, d6_date.day, 23, 30, tzinfo=BANGKOK_TZ).astimezone(UTC_TZ)
    d7_0200 = datetime.datetime(d7_date.year, d7_date.month, d7_date.day, 2, 0, tzinfo=BANGKOK_TZ).astimezone(UTC_TZ)
    
    decisions.append((d6_2330, "AC-S4", "TURN OFF", "OFF", "Executive floor sweep confirmed empty, auxiliary power turned off"))
    decisions.append((d7_0200, "FAN-01", "SET TEMP", "40%", "Basement air quality optimal, speed sustained at baseline 40%"))

    print(f"Inserting {len(decisions)} AI decision audit records...")
    execute_batch(cur, """
        INSERT INTO ai_decisions (timestamp, machine_name, action, parameter_value, reason)
        VALUES (%s, %s, %s, %s, %s)
    """, decisions)
    conn.commit()

    # Pre-populate sample pending action for Question 10 demo (Option A)
    cur.execute("""
        INSERT INTO pending_actions (machine_name, proposed_action, parameter_value, reasoning, status)
        VALUES ('AC-L2', 'TURN OFF', 'OFF', 'Operator requested immediate shutdown; pending human confirmation.', 'PENDING')
        ON CONFLICT DO NOTHING;
    """)
    conn.commit()

    cur.close()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    import sys
    seed_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    seed_database(seed_arg)
