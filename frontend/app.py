import streamlit as st
import requests
import json
import os
import html
import uuid
import pandas as pd

# Backend API Configuration
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Somchai's Building AI Assistant | AltoTech Global",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- CLEAN ZINC STYLING -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {
        --bg: #09090b;
        --card: #121215;
        --border: #27272a;
        --text: #fafafa;
        --text-muted: #a1a1aa;
        --accent: #2563eb;
        --green: #22c55e;
        --green-muted: rgba(34, 197, 94, 0.12);
        --red: #ef4444;
        --red-muted: rgba(239, 68, 68, 0.12);
    }

    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', -apple-system, sans-serif !important;
    }

    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin-bottom: 0.15rem;
    }
    .sub-header {
        color: var(--text-muted);
        font-size: 0.9rem;
        margin-bottom: 1.25rem;
    }

    .metric-card {
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.85rem 1rem;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text);
        margin: 0.2rem 0;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Badges */
    .guard-badge {
        display: inline-block;
        background-color: var(--green-muted);
        color: var(--green);
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .system2-badge {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .tripwire-badge {
        display: inline-block;
        background-color: var(--red-muted);
        color: var(--red);
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-bottom: 6px;
    }

    /* Padding so fixed bottom chat input never covers message content */
    .main .block-container {
        padding-bottom: 7rem !important;
    }
    [data-testid="stBottom"] {
        background-color: var(--bg) !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- BACKEND STATUS -----------------
@st.cache_data(ttl=10)
def fetch_system_status():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=60)
def fetch_available_models():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/models", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {
        "models": [
            {"id": "inclusionai/ling-3.0-flash-sante:free", "name": "Ling 3.0 Flash (Default · Ultra-Fast)", "context_length": "256k"},
            {"id": "nvidia/nemotron-3.5-lightning:free", "name": "NVIDIA Nemotron 3.5 Lightning (High Precision)", "context_length": "1,000k"},
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "NVIDIA Nemotron 3 Ultra 550B (Deep Reasoning)", "context_length": "1,000k"},
            {"id": "google/gemma-4-31b-it:free", "name": "Google Gemma 4 31B Instruct", "context_length": "262k"},
            {"id": "qwen/qwen3.8-27b:free", "name": "Qwen 3.8 27B Instruct", "context_length": "262k"},
            {"id": "openrouter/free", "name": "OpenRouter Auto-Free Router", "context_length": "200k"}
        ],
        "default": "inclusionai/ling-3.0-flash-sante:free"
    }

# App Header
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown('<div class="main-header">🏢 Somchai\'s Facility AI Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Grounded HVAC Energy Intelligence & Safety Control · Bangkok Commercial Tower (UTC+7)</div>', unsafe_allow_html=True)

status_data = fetch_system_status()
with col_status:
    if status_data and status_data.get("database", {}).get("has_data"):
        sim_time = status_data["database"].get("current_time_bkk") or status_data["database"].get("simulated_now_bkk", "Live")
        st.success(f"🟢 Database Connected\nTime: {sim_time[:19]}")
    else:
        st.warning("⚠️ Connecting to Database...")

# ----------------- SIDEBAR -----------------
with st.sidebar:
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = f"session_{uuid.uuid4().hex[:8]}"

    col_btn, col_info = st.columns([2, 1])
    if st.button("➕ New Chat Session", use_container_width=True):
        if "conversation_id" in st.session_state:
            try:
                requests.post(
                    f"{BACKEND_URL}/api/chat/reset",
                    json={"conversation_id": st.session_state.conversation_id},
                    timeout=3
                )
            except Exception:
                pass
        st.session_state.conversation_id = f"session_{uuid.uuid4().hex[:8]}"
        st.session_state.messages = [
            {"role": "assistant", "content": "Sawadee krup Somchai! I'm your facility AI assistant for Bangkok Commercial Tower. How can I assist with building HVAC telemetry, energy consumption, or operating policies today?"}
        ]
        st.session_state.last_sample = None
        st.rerun()

    st.caption(f"Active Session: `{st.session_state.conversation_id}`")
    st.divider()

    # OpenRouter Free Model Selector
    st.markdown("### 🤖 OpenRouter Model (Free)")
    models_data = fetch_available_models()
    model_list = models_data.get("models", [])
    model_options = {m["name"]: m["id"] for m in model_list}
    default_id = models_data.get("default", "inclusionai/ling-3.0-flash-sante:free")
    
    default_name = next((k for k, v in model_options.items() if v == default_id), list(model_options.keys())[0] if model_options else "Default")
    default_idx = list(model_options.keys()).index(default_name) if default_name in model_options else 0

    selected_model_name = st.selectbox(
        "Active Free Model:",
        options=list(model_options.keys()),
        index=default_idx,
        help="All models are 100% verified Free Tier on OpenRouter supporting function calling."
    )
    selected_model_id = model_options.get(selected_model_name, default_id)
    st.session_state.selected_model = selected_model_id
    st.caption(f"Endpoint: `{selected_model_id}` · Free Tier 🟢")
    st.divider()

    st.markdown("### ⚡ Benchmark Queries")
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
    selected_sample = st.selectbox("Load golden test question:", ["-- Select Query --"] + sample_questions)

    st.divider()

    # Problem 2.5: Usage and Cost Ledger
    st.markdown("### 📊 Cost & Usage Ledger")
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
                    Total Cost: <b>${summary.get('total_cost_usd', 0.0):.4f}</b><br>
                    Avg Latency: <b>{summary.get('avg_latency_ms', 0):.1f} ms</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass

# ----------------- MAIN TABS -----------------
tab_console, tab_safety = st.tabs([
    "💬 Operations Console",
    "🛡️ Human-in-the-Loop Safety Queue"
])

