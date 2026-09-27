# AI Energy Optimization Control Policy

**Facility**: Bangkok Commercial Tower  
**Effective Date**: Automated Phase (Days 4–7 onwards)  
**Document ID**: DOC-POL-AI-004  
**Author**: Energy Optimization Systems Engineering  

---

## 1. Operating Principles

The building automation system employs an autonomous AI supervisory agent designed to reduce unnecessary power consumption while maintaining strict tenant comfort and equipment safety. The AI executes discrete actions logged with full rationale in the `ai_decisions` table.

---

## 2. Autonomous Control Rules

### Rule 1: Occupancy-Based Dynamic Shutdown
* **Target Units**: Floor-specific split units, particularly **`AC-S3`** (Floor 3 Dedicated Meeting Rooms).
* **Policy Trigger**: If PIR motion sensors and calendar integration report zero occupancy in the meeting suites for more than 15 consecutive minutes during operational hours, the AI immediately issues a `TURN OFF` command to `AC-S3`.
* **Rationale**: Meeting rooms represent high-intermittency loads. Shutting off `AC-S3` during vacant afternoon hours (e.g. 14:30) avoids cooling empty conference rooms without affecting tenant offices.
* **Pre-cooling Override**: The AI reactivates the unit 20 minutes prior to any scheduled room reservation.

### Rule 2: Outdoor Temperature Compensation Setpoints
* **Target Units**: Large Air Handlers (**`AC-L1`**, **`AC-L2`**, **`AC-L3`**).
* **Policy Trigger**: When ambient Bangkok outdoor temperatures rise above 34.0°C during peak sunlight (typically 09:30–15:00), the AI proactively lowers the chilled water setpoint from 25.0°C to 24.0°C to prevent thermal inertia lag.
* **Evening Recovery**: As solar load abates after 17:00, setpoints are gradually restored to 25.0°C.

### Rule 3: Night Mode Setback & Sequential Shutdown
* **Schedule Window**: 18:00 – 22:00 (Evening Wind-Down) and 22:00 – 06:00 (Night Mode).
* **Policy Sequence**:
  1. **18:00–22:00**: Individual office ACs (`AC-S1`, `AC-S2`, `AC-S4`) are shut down as tenant floors empty.
  2. **19:00**: Upper large air handlers (`AC-L2`, `AC-L3`) and high-rise ventilation fans (`FAN-02`, `FAN-03`, `FAN-04`) are commanded `TURN OFF`.
  3. **22:00**: Ground Floor Lobby unit (`AC-L1`) temperature setpoint is relaxed from 24.0°C/25.0°C to **27.0°C** (`SET TEMP 27°C`) to preserve energy while preventing extreme humidity buildup in the atrium.

---

## 3. Mission-Critical Equipment Exclusion List (NEVER SHUT OFF)

* **Unit `AC-S5` (Server Room & Data Center)**:
  * **STRICT PROHIBITION**: Unit `AC-S5` is hard-interlocked. The AI controller is **strictly forbidden from issuing a `TURN OFF` command** to `AC-S5` under any operational condition.
  * Must run continuously **24 hours a day, 7 days a week**.
* **Unit `FAN-01` (Basement Parking Ventilation)**:
  * Operates continuously 24/7 at minimum 40% speed for carbon monoxide safety compliance.

---

## 4. Manual Operation Baseline vs. AI Optimization Comparison

* **Days 1 to 3 (Manual Baseline)**: All equipment operated under manual human control, running continuously from 06:00 to 22:00 regardless of occupancy, with static setpoints and no setback.
* **Days 4 to 7 (AI Optimization Active)**: AI control actively trims off-peak waste, yielding approximately **13% to 17% overall energy savings** across the building.
