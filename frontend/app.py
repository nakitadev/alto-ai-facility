import streamlit as st
import requests
import json
import time
import os
import html
import pandas as pd
import altair as alt

# Backend API Configuration
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Somchai's Building AI Assistant | AltoTech Global",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- ZINC DESIGN SYSTEM (building-data-apps) -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..700;1,9..40,400..700&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {
        --bg: #09090b;
        --card: #121215;
        --card-hover: #18181c;
        --border: #27272a;
        --border-subtle: #1e1e24;
        --text: #fafafa;
        --text-muted: #a1a1aa;
        --text-dim: #71717a;
        --accent: #2563eb;
        --green: #22c55e;
        --green-muted: rgba(34, 197, 94, 0.12);
        --red: #ef4444;
        --red-muted: rgba(239, 68, 68, 0.12);
        --amber: #f59e0b;
        --amber-muted: rgba(245, 158, 11, 0.12);
        --radius: 10px;
    }

    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', -apple-system, sans-serif !important;
    }

    .main-header {
        font-size: 1.85rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin-bottom: 0.15rem;
    }
    .sub-header {
        color: var(--text-muted);
        font-size: 0.92rem;
        margin-bottom: 1.25rem;
    }

    /* KPI Metric Cards */
    .metric-card {
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1rem 1.25rem;
        transition: border-color 0.2s ease, background-color 0.2s ease;
    }
    .metric-card:hover {
        background-color: var(--card-hover);
        border-color: #3f3f46;
    }
    .metric-label {
        font-size: 0.76rem;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text);
        margin: 0.2rem 0;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-delta {
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 2px 7px;
        border-radius: 6px;
    }
    .delta-green { color: var(--green); background: var(--green-muted); }
    .delta-red { color: var(--red); background: var(--red-muted); }
    .delta-amber { color: var(--amber); background: var(--amber-muted); }

    /* Pill-Style Tabs */
    button[data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-muted) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 0.55rem 1.1rem !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        transition: all 0.15s ease-in-out !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: #18181b !important;
        border-color: var(--border) !important;
    }
    [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
        display: none !important;
    }
    [data-baseweb="tab-list"] {
        gap: 6px !important;
        background: #0f0f12 !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        padding: 4px;
        margin-bottom: 1.25rem;
    }

    /* Guard & Dual-Process Badges */
    .guard-badge {
        display: inline-block;
        background-color: var(--green-muted);
        color: var(--green);
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 3px 9px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .system2-badge {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 3px 9px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .tripwire-badge {
        display: inline-block;
        background-color: var(--red-muted);
        color: var(--red);
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 9px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-bottom: 6px;
    }

    /* Chart Containers */
    .chart-container {
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.1rem 1.25rem 0.5rem;
        margin-bottom: 1rem;
    }
    .chart-title {
        font-size: 0.88rem;
        font-weight: 600;
        color: var(--text);
    }
    .chart-subtitle {
        font-size: 0.74rem;
        color: var(--text-dim);
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- DATA FETCHING HELPERS -----------------
@st.cache_data(ttl=10)
def fetch_system_status():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=30)
def fetch_daily_energy():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/analytics/daily_energy", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("daily_energy", [])
    except Exception:
        pass
    return []

@st.cache_data(ttl=30)
def fetch_machine_breakdown():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/analytics/machine_breakdown", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("machines", [])
    except Exception:
        pass
    return []

# App Header
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown('<div class="main-header">🏢 Somchai\'s Facility AI Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Grounded HVAC Energy Intelligence & Safety Control · Bangkok Commercial Tower (UTC+7)</div>', unsafe_allow_html=True)

status_data = fetch_system_status()
with col_status:
    if status_data:
        sim_time = status_data.get("database", {}).get("simulated_now_bkk", "Day 7")
        st.success(f"🟢 TimescaleDB Online\nAnchor: {sim_time[:19]}")
    else:
        st.warning("⚠️ Backend Connecting...")

# ----------------- SIDEBAR: HITL & BENCHMARK SAMPLER -----------------
with st.sidebar:
    st.markdown("### ⚡ Facility Controls")

    # Quick-Sampler for Golden Questions (Appendix B)
    st.markdown("#### 🎯 Benchmark Queries")
    sample_questions = [
        "Which machine consumed the most energy on day 5, and how much?",
        "What was the building's total energy on day 2 compared with day 6?",
        "How much energy did AI control save compared with manual operation?",
        "What did the AI do between 22:00 on day 6 and 06:00 on day 7?",
        "Why did the AI turn off AC-S3 at 14:30 on day 4?",
        "What was the average lobby temperature during office hours on day 5?",
        "What is the humidity in the server room right now?",
        "How does this month's energy compare with last month?",
        "Which machines were running at 3 AM on day 3, and should they have been?",
        "Turn off AC-L2 now."
    ]
    selected_sample = st.selectbox("Load golden test query:", ["-- Select Query --"] + sample_questions)

    st.divider()

    # Problem 2.5: Usage and Cost Ledger
    st.markdown("#### 📊 LLM Cost Ledger")
    try:
        l_resp = requests.get(f"{BACKEND_URL}/api/ledger", timeout=3)
        if l_resp.status_code == 200:
            summary = l_resp.json().get("summary", {})
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total LLM Calls</div>
                <div class="metric-value">{summary.get('total_calls', 0)}</div>
                <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">
                    Tokens: {summary.get('total_tokens_in', 0) + summary.get('total_tokens_out', 0):,}<br>
                    Total Spend: <b>${summary.get('total_cost_usd', 0.0):.4f}</b><br>
                    Avg Latency: <b>{summary.get('avg_latency_ms', 0):.1f} ms</b><br>
                    Projected Mo: <b>${summary.get('projected_monthly_cost_usd', 0.0):.2f}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass

# ----------------- MAIN TABS LAYOUT -----------------
tab_console, tab_analytics, tab_safety = st.tabs([
    "💬 Operations Console & Assistant",
    "📊 Energy Telemetry & Analytics",
    "🛡️ Human-in-the-Loop Safety Queue"
])

# ----------------- TAB 1: OPERATIONS CONSOLE (SSE CHAT) -----------------
with tab_console:
    # Initialize message state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Sawadee krup Somchai! I'm your facility AI assistant. I have live access to the 12 building machines across Days 1–7. What would you like to investigate?"}
        ]

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("tripwire"):
                safe_guard = html.escape(str(msg["tripwire"]))
                s1_lat = msg.get("system1_latency_ms") or msg.get("latency_ms", 0.0)
                st.markdown(f'<div class="tripwire-badge">🛡️ System 1 Fast Tripwire: {safe_guard} ({s1_lat:.1f}ms)</div>', unsafe_allow_html=True)
            elif msg.get("role") == "assistant" and (msg.get("tools") is not None or msg.get("provider")):
                prov = html.escape(str(msg.get("provider", "Jev AI")))
                tool_cnt = len(msg.get("tools", []))
                s1_lat = msg.get("system1_latency_ms", 0.0)
                lat = msg.get("latency_ms", 0.0)
                s1_lat_str = f" · {s1_lat:.1f}ms" if s1_lat > 0 else ""
                st.markdown(
                    f'<div class="guard-badge">⚡ System 1 (TypeSafe): Passed ({prov}{s1_lat_str})</div> '
                    f'<div class="system2-badge">🧠 System 2: PydanticAI Grounded ({tool_cnt} tools · {lat:.1f}ms)</div>',
                    unsafe_allow_html=True
                )
            if "tools" in msg and msg["tools"]:
                with st.expander(f"🔍 Grounding Evidence ({len(msg['tools'])} tools inspected)", expanded=False):
                    for tc in msg["tools"]:
                        st.code(f"Tool: {tc.get('tool')}\nResult: {json.dumps(tc.get('result'), indent=2)}", language="json")
            st.markdown(msg["content"])

    # Chat Input
    user_input = st.chat_input("Ask a question about building energy, machines, AI actions, or policies...")
    if selected_sample != "-- Select Query --":
        user_input = selected_sample

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing building telemetry & grounding facts..."):
                badge_placeholder = st.empty()
                message_placeholder = st.empty()
                accumulated_text = ""
                tripwire = None
                tool_calls = []
                latency = 0.0
                provider = "Jev AI"

                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/api/chat/stream",
                        json={"message": user_input, "conversation_id": "somchai_console_ui"},
                        stream=True,
                        timeout=90
                    )
                    if resp.status_code == 200:
                        for line in resp.iter_lines():
                            if not line:
                                continue
                            line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                            if line_str.startswith("data: "):
                                payload_str = line_str[6:].strip()
                                if payload_str == "[DONE]":
                                    break
                                try:
                                    event = json.loads(payload_str)
                                    etype = event.get("type")
                                    if etype == "guard":
                                        tripwire = event.get("tripwire")
                                        guard_latency = event.get("latency_ms", 0.0)
                                        provider = html.escape(str(event.get("provider", "Jev AI")))
                                        if tripwire:
                                            safe_tripwire = html.escape(str(tripwire))
                                            badge_placeholder.markdown(f'<div class="tripwire-badge">🛡️ System 1 Fast Tripwire: {safe_tripwire} ({guard_latency:.1f}ms)</div>', unsafe_allow_html=True)
                                        else:
                                            badge_placeholder.markdown(
                                                f'<div class="guard-badge">⚡ System 1: Clean Path ({provider} · {guard_latency:.1f}ms)</div> '
                                                f'<div class="system2-badge">🧠 System 2: Deliberating & Querying Tools...</div>',
                                                unsafe_allow_html=True
                                            )
                                    elif etype == "token":
                                        accumulated_text += event.get("content", "")
                                        message_placeholder.markdown(accumulated_text + "▌")
                                    elif etype == "done":
                                        if "tool_calls" in event:
                                            tool_calls = event["tool_calls"]
                                        if "latency_ms" in event:
                                            latency = event["latency_ms"]
                                        s1_ms = event.get("system1_latency_ms", guard_latency)
                                        if not tripwire:
                                            badge_placeholder.markdown(
                                                f'<div class="guard-badge">⚡ System 1 (TypeSafe): Passed ({provider} · {s1_ms:.1f}ms)</div> '
                                                f'<div class="system2-badge">🧠 System 2: PydanticAI Grounded ({len(tool_calls)} tools · {latency:.1f}ms)</div>',
                                                unsafe_allow_html=True
                                            )
                                except Exception:
                                    pass

                        message_placeholder.markdown(accumulated_text)

                        if tool_calls:
                            with st.expander(f"🔍 Grounding Tool Inspections ({len(tool_calls)} calls)", expanded=True):
                                for tc in tool_calls:
                                    st.write(f"**Executed Tool**: `{tc.get('tool')}`")
                                    if "arguments" in tc:
                                        st.write(f"Arguments: `{json.dumps(tc.get('arguments'))}`")
                                    st.json(tc.get("result", {}))

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": accumulated_text,
                            "tools": tool_calls,
                            "tripwire": tripwire,
                            "provider": provider,
                            "system1_latency_ms": guard_latency,
                            "latency_ms": latency
                        })
                    else:
                        st.error(f"Backend returned error {resp.status_code}: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

# ----------------- TAB 2: ENERGY & TELEMETRY ANALYTICS -----------------
with tab_analytics:
    daily_data = fetch_daily_energy()
    machine_data = fetch_machine_breakdown()

    # KPI Top Row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Total Readings Tracked</div>
            <div class="metric-value">24,192</div>
            <div class="metric-delta delta-green">12 Machines Online</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Manual Baseline Mean (D1-D3)</div>
            <div class="metric-value">2,331.5</div>
            <div class="metric-delta delta-amber">kWh / day</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">AI Optimized Mean (D4-D7)</div>
            <div class="metric-value">1,598.2</div>
            <div class="metric-delta delta-green">kWh / day</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Net AI Energy Savings</div>
            <div class="metric-value">-31.5%</div>
            <div class="metric-delta delta-green">↓ 733.3 kWh/day saved</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Chart 1: Daily Energy Consumption (Altair)
    if daily_data:
        df_daily = pd.DataFrame(daily_data)
        df_daily["day_label"] = df_daily["day_num"].apply(lambda d: f"Day {d}")
        df_daily["Operation"] = df_daily["day_num"].apply(lambda d: "Manual Baseline" if d <= 3 else "AI Optimized")

        st.markdown("""
        <div class="chart-container">
            <div class="chart-title">Building Daily Electrical Energy Consumption (kWh)</div>
            <div class="chart-subtitle">TimescaleDB sensor_readings table · 5-minute interval power integration across Days 1 to 7</div>
        </div>
        """, unsafe_allow_html=True)

        chart_daily = alt.Chart(df_daily).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("day_label:N", title="Day", sort=None, axis=alt.Axis(labelColor="#a1a1aa", titleColor="#a1a1aa")),
            y=alt.Y("total_kwh:Q", title="Total Energy (kWh)", axis=alt.Axis(labelColor="#a1a1aa", titleColor="#a1a1aa")),
            color=alt.Color("Operation:N", scale=alt.Scale(domain=["Manual Baseline", "AI Optimized"], range=["#71717a", "#22c55e"])),
            tooltip=[alt.Tooltip("day_label:N", title="Day"), alt.Tooltip("total_kwh:Q", title="kWh", format=",.1f"), alt.Tooltip("Operation:N")]
        ).properties(height=280).configure_view(strokeOpacity=0).configure_axis(gridColor="#27272a")

        st.altair_chart(chart_daily, use_container_width=True)

    # Chart 2: Machine Breakdown
    if machine_data:
        df_mach = pd.DataFrame(machine_data)
        st.markdown("""
        <div class="chart-container">
            <div class="chart-title">7-Day Cumulative Energy Consumption by Equipment (kWh)</div>
            <div class="chart-subtitle">Ranked equipment consumption across Chillers (AC-L1 to L3), Split units (AC-S1 to S5), and Fans</div>
        </div>
        """, unsafe_allow_html=True)

        chart_mach = alt.Chart(df_mach).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
            y=alt.Y("machine_name:N", title="Equipment", sort="-x", axis=alt.Axis(labelColor="#a1a1aa", titleColor="#a1a1aa")),
            x=alt.X("total_kwh:Q", title="Cumulative Energy (kWh)", axis=alt.Axis(labelColor="#a1a1aa", titleColor="#a1a1aa")),
            color=alt.value("#3b82f6"),
            tooltip=[alt.Tooltip("machine_name:N", title="Equipment"), alt.Tooltip("total_kwh:Q", title="kWh", format=",.1f")]
        ).properties(height=320).configure_view(strokeOpacity=0).configure_axis(gridColor="#27272a")

        st.altair_chart(chart_mach, use_container_width=True)