# ----------------- TAB 1: OPERATIONS CONSOLE -----------------
with tab_console:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Sawadee krup Somchai! I'm your facility AI assistant for Bangkok Commercial Tower. How can I assist with building HVAC telemetry, energy consumption, or operating policies today?"}
        ]

    if "last_sample" not in st.session_state:
        st.session_state.last_sample = None

    chat_container = st.container()

    user_input = st.chat_input("Ask about facility energy, machines, temperatures, or AI actions...")
    if selected_sample != "-- Select Query --" and selected_sample != st.session_state.last_sample:
        user_input = selected_sample
        st.session_state.last_sample = selected_sample

    with chat_container:
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
                    raw_model = msg.get("model_name", "OpenRouter Free")
                    model_label = html.escape(raw_model.split("/")[-1] if "/" in raw_model else raw_model)
                    st.markdown(
                        f'<div class="guard-badge">⚡ System 1: Clean Path ({prov}{s1_lat_str})</div> '
                        f'<div class="system2-badge">🧠 System 2: Grounded ({model_label} · {tool_cnt} tools · {lat:.1f}ms)</div>',
                        unsafe_allow_html=True
                    )
                if "tools" in msg and msg["tools"]:
                    with st.expander(f"🔍 Grounding Evidence ({len(msg['tools'])} database queries inspected)", expanded=False):
                        for tc in msg["tools"]:
                            st.markdown(f"**🔧 Executed Tool**: `{tc.get('tool')}`")
                            if tc.get("arguments"):
                                st.caption("Database Query Parameters:")
                                st.json(tc.get("arguments"))
                            if tc.get("result"):
                                st.caption("TimescaleDB Ground Truth Telemetry:")
                                st.json(tc.get("result"))
                st.markdown(msg["content"])

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Connecting to TimescaleDB & grounding facts..."):
                    badge_placeholder = st.empty()
                    message_placeholder = st.empty()
                    accumulated_text = ""
                    tripwire = None
                    tool_calls = []
                    latency = 0.0
                    provider = "Jev AI"
                    guard_latency = 0.0
                    chosen_model = st.session_state.get("selected_model")
                    active_model = chosen_model

                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/api/chat",
                            json={
                                "message": user_input,
                                "conversation_id": st.session_state.conversation_id,
                                "model": chosen_model
                            },
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
                                                    f'<div class="system2-badge">🧠 System 2: Deliberating & Inspecting Database...</div>',
                                                    unsafe_allow_html=True
                                                )
                                        elif etype == "tool_call":
                                            tool_name = html.escape(str(event.get("tool", "tool")))
                                            if tool_name == "deliberating":
                                                badge_placeholder.markdown(
                                                    f'<div class="guard-badge">⚡ System 1: Clean Path ({provider} · {guard_latency:.1f}ms)</div> '
                                                    f'<div class="system2-badge">🧠 System 2: Inspecting Database Constraints...</div>',
                                                    unsafe_allow_html=True
                                                )
                                            else:
                                                badge_placeholder.markdown(
                                                    f'<div class="guard-badge">⚡ System 1: Clean Path ({provider} · {guard_latency:.1f}ms)</div> '
                                                    f'<div class="system2-badge">🔧 Querying TimescaleDB: <b>{tool_name}</b>...</div>',
                                                    unsafe_allow_html=True
                                                )
                                        elif etype == "tool_result":
                                            tool_name = html.escape(str(event.get("tool", "tool")))
                                            badge_placeholder.markdown(
                                                f'<div class="guard-badge">⚡ System 1: Clean Path ({provider} · {guard_latency:.1f}ms)</div> '
                                                f'<div class="system2-badge">📊 {tool_name} Telemetry Retrieved · Formulating Answer...</div>',
                                                unsafe_allow_html=True
                                            )
                                        elif etype == "token":
                                            accumulated_text += event.get("content", "")
                                            message_placeholder.markdown(accumulated_text + "▌")
                                        elif etype == "done":
                                            tool_calls = event.get("tool_calls", [])
                                            latency = event.get("latency_ms", 0.0)
                                            active_model = event.get("model_name") or chosen_model or "OpenRouter Free"
                                            short_model = html.escape(active_model.split("/")[-1] if "/" in active_model else active_model)
                                            if not tripwire:
                                                badge_placeholder.markdown(
                                                    f'<div class="guard-badge">⚡ System 1: Clean Path ({provider} · {guard_latency:.1f}ms)</div> '
                                                    f'<div class="system2-badge">🧠 System 2: Grounded ({short_model} · {len(tool_calls)} tools · {latency:.1f}ms)</div>',
                                                    unsafe_allow_html=True
                                                )
                                    except Exception:
                                        pass

                            message_placeholder.markdown(accumulated_text)

                            if tool_calls:
                                with st.expander(f"🔍 Grounding Evidence ({len(tool_calls)} database queries inspected)", expanded=True):
                                    for tc in tool_calls:
                                        st.markdown(f"**🔧 Executed Tool**: `{tc.get('tool')}`")
                                        if tc.get("arguments"):
                                            st.caption("Database Query Parameters:")
                                            st.json(tc.get("arguments"))
                                        if tc.get("result"):
                                            st.caption("TimescaleDB Ground Truth Telemetry:")
                                            st.json(tc.get("result"))

                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": accumulated_text,
                                "tools": tool_calls,
                                "tripwire": tripwire,
                                "provider": provider,
                                "model_name": active_model if not tripwire else provider,
                                "system1_latency_ms": guard_latency,
                                "latency_ms": latency
                            })
                        else:
                            st.error(f"Backend returned error {resp.status_code}: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to backend: {e}")

# ----------------- TAB 2: HUMAN-IN-THE-LOOP SAFETY QUEUE (Problem 3 Option A) -----------------
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
