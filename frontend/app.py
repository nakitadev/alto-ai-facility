import streamlit as st
import requests
import json
import time
import os

# Backend API Configuration
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Somchai's Building AI Assistant | AltoTech Global",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Sleek Dark Terminal Aesthetic
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #8892b0;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e222d;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .guard-badge {
        display: inline-block;
        background-color: #1f3a2f;
        color: #4ade80;
        border: 1px solid #166534;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .tripwire-badge {
        display: inline-block;
        background-color: #3b1d22;
        color: #f87171;
        border: 1px solid #991b1b;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# App Title & Status
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown('<div class="main-header">🏢 Somchai\'s Facility AI Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Grounded HVAC Energy Intelligence & Safety Control · Bangkok Commercial Tower (UTC+7)</div>', unsafe_allow_html=True)

# Fetch backend health
@st.cache_data(ttl=10)
def fetch_system_status():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

status_data = fetch_system_status()
with col_status:
    if status_data:
        sim_time = status_data.get("database", {}).get("simulated_now_bkk", "Day 7")
        st.success(f"🟢 Connected to TimescaleDB\nAnchor: {sim_time[:19]}")
    else:
        st.warning("⚠️ Backend Connecting...")

# ----------------- SIDEBAR: AUDIT LEDGER & HUMAN-IN-THE-LOOP -----------------
with st.sidebar:
    st.header("⚡ System Control Panel")
    
    # 1. Problem 3 Option A: Pending Control Actions (Human In The Loop)
    st.subheader("🛡️ Pending Machine Actions (HITL)")
    st.caption("Read-only guarantee: Proposals require human authorization.")
    
    try:
        p_resp = requests.get(f"{BACKEND_URL}/api/pending_actions", timeout=3)
        if p_resp.status_code == 200:
            pending_list = [p for p in p_resp.json().get("pending_actions", []) if p["status"] == "PENDING"]
            if not pending_list:
                st.info("No pending proposals awaiting review.")
            else:
                for p in pending_list:
                    with st.expander(f"Proposal #{p['id']}: {p['proposed_action']} {p['machine_name']}", expanded=True):
                        st.write(f"**Action**: `{p['proposed_action']}`")
                        st.write(f"**Target Machine**: `{p['machine_name']}`")
                        st.write(f"**Reasoning**: {p['reasoning']}")
                        
                        col_app, col_rej = st.columns(2)
                        with col_app:
                            if st.button("✔ Approve", key=f"app_{p['id']}"):
                                requests.post(f"{BACKEND_URL}/api/pending_actions/{p['id']}/approve", json={"reviewer_name": "Somchai"})
                                st.success("Action Approved!")
                                st.rerun()
                        with col_rej:
                            if st.button("✖ Reject", key=f"rej_{p['id']}"):
                                requests.post(f"{BACKEND_URL}/api/pending_actions/{p['id']}/reject", json={"reviewer_name": "Somchai"})
                                st.warning("Action Rejected.")
                                st.rerun()
    except Exception as e:
        st.caption(f"Pending actions queue offline: {e}")

    st.divider()

    # 2. Problem 2.5: Usage and Cost Ledger
    st.subheader("📊 LLM Cost Ledger")
    try:
        l_resp = requests.get(f"{BACKEND_URL}/api/ledger", timeout=3)
        if l_resp.status_code == 200:
            summary = l_resp.json().get("summary", {})
            st.markdown(f"""
            <div class="metric-card">
                <b>Total Calls:</b> {summary.get('total_calls', 0)}<br>
                <b>Total Tokens:</b> {summary.get('total_tokens_in', 0) + summary.get('total_tokens_out', 0):,}<br>
                <b>Total Spend:</b> ${summary.get('total_cost_usd', 0.0):.4f}<br>
                <b>Avg Latency:</b> {summary.get('avg_latency_ms', 0):.1f} ms<br>
                <b>Projected Monthly:</b> ${summary.get('projected_monthly_cost_usd', 0.0):.2f}
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass

    st.divider()

    # 3. Quick-Sampler for Golden Questions (Appendix B)
    st.subheader("🎯 Test Golden Questions")
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
    selected_sample = st.selectbox("Select a benchmark query:", ["-- Select --"] + sample_questions)

# ----------------- MAIN CHAT CONSOLE -----------------

# Initialize message state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Sawadee krup Somchai! I'm your facility AI assistant. I have live access to the 12 building machines across Days 1–7. What would you like to investigate?"}
    ]

# Render existing chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "guard" in msg and msg["guard"]:
            st.markdown(f'<div class="guard-badge">🛡️ System 1 Guard: {msg["guard"]}</div>', unsafe_allow_html=True)
        if "tools" in msg and msg["tools"]:
            with st.expander(f"🔍 Grounding Evidence ({len(msg['tools'])} tools inspected)", expanded=False):
                for tc in msg["tools"]:
                    st.code(f"Tool: {tc.get('tool')}\nResult: {json.dumps(tc.get('result'), indent=2)}", language="json")
        st.markdown(msg["content"])

# User Input Handling
user_input = st.chat_input("Ask a question about building energy, machines, AI actions, or policies...")

# If quick sample selected
if selected_sample != "-- Select --":
    user_input = selected_sample

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Process via Backend
    with st.chat_message("assistant"):
        with st.spinner("Analyzing building telemetry & grounding facts..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/api/chat",
                    json={"message": user_input, "conversation_id": "somchai_console_ui"},
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer_text = data.get("response", "")
                    tool_calls = data.get("tool_calls", [])
                    tripwire = data.get("guard_tripwire")
                    latency = data.get("latency_ms", 0)

                    # Show System 1 Guard badge
                    if tripwire:
                        st.markdown(f'<div class="tripwire-badge">🛡️ System 1 Tripwire: {tripwire} ({latency:.1f}ms)</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="guard-badge">⚡ System 1 Routed · Latency: {latency:.1f}ms</div>', unsafe_allow_html=True)

                    # Show Tool Inspector (Transparency requirement)
                    if tool_calls:
                        with st.expander(f"🔍 Grounding Tool Inspections ({len(tool_calls)} calls)", expanded=True):
                            for tc in tool_calls:
                                st.write(f"**Executed Tool**: `{tc.get('tool')}`")
                                if "arguments" in tc:
                                    st.write(f"Arguments: `{json.dumps(tc.get('arguments'))}`")
                                st.json(tc.get("result", {}))

                    # Display streaming / rendered text
                    message_placeholder = st.empty()
                    # Simulate smooth streaming for UX
                    displayed = ""
                    for chunk in answer_text.split(" "):
                        displayed += chunk + " "
                        message_placeholder.markdown(displayed + "▌")
                        time.sleep(0.015)
                    message_placeholder.markdown(answer_text)

                    # Save to state
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer_text,
                        "tools": tool_calls,
                        "guard": tripwire
                    })
                else:
                    st.error(f"Backend returned error {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")
