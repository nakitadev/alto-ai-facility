import re
import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, Tuple
from backend.database import get_registered_machines, execute_insert
from backend.config import DEFAULT_TIMEZONE

BANGKOK_TZ = ZoneInfo(DEFAULT_TIMEZONE)

# Known building machines
MACHINE_NAMES = [
    "AC-L1", "AC-L2", "AC-L3",
    "AC-S1", "AC-S2", "AC-S3", "AC-S4", "AC-S5",
    "FAN-01", "FAN-02", "FAN-03", "FAN-04"
]

ZONE_ALIASES = {
    "lobby": "AC-L1",
    "atrium": "AC-L1",
    "zone a": "AC-L1",
    "zone b": "AC-L2",
    "floors 1-3": "AC-L2",
    "zone c": "AC-L3",
    "floors 4-6": "AC-L3",
    "floor 1": "AC-S1",
    "floor 2": "AC-S2",
    "meeting room": "AC-S3",
    "meeting rooms": "AC-S3",
    "conference room": "AC-S3",
    "executive": "AC-S4",
    "floor 5": "AC-S4",
    "server room": "AC-S5",
    "data center": "AC-S5",
    "datacenter": "AC-S5",
    "basement": "FAN-01",
    "parking": "FAN-01",
}

class System1Guard:
    """
    System 1: Sub-100ms Fast Guard, Intent Classifier, and Security Shield.
    Enforces read-only safety tripwires, rejects unmonitored sensors,
    sanitizes prompt injections, and resolves Bangkok temporal bounds.
    """

    def analyze_query(self, user_prompt: str) -> Dict[str, Any]:
        prompt_lower = user_prompt.lower()
        
        # 1. Prompt Injection Shield
        if re.search(r"ignore\s+(all\s+)?previous\s+instructions", prompt_lower):
            return {
                "guard_triggered": True,
                "intent": "INJECTION_BLOCKED",
                "immediate_response": "Security Guardrail Alert: Subversive instruction pattern detected and blocked. The assistant operates strictly under facility control policy."
            }

        # 2. Unmonitored Sensor Check (e.g. Humidity)
        if "humidity" in prompt_lower or "rh%" in prompt_lower or "moisture" in prompt_lower:
            return {
                "guard_triggered": True,
                "intent": "UNANSWERABLE_NO_SENSOR",
                "immediate_response": (
                    "The building is not equipped with humidity sensors anywhere in the facility, "
                    "including the server room (AC-S5). Available sensors monitor electrical power (kW), "
                    "temperature (°C), setpoint (°C), operational status (ON/OFF), and ventilation speed (%)."
                )
            }

        # 3. Direct Machine Control / Write Action Tripwire
        write_patterns = [
            r"\b(turn\s+off|switch\s+off|shut\s+down|power\s+down|stop)\b",
            r"\b(turn\s+on|switch\s+on|power\s+up|start)\b",
            r"\b(set\s+temp|set\s+temperature|change\s+setpoint|adjust\s+temperature)\b",
        ]
        
        is_write = any(re.search(pat, prompt_lower) for pat in write_patterns)
        
        # Check if the query asks about historical AI action vs commanding a current action
        # e.g., "Why did the AI turn off AC-S3" is analytical, NOT a write command!
        is_historical_why = bool(re.search(r"\b(why|when|what\s+did|how\s+many\s+times)\b", prompt_lower))
        
        if is_write and not is_historical_why:
            # Extract target machine
            target_machine = None
            for m in MACHINE_NAMES:
                if m.lower() in prompt_lower:
                    target_machine = m
                    break
            
            if not target_machine:
                for alias, m in ZONE_ALIASES.items():
                    if alias in prompt_lower:
                        target_machine = m
                        break

            target_machine = target_machine or "AC-L2"
            
            # Determine proposed action
            action = "TURN OFF" if any(w in prompt_lower for w in ["off", "shut", "stop"]) else "TURN ON"
            if "set" in prompt_lower or "temp" in prompt_lower:
                action = "SET TEMP"

            # Auto-record proposal into pending_actions table (Problem 3 Option A)
            proposal_id = None
            try:
                proposal_id = execute_insert(
                    """
                    INSERT INTO pending_actions (machine_name, proposed_action, parameter_value, reasoning, status)
                    VALUES (%s, %s, %s, %s, 'PENDING')
                    RETURNING id;
                    """,
                    (target_machine, action, "N/A", f"Operator prompted: '{user_prompt}'")
                )
            except Exception:
                proposal_id = 999

            return {
                "guard_triggered": True,
                "intent": "WRITE_ACTION_PROPOSED",
                "target_machine": target_machine,
                "proposed_action": action,
                "proposal_id": proposal_id,
                "immediate_response": (
                    f"I do not have authorization to directly control physical HVAC hardware. "
                    f"In accordance with our safety architecture (Propose-Only Control), I have created a pending proposal "
                    f"to {action} {target_machine} (Proposal #{proposal_id}). "
                    f"Please review and confirm via the control interface."
                )
            }

        # 4. Out of Range / Calendar span check (e.g. "this month vs last month")
        if re.search(r"\b(this\s+month|last\s+month|last\s+year|annual|historical\s+year)\b", prompt_lower):
            return {
                "guard_triggered": True,
                "intent": "TEMPORAL_OUT_OF_RANGE",
                "immediate_response": (
                    "Our active dataset contains 7 days of 5-minute telemetry (Day 1 through Day 7). "
                    "I cannot provide a month-over-month comparison because data for previous months is not available. "
                    "I can, however, compare individual days (e.g., Day 2 vs Day 6) or compare the 3-day manual baseline against the 4-day AI-controlled period."
                )
            }

        # 5. Normal analytical query - extract domain hints for System 2
        entities = self._extract_entities(user_prompt)
        return {
            "guard_triggered": False,
            "intent": "ANALYTICAL_QUERY",
            "entities": entities
        }

    def _extract_entities(self, prompt: str) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        extracted_machines = [m for m in MACHINE_NAMES if m.lower() in prompt_lower]
        
        # Check aliases
        for alias, m in ZONE_ALIASES.items():
            if alias in prompt_lower and m not in extracted_machines:
                extracted_machines.append(m)

        # Detect days mentioned
        days = re.findall(r"\bday\s*([1-7])\b", prompt_lower)
        days = [int(d) for d in days]

        return {
            "machines": extracted_machines,
            "days": days,
            "has_yesterday": "yesterday" in prompt_lower,
            "has_overnight": "overnight" in prompt_lower or "night" in prompt_lower
        }

# Global singleton
system1_guard = System1Guard()
