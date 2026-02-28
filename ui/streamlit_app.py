import uuid

import httpx
import streamlit as st

# Configuration
API_BASE_URL = "http://localhost:8000/api"

st.set_page_config(
    page_title="AgentForge Healthcare AI",
    page_icon="🏥",
    layout="centered",
)

# ── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* ── Global ── */
    .stApp {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* ── Full-page watermark logo (center) ── */
    .stApp::before {
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 75vw;
        height: 60vh;
        pointer-events: none;
        z-index: 0;
        opacity: 0.04;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 220'%3E%3Cdefs%3E%3ClinearGradient id='wm' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0%25' stop-color='%230ea5e9'/%3E%3Cstop offset='100%25' stop-color='%2338bdf8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Ctext x='300' y='110' text-anchor='middle' font-family='Inter,system-ui,sans-serif' font-weight='900' font-size='82' fill='url(%23wm)' letter-spacing='-2'%3EAGENTFORGE%3C/text%3E%3Ctext x='300' y='175' text-anchor='middle' font-family='Inter,system-ui,sans-serif' font-weight='600' font-size='32' fill='%230ea5e9' letter-spacing='10'%3EHEALTHCARE AI%3C/text%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
    }
    /* ── Gauntlet AI G4 badge (bottom-right) ── */
    .stApp::after {
        content: "";
        position: fixed;
        bottom: 18px;
        right: 22px;
        width: 140px;
        height: 52px;
        pointer-events: none;
        z-index: 0;
        opacity: 0.10;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 260 70'%3E%3Ctext x='8' y='32' font-family='Inter,system-ui,sans-serif' font-weight='800' font-size='18' fill='%230ea5e9' letter-spacing='3'%3EGAUNTLET AI%3C/text%3E%3Crect x='8' y='42' width='56' height='24' rx='12' fill='none' stroke='%230ea5e9' stroke-width='2'/%3E%3Ctext x='36' y='60' text-anchor='middle' font-family='Inter,system-ui,sans-serif' font-weight='900' font-size='16' fill='%230ea5e9'%3EG4%3C/text%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
    }

    /* ── Tighter spacing ── */
    .stMainBlockContainer { padding-top: 1rem; }

    /* ── Animated gradient header ── */
    @keyframes headerShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .af-header {
        background: linear-gradient(135deg, #0c1220 0%, #0f2847 25%, #0c1e3a 50%, #112240 75%, #0c1220 100%);
        background-size: 400% 400%;
        animation: headerShift 12s ease infinite;
        border: 1px solid rgba(14,165,233,0.2);
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 0.75rem;
        position: relative;
        overflow: hidden;
    }
    .af-header::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(ellipse at 20% 50%, rgba(14,165,233,0.08) 0%, transparent 60%);
        pointer-events: none;
    }
    .af-header h1 {
        margin: 0 0 0.2rem 0;
        font-size: 1.7rem;
        font-weight: 800;
        background: linear-gradient(135deg, #e2e8f0, #f8fafc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.03em;
    }
    .af-header .af-tagline {
        font-size: 0.82rem;
        color: #64748b;
        margin: 0 0 0.65rem 0;
        font-weight: 500;
        letter-spacing: 0.01em;
    }
    .af-badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
    }
    .af-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(14,165,233,0.08);
        color: #38bdf8;
        border: 1px solid rgba(14,165,233,0.18);
        border-radius: 999px;
        padding: 0.2rem 0.65rem;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        backdrop-filter: blur(4px);
    }
    .af-badge .af-badge-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #0ea5e9;
        box-shadow: 0 0 6px rgba(14,165,233,0.6);
    }

    /* ── Example question cards ── */
    .af-examples-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.55rem;
        margin: 0.5rem 0 1rem 0;
    }
    .af-example-card {
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(14,165,233,0.12);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        cursor: pointer;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .af-example-card:hover {
        border-color: rgba(14,165,233,0.45);
        background: rgba(15,23,42,0.7);
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(14,165,233,0.1);
    }
    .af-example-card::after {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 0% 0%, rgba(14,165,233,0.06) 0%, transparent 50%);
        pointer-events: none;
    }
    .af-example-icon {
        font-size: 1.1rem;
        margin-bottom: 0.25rem;
    }
    .af-example-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.15rem;
    }
    .af-example-text {
        font-size: 0.82rem;
        color: #94a3b8;
        line-height: 1.35;
    }

    /* ── Override Streamlit buttons to look like our cards ── */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        border: 1px solid rgba(14,165,233,0.15);
        border-radius: 12px;
        transition: all 0.25s ease;
        text-align: left;
        font-size: 0.82rem;
        padding: 0.7rem 0.9rem;
        background: rgba(15,23,42,0.4);
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        border-color: rgba(14,165,233,0.5);
        background: rgba(14,165,233,0.06);
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(14,165,233,0.08);
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(14,165,233,0.08);
        background: linear-gradient(180deg, rgba(12,18,32,0.95) 0%, rgba(15,23,42,0.95) 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        opacity: 0.5;
        margin-bottom: 0.4rem;
        font-weight: 700;
    }
    .af-sidebar-section {
        background: rgba(14,165,233,0.04);
        border: 1px solid rgba(14,165,233,0.08);
        border-radius: 10px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .af-tool-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.3rem;
    }
    .af-tool-chip {
        font-size: 0.68rem;
        color: #94a3b8;
        background: rgba(14,165,233,0.06);
        border: 1px solid rgba(14,165,233,0.1);
        border-radius: 6px;
        padding: 0.25rem 0.5rem;
        text-align: center;
        font-weight: 500;
    }
    .af-tool-chip.af-bounty {
        color: #fbbf24;
        background: rgba(251,191,36,0.06);
        border-color: rgba(251,191,36,0.15);
    }

    /* ── Sidebar metrics ── */
    div[data-testid="stMetricValue"] { font-size: 1.2rem; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.68rem; opacity: 0.6; font-weight: 600; }

    /* ── Tool usage bars ── */
    .af-tool-bar-row {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-bottom: 0.3rem;
        font-size: 0.68rem;
    }
    .af-tool-bar-label {
        min-width: 80px;
        color: #94a3b8;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .af-tool-bar-track {
        flex: 1;
        height: 6px;
        background: rgba(14,165,233,0.08);
        border-radius: 3px;
        overflow: hidden;
    }
    .af-tool-bar-fill {
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, #0ea5e9, #38bdf8);
        transition: width 0.4s ease;
    }
    .af-tool-bar-fill.af-bounty-bar {
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
    }
    .af-tool-bar-count {
        min-width: 18px;
        text-align: right;
        color: #64748b;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.62rem;
    }

    /* ── Escalation counter ── */
    .af-escalation {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.6rem;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 600;
        margin: 0.3rem 0;
    }
    .af-escalation-safe {
        background: rgba(74,222,128,0.06);
        border: 1px solid rgba(74,222,128,0.15);
        color: #4ade80;
    }
    .af-escalation-active {
        background: rgba(248,113,113,0.08);
        border: 1px solid rgba(248,113,113,0.2);
        color: #f87171;
    }

    /* ── Verification scorecard (inline) ── */
    .af-verification {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.35rem;
        padding: 0.4rem 0.6rem;
        background: rgba(15,23,42,0.4);
        border: 1px solid rgba(148,163,184,0.06);
        border-radius: 6px;
        font-size: 0.65rem;
        color: #64748b;
    }
    .af-v-item {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    .af-v-pass { color: #4ade80; }
    .af-v-warn { color: #fbbf24; }
    .af-v-fail { color: #f87171; }

    /* ── Chat bubbles ── */
    .stChatMessage {
        border-radius: 14px;
        border: 1px solid rgba(148,163,184,0.06);
    }
    .stChatMessage [data-testid="chatAvatarIcon-user"] {
        background: linear-gradient(135deg, #0ea5e9, #38bdf8);
    }
    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
        background: linear-gradient(135deg, #10b981, #34d399);
    }

    /* ── Metadata bar ── */
    .af-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        align-items: center;
        font-size: 0.72rem;
        color: #64748b;
        margin-top: 0.5rem;
        padding: 0.5rem 0.6rem;
        border-top: 1px solid rgba(148,163,184,0.08);
        background: rgba(15,23,42,0.3);
        border-radius: 8px;
    }
    .af-meta .af-pill {
        background: rgba(14,165,233,0.1);
        color: #7dd3fc;
        border: 1px solid rgba(14,165,233,0.15);
        border-radius: 999px;
        padding: 0.12rem 0.55rem;
        font-size: 0.65rem;
        font-weight: 600;
    }
    .af-meta .af-latency {
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.65rem;
        color: #475569;
    }
    .af-confidence-high { color: #4ade80; font-weight: 600; }
    .af-confidence-mid  { color: #fbbf24; font-weight: 600; }
    .af-confidence-low  { color: #f87171; font-weight: 600; }

    /* ── Tool activity pulse ── */
    @keyframes toolPulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    .af-tool-active {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        color: #38bdf8;
        font-weight: 600;
        animation: toolPulse 1.5s ease infinite;
    }
    .af-tool-active::before {
        content: "";
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #0ea5e9;
        box-shadow: 0 0 8px rgba(14,165,233,0.6);
    }

    /* ── Disclaimer bar ── */
    .af-disclaimer {
        background: rgba(234,179,8,0.06);
        border: 1px solid rgba(234,179,8,0.15);
        border-radius: 10px;
        padding: 0.6rem 0.9rem;
        font-size: 0.75rem;
        color: #a3a3a3;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .af-disclaimer strong { color: #fbbf24; }

    /* ── Welcome heading ── */
    .af-welcome {
        text-align: center;
        margin: 1rem 0 0.25rem 0;
    }
    .af-welcome h2 {
        font-size: 1.15rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 0;
    }
    .af-welcome p {
        font-size: 0.8rem;
        color: #64748b;
        margin: 0.25rem 0 0 0;
    }

    /* ── Chat input ── */
    .stChatInput textarea {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


def init_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []


def send_message(message: str) -> dict | None:
    """Send a message to the AgentForge API."""
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{API_BASE_URL}/chat",
                json={
                    "message": message,
                    "session_id": st.session_state.session_id,
                },
            )
            if resp.status_code == 200:
                return resp.json()
            st.error(f"API error: {resp.status_code}")
            return None
    except httpx.ConnectError:
        st.error("Cannot connect to backend. Please try again in a moment.")
        return None


def send_feedback(trace_id: str, rating: str):
    """Send feedback for a response."""
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(
                f"{API_BASE_URL}/feedback",
                json={
                    "trace_id": trace_id,
                    "session_id": st.session_state.session_id,
                    "rating": rating,
                },
            )
    except httpx.ConnectError:
        pass


def get_dashboard_stats() -> dict | None:
    """Fetch observability dashboard stats."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{API_BASE_URL}/dashboard")
            if resp.status_code == 200:
                return resp.json()
    except httpx.ConnectError:
        pass
    return None


EXAMPLE_QUESTIONS = [
    ("💊", "Drug Interactions", "Check interaction between warfarin and aspirin"),
    ("🤒", "Symptom Triage", "I have a persistent headache with fever"),
    ("🩺", "Find a Provider", "Find me a cardiologist"),
    ("🛡️", "Insurance", "Does Blue Cross PPO cover an MRI?"),
    ("💉", "Medication Info", "What are the side effects of metformin?"),
    ("⚠️", "FDA Recalls", "Scan patient P001's medications for FDA recalls"),
]


def main():
    init_session()

    # ── Branded header ──────────────────────────────────────────────────
    st.markdown("""
    <div class="af-header">
        <h1>AgentForge Healthcare AI</h1>
        <p class="af-tagline">Nine tools. Five safeguards. Zero hallucinations.</p>
        <div class="af-badge-row">
            <span class="af-badge"><span class="af-badge-dot"></span> LangGraph ReAct</span>
            <span class="af-badge">Groq / Llama 3.3 70B</span>
            <span class="af-badge">9 Tools</span>
            <span class="af-badge">5-Layer Verification</span>
            <span class="af-badge">FDA Recall Monitoring</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""
    <div class="af-disclaimer">
        <span>⚕️</span>
        <span><strong>Educational purposes only.</strong> Not a substitute for professional medical advice. If experiencing a medical emergency, call <strong>911</strong> immediately.</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Core Tools")
        st.markdown("""
        <div class="af-sidebar-section">
            <div class="af-tool-grid">
                <span class="af-tool-chip">💊 Interactions</span>
                <span class="af-tool-chip">🤒 Symptoms</span>
                <span class="af-tool-chip">🩺 Providers</span>
                <span class="af-tool-chip">📅 Appointments</span>
                <span class="af-tool-chip">🛡️ Insurance</span>
                <span class="af-tool-chip">💉 Medications</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Bounty — FDA Recalls")
        st.markdown("""
        <div class="af-sidebar-section">
            <div class="af-tool-grid">
                <span class="af-tool-chip af-bounty">📋 Watchlist</span>
                <span class="af-tool-chip af-bounty">🔍 Recall Check</span>
                <span class="af-tool-chip af-bounty" style="grid-column: span 2">⚠️ Watchlist Scanner</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        if st.button("New Conversation", use_container_width=True, type="primary"):
            try:
                with httpx.Client(timeout=10.0) as client:
                    client.post(
                        f"{API_BASE_URL}/clear-session",
                        json={"session_id": st.session_state.session_id},
                    )
            except httpx.ConnectError:
                pass
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        # Observability dashboard
        stats = get_dashboard_stats()
        if stats and stats.get("total_requests", 0) > 0:
            st.divider()
            st.markdown("### Observability")
            c1, c2 = st.columns(2)
            c1.metric("Requests", stats["total_requests"])
            error_count = stats.get("error_count", 0)
            error_rate = stats.get("error_rate", 0)
            c2.metric("Errors", f"{error_count} ({error_rate:.0%})")
            c1.metric("Avg Latency", f"{stats.get('avg_latency_ms', 0):.0f}ms")
            c2.metric("Avg Confidence", f"{stats.get('avg_confidence', 0):.0%}")

            # Token usage
            total_tokens = stats.get("total_tokens", 0)
            if total_tokens > 0:
                total_cost = stats.get("total_cost_usd", 0)
                cost_str = f"  ·  ${total_cost:.4f}" if total_cost > 0 else ""
                st.caption(f"Tokens: {total_tokens:,}{cost_str}")

            # Feedback
            fb = stats.get("feedback", {})
            if fb.get("thumbs_up", 0) or fb.get("thumbs_down", 0):
                st.caption(f"👍 {fb.get('thumbs_up', 0)}  ·  👎 {fb.get('thumbs_down', 0)}")

            # Escalation counter
            esc_count = stats.get("escalation_count", 0)
            if esc_count > 0:
                st.markdown(
                    f'<div class="af-escalation af-escalation-active">🚨 {esc_count} emergency escalation{"s" if esc_count != 1 else ""} triggered</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="af-escalation af-escalation-safe">✓ No emergency escalations</div>',
                    unsafe_allow_html=True,
                )

            # Tool usage breakdown
            tool_usage = stats.get("tool_usage", {})
            if tool_usage:
                st.markdown("### Tool Usage")
                bounty_tools = {"manage_watchlist", "check_drug_recalls", "scan_watchlist_recalls"}
                max_count = max(tool_usage.values()) if tool_usage else 1
                sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
                bars_html = ""
                for tool_name, count in sorted_tools:
                    pct = (count / max_count) * 100
                    short_name = tool_name.replace("_", " ").title()
                    if len(short_name) > 14:
                        short_name = short_name[:13] + "…"
                    bar_class = "af-bounty-bar" if tool_name in bounty_tools else ""
                    bars_html += f"""<div class="af-tool-bar-row">
                        <span class="af-tool-bar-label">{short_name}</span>
                        <div class="af-tool-bar-track"><div class="af-tool-bar-fill {bar_class}" style="width:{pct:.0f}%"></div></div>
                        <span class="af-tool-bar-count">{count}</span>
                    </div>"""
                st.markdown(
                    f'<div class="af-sidebar-section">{bars_html}</div>',
                    unsafe_allow_html=True,
                )

        # Session info
        msg_count = len(st.session_state.messages)
        if msg_count > 0:
            user_msgs = sum(1 for m in st.session_state.messages if m["role"] == "user")
            st.caption(f"Session: {user_msgs} query{'s' if user_msgs != 1 else ''}")

        # Debug (collapsed)
        with st.expander("System Debug", expanded=False):
            st.caption(f"Session: `{st.session_state.session_id[:8]}`")

            # Recent errors
            if stats and stats.get("recent_errors"):
                st.markdown("**Recent Errors:**")
                for err in stats["recent_errors"][-3:]:
                    st.caption(f"• `{err.get('category', 'Unknown')}`: {err.get('error', 'N/A')[:80]}")

            if st.button("Run Diagnostics", key="diag"):
                try:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.get(f"{API_BASE_URL.replace('/api', '')}/debug")
                        if resp.status_code == 200:
                            st.json(resp.json())
                        else:
                            st.error(f"Debug returned {resp.status_code}")
                except Exception as e:
                    st.error(f"Debug failed: {e}")

    # ── Chat area ───────────────────────────────────────────────────────
    if not st.session_state.messages:
        # Welcome state
        st.markdown("""
        <div class="af-welcome">
            <h2>What can I help you with?</h2>
            <p>Ask about drug interactions, symptoms, providers, insurance, or FDA recalls.</p>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(2)
        for i, (icon, label, question) in enumerate(EXAMPLE_QUESTIONS):
            col = cols[i % 2]
            with col:
                if st.button(
                    f"{icon} **{label}**\n{question}",
                    key=f"welcome_{i}",
                    use_container_width=True,
                ):
                    st.session_state.pending_example = question
                    st.rerun()
    else:
        # Display chat history
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("metadata"):
                    _render_metadata(msg["metadata"], i)

    # Handle pending example question
    if "pending_example" in st.session_state:
        example = st.session_state.pop("pending_example")
        _process_message(example)

    # Chat input
    if prompt := st.chat_input("Ask a healthcare question..."):
        _process_message(prompt)


def _render_metadata(meta: dict, msg_index: int):
    """Render response metadata as a clean bar with pills and feedback."""
    tools = meta.get("tools_used", [])
    confidence = meta.get("confidence", 0)
    latency = meta.get("latency_ms", 0)
    sources = meta.get("sources", [])

    # Confidence colour class
    if confidence >= 0.7:
        conf_cls = "af-confidence-high"
    elif confidence >= 0.5:
        conf_cls = "af-confidence-mid"
    else:
        conf_cls = "af-confidence-low"

    # Build HTML metadata bar
    pills_html = "".join(f'<span class="af-pill">{t}</span>' for t in tools)
    parts = []
    if tools:
        parts.append(pills_html)
    parts.append(f'<span class="{conf_cls}">Confidence {confidence:.0%}</span>')
    if latency:
        parts.append(f'<span class="af-latency">{latency:.0f}ms</span>')
    if sources:
        parts.append(f"{len(sources)} source{'s' if len(sources) != 1 else ''}")

    st.markdown(
        f'<div class="af-meta">{" ".join(parts)}</div>',
        unsafe_allow_html=True,
    )

    # Inline verification scorecard
    verification = meta.get("verification", {})
    if verification:
        v_items = []
        # Source grounding
        has_sources = verification.get("has_sources", False)
        v_items.append(
            f'<span class="af-v-item {"af-v-pass" if has_sources else "af-v-warn"}">{"✓" if has_sources else "○"} Sources</span>'
        )
        # Hallucination risk
        h_risk = verification.get("hallucination_risk", 0)
        if h_risk > 0.5:
            v_items.append(f'<span class="af-v-item af-v-fail">⚠ Hallucination {h_risk:.0%}</span>')
        elif h_risk > 0:
            v_items.append(f'<span class="af-v-item af-v-warn">○ Hallucination {h_risk:.0%}</span>')
        else:
            v_items.append('<span class="af-v-item af-v-pass">✓ Grounded</span>')
        # Domain violations
        violations = verification.get("domain_violations", [])
        if violations:
            v_items.append(f'<span class="af-v-item af-v-fail">⚠ {len(violations)} violation{"s" if len(violations) != 1 else ""}</span>')
        else:
            v_items.append('<span class="af-v-item af-v-pass">✓ Domain safe</span>')
        # Escalation
        if verification.get("needs_escalation"):
            v_items.append('<span class="af-v-item af-v-fail">🚨 Escalation</span>')
        # Output valid
        if verification.get("output_valid", True):
            v_items.append('<span class="af-v-item af-v-pass">✓ Valid</span>')
        else:
            v_items.append('<span class="af-v-item af-v-fail">⚠ Invalid</span>')

        st.markdown(
            f'<div class="af-verification">{" ".join(v_items)}</div>',
            unsafe_allow_html=True,
        )

    # Collapsible structured results
    if tools or meta.get("trace_id"):
        with st.expander("View Structured Results", expanded=False):
            import json as _json
            debug_data = {}
            if tools:
                debug_data["tools_called"] = tools
            if confidence:
                debug_data["confidence_score"] = confidence
            if sources:
                debug_data["sources"] = sources
            if meta.get("trace_id"):
                debug_data["trace_id"] = meta["trace_id"]
            if latency:
                debug_data["latency_ms"] = round(latency, 1)
            if meta.get("tokens"):
                debug_data["tokens"] = meta["tokens"]
            if meta.get("verification"):
                debug_data["verification"] = meta["verification"]
            st.json(debug_data)

    # Feedback buttons
    trace_id = meta.get("trace_id", "")
    if trace_id:
        feedback_key = f"feedback_{msg_index}"
        if feedback_key not in st.session_state:
            bcol1, bcol2, bcol3 = st.columns([1, 1, 10])
            with bcol1:
                if st.button("👍", key=f"up_{msg_index}", help="Helpful"):
                    send_feedback(trace_id, "up")
                    st.session_state[feedback_key] = "up"
                    st.rerun()
            with bcol2:
                if st.button("👎", key=f"down_{msg_index}", help="Not helpful"):
                    send_feedback(trace_id, "down")
                    st.session_state[feedback_key] = "down"
                    st.rerun()
        else:
            rating = st.session_state[feedback_key]
            icon = "👍" if rating == "up" else "👎"
            st.caption(f"Feedback: {icon} recorded")


def _stream_message(message: str) -> tuple[str, dict]:
    """Stream a message via SSE endpoint. Returns (full_text, metadata)."""
    import json

    full_text = ""
    metadata = {}
    tool_status = st.empty()

    try:
        with httpx.Client(timeout=90.0) as client:
            with client.stream(
                "POST",
                f"{API_BASE_URL}/chat/stream",
                json={"message": message, "session_id": st.session_state.session_id},
            ) as resp:
                if resp.status_code != 200:
                    return "", {}

                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = json.loads(line[6:])
                    event_type = data.get("type", "")

                    if event_type == "token":
                        full_text += data["content"]
                        yield data["content"]
                    elif event_type == "tool_start":
                        tool_status.markdown(
                            f'<div class="af-tool-active">Using {data["content"]}</div>',
                            unsafe_allow_html=True,
                        )
                    elif event_type == "tool_end":
                        tool_status.empty()
                    elif event_type == "done":
                        metadata.update(data.get("content", {}))
                    elif event_type == "error":
                        yield f"\n\nError: {data['content']}"
    except httpx.ConnectError:
        yield "Cannot connect to backend. Please try again in a moment."
    except Exception:
        yield "An error occurred while streaming the response."

    # Store metadata on session state for retrieval after streaming
    st.session_state._stream_metadata = metadata
    st.session_state._stream_full_text = full_text


def _process_message(message: str):
    """Process a user message and get agent response with streaming."""
    st.session_state.messages.append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.markdown(message)

    with st.chat_message("assistant"):
        # Try streaming first, fall back to non-streaming
        try:
            full_text = st.write_stream(_stream_message(message))
            meta = st.session_state.pop("_stream_metadata", {})

            if meta:
                result_meta = {
                    "tools_used": meta.get("tools_used", []),
                    "confidence": meta.get("confidence", 0),
                    "sources": meta.get("sources", []),
                    "trace_id": meta.get("trace_id", ""),
                    "latency_ms": meta.get("latency_ms", 0),
                    "tokens": meta.get("tokens", {}),
                    "verification": meta.get("verification", {}),
                }
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_text,
                    "metadata": result_meta,
                })
                _render_metadata(result_meta, len(st.session_state.messages) - 1)
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_text,
                })
        except Exception:
            # Fall back to non-streaming
            with st.spinner("Analyzing your query..."):
                result = send_message(message)

            if result:
                st.markdown(result["response"])
                meta = {
                    "tools_used": result.get("tools_used", []),
                    "confidence": result.get("confidence", 0),
                    "sources": result.get("sources", []),
                    "trace_id": result.get("trace_id", ""),
                    "latency_ms": result.get("latency_ms", 0),
                    "tokens": result.get("tokens", {}),
                    "verification": result.get("verification", {}),
                }
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"],
                    "metadata": meta,
                })
                _render_metadata(meta, len(st.session_state.messages) - 1)
            else:
                error_msg = "Sorry, I couldn't process your request. Please try again."
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