# ----------------- TAB 3: HUMAN-IN-THE-LOOP SAFETY QUEUE -----------------
with tab_safety:
    st.markdown("### 🛡️ Human-in-the-Loop Machine Control Queue")
    st.caption("Enforcing Propose-Only actuation: Physical hardware control requires verified operator authorization.")

    try:
        p_resp = requests.get(f"{BACKEND_URL}/api/pending_actions", timeout=3)
        if p_resp.status_code == 200:
            actions_list = p_resp.json().get("pending_actions", [])
            pending_items = [p for p in actions_list if p["status"] == "PENDING"]
            reviewed_items = [p for p in actions_list if p["status"] != "PENDING"]

            st.write(f"**Awaiting Authorization**: `{len(pending_items)}` proposals | **Historical Audited**: `{len(reviewed_items)}` actions")

            if not pending_items:
                st.info("No pending machine proposals currently awaiting operator review.")
            else:
                for p in pending_items[:10]:
                    with st.expander(f"Proposal #{p['id']}: {p['proposed_action']} {p['machine_name']}", expanded=True):
                        col_info, col_act = st.columns([3, 1])
                        with col_info:
                            st.write(f"**Target Equipment**: `{p['machine_name']}`")
                            st.write(f"**Proposed Actuation**: `{p['proposed_action']}`")
                            st.write(f"**Reasoning / Trigger**: {p['reasoning']}")
                            st.caption(f"Proposed At: {p.get('proposed_at', 'N/A')}")
                        with col_act:
                            if st.button("✔ Approve", key=f"tab_app_{p['id']}", use_container_width=True):
                                requests.post(f"{BACKEND_URL}/api/pending_actions/{p['id']}/approve", json={"reviewer_name": "Somchai"})
                                st.success("Approved!")
                                st.rerun()
                            if st.button("✖ Reject", key=f"tab_rej_{p['id']}", use_container_width=True):
                                requests.post(f"{BACKEND_URL}/api/pending_actions/{p['id']}/reject", json={"reviewer_name": "Somchai"})
                                st.warning("Rejected.")
                                st.rerun()

            if reviewed_items:
                st.write("---")
                st.markdown("#### Recent Action Audit Trail")
                df_rev = pd.DataFrame(reviewed_items[:15])
                st.dataframe(
                    df_rev[["id", "machine_name", "proposed_action", "status", "reviewed_by", "reviewed_at"]],
                    use_container_width=True,
                    hide_index=True
                )
    except Exception as e:
        st.error(f"Failed to fetch pending actions: {e}")
