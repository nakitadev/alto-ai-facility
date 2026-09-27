# Building HVAC Operator Manual

**Facility**: Bangkok Commercial Tower  
**Location**: Bangkok, Thailand (UTC+7)  
**Document ID**: DOC-OPS-2026-v2  

---

## 1. System Overview & Machine Inventory

The cooling and ventilation infrastructure consists of 12 primary units divided into three distinct operational categories:

1. **Large Air Handling Units (AC-L1 to AC-L3)**:
   * **AC-L1**: Zone A (Ground Floor and Main Atrium/Lobby) - Rated 45 kW.
   * **AC-L2**: Zone B (Tenant Floors 1–3) - Rated 45 kW.
   * **AC-L3**: Zone C (Tenant Floors 4–6) - Rated 45 kW.
   * Responsible for base cooling load and fresh air conditioning for common and open-plan tenant areas.

2. **Small Split Units (AC-S1 to AC-S5)**:
   * **AC-S1**: Floor 1 Tenant Offices - Rated 12 kW.
   * **AC-S2**: Floor 2 Tenant Offices - Rated 12 kW.
   * **AC-S3**: Floor 3 Dedicated Conference & Meeting Rooms - Rated 10 kW.
   * **AC-S4**: Floor 5 Executive Suites - Rated 10 kW.
   * **AC-S5**: Critical Server Room & Network Data Center - Rated 15 kW. Must maintain 24/7 active cooling.

3. **Fresh Air Ventilation Fans (FAN-01 to FAN-04)**:
   * **FAN-01**: Basement Parking Fresh Air Injection - Rated 5.5 kW (Speed controlled 40–80%).
   * **FAN-02**: Ground Floor Air Circulation - Rated 3.5 kW.
   * **FAN-03**: Low-Rise Shaft Ventilation (Floors 1–3) - Rated 4.0 kW.
   * **FAN-04**: High-Rise Shaft Ventilation (Floors 4–6) - Rated 4.0 kW.

---

## 2. Sensor Instrumentation & Telemetry Capabilities

Every unit reports real-time telemetry every 5 minutes into the central building automation system:
* **Electrical Power (`power_kw`)**: Active power draw in kW.
* **Zone Temperature (`temperature`)**: Ambient room temperature in degrees Celsius (°C).
* **Setpoint Temperature (`setpoint`)**: Target cooling setpoint (°C).
* **Operational Status (`status`)**: Discrete binary state (`ON` or `OFF`).
* **Fan Speed (`speed`)**: Variable speed percentage (40–80%) for ventilation units.

> **CRITICAL SENSOR NOTICE**: The building telemetry network **DOES NOT** monitor relative or absolute humidity. There are **zero humidity sensors** installed across any tenant space, common zone, or the server room. Operators and automated assistants must never infer or estimate humidity values.

---

## 3. Standard Operating Comfort Bands

* **Occupied Hours (06:00 – 22:00 Bangkok Time)**:
  * Zone Temperature target: **22.0°C – 27.0°C**.
  * Standard setpoint range: **23.0°C – 26.0°C**.
  * Server Room (`AC-S5`): Strict target: **20.0°C – 22.0°C** setpoint, 24 hours a day, 365 days a year.
* **Unoccupied / Night Hours (22:00 – 06:00 Bangkok Time)**:
  * Non-critical units are shut down or setback to energy preservation mode (27.0°C).

---

## 4. Emergency Contacts & Escalation Matrix

* **Somchai Thanakit** (Chief Facility Operator): Extension 4101 / Mobile +66 81-555-0192
* **Building Automation Support (AltoTech Global)**: support@altotech.ai / Emergency Dispatch: +66 2-018-9900
* **Electrical Engineering On-Duty**: Facility Control Room, Level B1.
