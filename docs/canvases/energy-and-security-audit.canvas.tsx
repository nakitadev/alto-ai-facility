import {
  Stack,
  Row,
  Grid,
  Text,
  H1,
  H2,
  H3,
  Code,
  Card,
  CardHeader,
  CardBody,
  Stat,
  Table,
  Callout,
  BarChart,
  useHostTheme
} from "cursor/canvas";

export default function EnergyAndSecurityAuditCanvas() {
  const theme = useHostTheme();

  const dailyCategories = [
    "Day 1 (Manual)",
    "Day 2 (Manual)",
    "Day 3 (Manual)",
    "Day 4 (AI Active)",
    "Day 5 (AI Active)",
    "Day 6 (AI Active)",
    "Day 7 (AI Active)"
  ];

  const dailyEnergySeries = [
    {
      name: "Actual Energy Consumed (kWh)",
      data: [2345.3, 2347.6, 2301.5, 1632.3, 1631.3, 1631.4, 1497.7],
      tone: "info" as const
    }
  ];

  const machineCategories = [
    "AC-L1 (Lobby)",
    "AC-L2 (Fl 1-3)",
    "AC-L3 (Fl 4-6)",
    "AC-S5 (Server)",
    "AC-S1 (Fl 1)",
    "AC-S2 (Fl 2)",
    "AC-S3 (Meeting)",
    "AC-S4 (Exec)",
    "FAN-01 (Basement)",
    "FAN-03 (Vent)",
    "FAN-04 (Vent)",
    "FAN-02 (Stair)"
  ];

  const machineEnergySeries = [
    {
      name: "7-Day Cumulative Energy (kWh)",
      data: [3307.5, 2716.2, 2709.7, 1436.9, 610.4, 610.1, 549.5, 509.2, 480.4, 220.7, 220.7, 193.1],
      tone: "info" as const
    }
  ];

  const securityHeaders = [
    "Severity",
    "Location",
    "Component",
    "Vulnerability Finding",
    "Mitigation Strategy"
  ];

  const securityRows = [
    [
      <Text key="h1" tone="danger" weight={600}>HIGH</Text>,
      <Code key="h2">docker-compose.yml:28,58</Code>,
      <Text key="h3">TimescaleDB Container</Text>,
      <Text key="h4">Default postgres:postgres credentials and port 5432 exposed to 0.0.0.0 host network.</Text>,
      <Text key="h5">Bind to 127.0.0.1:5432 or keep internal to Docker network; enforce non-default .env secret.</Text>
    ],
    [
      <Text key="m1" tone="warning" weight={600}>MEDIUM</Text>,
      <Code key="m2">backend/main.py:38-43</Code>,
      <Text key="m3">FastAPI ASGI Middleware</Text>,
      <Text key="m4">Permissive CORS with wildcard origins (allow_origins=["*"]) enabled alongside credentials.</Text>,
      <Text key="m5">Restrict origins explicitly to trusted frontend origin (http://localhost:8501).</Text>
    ],
    [
      <Text key="m21" tone="warning" weight={600}>MEDIUM</Text>,
      <Code key="m22">backend/system1/guard.py:212</Code>,
      <Text key="m23">Jev System 1 Fallback</Text>,
      <Text key="m24">Calibrated local regex can be bypassed by paraphrasing or multilingual prompt injection.</Text>,
      <Text key="m25">Prioritize live TypeSafe Jev API; expand semantic token boundary defense.</Text>
    ],
    [
      <Text key="l1" tone="neutral" weight={600}>LOW</Text>,
      <Code key="l2">frontend/app.py:178,232</Code>,
      <Text key="l3">Streamlit UI Badges</Text>,
      <Text key="l4">unsafe_allow_html=True used with interpolated strings; risk if unvalidated text is passed.</Text>,
      <Text key="l5">Escape dynamic strings with html.escape() before inserting into custom badge HTML.</Text>
    ],
    [
      <Text key="l21" tone="neutral" weight={600}>LOW</Text>,
      <Code key="l22">backend/main.py:79,94</Code>,
      <Text key="l23">Chat API Endpoints</Text>,
      <Text key="l24">Missing rate limiting and input length bounds; susceptible to Denial of Wallet (DoW) token exhaustion.</Text>,
      <Text key="l25">Apply max length validation (e.g. 2,000 chars) and IP rate limiting (slowapi).</Text>
    ]
  ];

  const safetyHeaders = [
    "Proposal ID",
    "Target Equipment",
    "Proposed Actuation",
    "Triggering Reason",
    "Enforcement Model"
  ];

  const safetyRows = [
    [
      <Text key="p1">#101</Text>,
      <Code key="p2">AC-L2</Code>,
      <Text key="p3" tone="warning" weight={600}>TURN OFF</Text>,
      <Text key="p4">Operator prompt: "Turn off AC-L2 now."</Text>,
      <Text key="p5" tone="success">HITL Approval Required (Propose-Only)</Text>
    ],
    [
      <Text key="p6">#102</Text>,
      <Code key="p7">AC-S5</Code>,
      <Text key="p8" tone="danger" weight={600}>BLOCKED (24/7 CRITICAL)</Text>,
      <Text key="p9">Server room shutdown attempted; rule prohibits shutdown.</Text>,
      <Text key="p10" tone="danger">Hard Tripwire Intercept</Text>
    ],
    [
      <Text key="p11">#103</Text>,
      <Code key="p12">AC-S3</Code>,
      <Text key="p13" tone="info" weight={600}>OPTIMIZE SETPOINT (24.0°C)</Text>,
      <Text key="p14">Pre-cooling schedule before 14:00 peak occupancy.</Text>,
      <Text key="p15" tone="success">Logged in Pending Queue</Text>
    ]
  ];

  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <div>
        <H1>AltoTech HVAC Energy & Security Operations Console</H1>
        <Text tone="secondary">
          Commercial Tower Facility AI Intelligence · Bangkok (UTC+7) · 7-Day Telemetry Grounding
        </Text>
      </div>

      {/* Top Level KPIs */}
      <Grid columns={4} gap={16}>
        <Card>
          <CardBody>
            <Stat
              label="Total Telemetry Readings"
              value="24,192"
              tone="info"
            />
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat
              label="Manual Baseline (Days 1–3)"
              value="2,331.5 kWh/d"
            />
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat
              label="AI Optimized (Days 4–7)"
              value="1,598.2 kWh/d"
              tone="success"
            />
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat
              label="Net Efficiency Savings"
              value="-31.5% (-733 kWh/d)"
              tone="success"
            />
          </CardBody>
        </Card>
      </Grid>

      {/* Primary Analytics Section */}
      <Card>
        <CardHeader>
          <div>
            <H2>Building Daily Electrical Energy Consumption</H2>
            <Text size="small" tone="secondary">
              Source: TimescaleDB sensor_readings table (5-minute interval power_kw integration) · Days 1 to 7
            </Text>
          </div>
        </CardHeader>
        <CardBody>
          <BarChart
            categories={dailyCategories}
            series={dailyEnergySeries}
            valueSuffix=" kWh"
            height={260}
            referenceLines={[
              { value: 2331.5, label: "Baseline Mean: 2,331.5 kWh", tone: "neutral" },
              { value: 1598.2, label: "AI Target Mean: 1,598.2 kWh", tone: "success" }
            ]}
          />
        </CardBody>
      </Card>

      {/* Machine Breakdown */}
      <Card>
        <CardHeader>
          <div>
            <H2>Cumulative Equipment Energy Breakdown</H2>
            <Text size="small" tone="secondary">
              Ranked consumption across all 12 monitored HVAC units and ventilation fans
            </Text>
          </div>
        </CardHeader>
        <CardBody>
          <BarChart
            categories={machineCategories}
            series={machineEnergySeries}
            horizontal={true}
            valueSuffix=" kWh"
            height={320}
          />
        </CardBody>
      </Card>

      {/* Human In The Loop Safety Queue */}
      <Card>
        <CardHeader>
          <div>
            <H2>Human-in-the-Loop Safety Queue (Problem 3 Option A)</H2>
            <Text size="small" tone="secondary">
              All write actions are intercepted by System 1 and require human authorization before actuation
            </Text>
          </div>
        </CardHeader>
        <CardBody style={{ padding: 0 }}>
          <Table
            headers={safetyHeaders}
            rows={safetyRows}
            striped={true}
          />
        </CardBody>
      </Card>

      {/* Security Review Findings */}
      <Card>
        <CardHeader>
          <div>
            <H2>Security Posture & Vulnerability Audit</H2>
            <Text size="small" tone="secondary">
              Static and runtime vulnerability analysis across container, API gateway, and guardrail boundaries
            </Text>
          </div>
        </CardHeader>
        <CardBody style={{ padding: 0 }}>
          <Table
            headers={securityHeaders}
            rows={securityRows}
            striped={true}
          />
        </CardBody>
      </Card>

      {/* Architectural Guarantee Summary */}
      <Callout tone="info" title="Dual-Process System 1 + System 2 Reliability Guarantee">
        Direct physical hardware control is strictly prohibited in software. All user actuation commands are captured into the PostgreSQL pending_actions ledger with audit timestamps. Operational telemetry queries are computed deterministically over TimescaleDB with zero synthetic hallucination.
      </Callout>
    </Stack>
  );
}
