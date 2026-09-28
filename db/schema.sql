-- Enable TimescaleDB extension if available
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Machine Registry Table
CREATE TABLE IF NOT EXISTS machines (
    machine_name VARCHAR(32) PRIMARY KEY,
    machine_type VARCHAR(32) NOT NULL,
    zone VARCHAR(64) NOT NULL,
    floor VARCHAR(32),
    rated_power_kw NUMERIC(6, 2) NOT NULL,
    is_critical_24_7 BOOLEAN DEFAULT FALSE,
    description TEXT
);

-- 2. Sensor Readings Time-Series Table
CREATE TABLE IF NOT EXISTS sensor_readings (
    time TIMESTAMPTZ NOT NULL,
    machine_name VARCHAR(32) NOT NULL REFERENCES machines(machine_name),
    status VARCHAR(8) NOT NULL CHECK (status IN ('ON', 'OFF')),
    power_kw NUMERIC(6, 2) NOT NULL CHECK (power_kw >= 0),
    temperature NUMERIC(4, 2), -- Nullable for fans
    setpoint NUMERIC(4, 2),    -- Nullable for fans
    speed NUMERIC(5, 2),       -- Nullable for ACs, 40-80% for fans
    PRIMARY KEY (time, machine_name)
);

-- Convert sensor_readings to a TimescaleDB hypertable partitioned by time
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'TimescaleDB hypertable setup skipped or already exists: %', SQLERRM;
END $$;

CREATE INDEX IF NOT EXISTS idx_sensor_readings_machine_time 
    ON sensor_readings (machine_name, time DESC);

-- 3. AI Decisions Audit Log
CREATE TABLE IF NOT EXISTS ai_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    machine_name VARCHAR(32) NOT NULL REFERENCES machines(machine_name),
    action VARCHAR(32) NOT NULL, -- 'TURN ON', 'TURN OFF', 'SET TEMP'
    parameter_value VARCHAR(64), -- e.g. '24°C'
    reason TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_time_machine 
    ON ai_decisions (timestamp, machine_name);

-- 4. Pending Control Actions (Problem 3 Option A - Propose-Only Human-in-the-Loop)
CREATE TABLE IF NOT EXISTS pending_actions (
    id SERIAL PRIMARY KEY,
    proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    machine_name VARCHAR(64) NOT NULL REFERENCES machines(machine_name),
    proposed_action TEXT NOT NULL,
    parameter_value TEXT,
    reasoning TEXT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,
    execution_notes TEXT
);

-- 5. LLM Usage & Cost Ledger (Problem 2.5)
CREATE TABLE IF NOT EXISTS llm_cost_ledger (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    conversation_id VARCHAR(64) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    latency_ms NUMERIC(10, 2) NOT NULL,
    intent_detected VARCHAR(64),
    tools_called TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_cost_conv 
    ON llm_cost_ledger (conversation_id, timestamp);
