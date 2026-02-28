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
        opacity: 0.07;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 220'%3E%3Cdefs%3E%3ClinearGradient id='wm' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0%25' stop-color='%230ea5e9'/%3E%3Cstop offset='100%25' stop-color='%2338bdf8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Ctext x='300' y='110' text-anchor='middle' font-family='system-ui,sans-serif' font-weight='900' font-size='82' fill='url(%23wm)' letter-spacing='-2'%3EAGENTFORGE%3C/text%3E%3Ctext x='300' y='175' text-anchor='middle' font-family='system-ui,sans-serif' font-weight='600' font-size='32' fill='%230ea5e9' letter-spacing='10'%3EHEALTHCARE AI%3C/text%3E%3C/svg%3E");
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
        opacity: 0.13;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 260 70'%3E%3Ctext x='8' y='32' font-family='system-ui,sans-serif' font-weight='800' font-size='18' fill='%230ea5e9' letter-spacing='3'%3EGAUNTLET AI%3C/text%3E%3Crect x='8' y='42' width='56' height='24' rx='12' fill='none' stroke='%230ea5e9' stroke-width='2'/%3E%3Ctext x='36' y='60' text-anchor='middle' font-family='system-ui,sans-serif' font-weight='900' font-size='16' fill='%230ea5e9'%3EG4%3C/text%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
    }

    /* Tighter top padding */
    .stMainBlockContainer { padding-top: 1.5rem; }

    /* Branded header strip */
    .af-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        border: 1px solid rgba(14,165,233,0.25);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .af-header h1 {
        margin: 0 0 0.15rem 0;
        font-size: 1.65rem;
        color: #f1f5f9;
        letter-spacing: -0.02em;
    }
    .af-header .af-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        margin: 0;
    }
    .af-header .af-badge {
        display: inline-block;
        background: rgba(14,165,233,0.15);
        color: #38bdf8;
        border: 1px solid rgba(14,165,233,0.3);
        border-radius: 999px;
        padding: 0.15rem 0.6rem;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        margin-right: 0.35rem;
    }

    /* Example question cards */
    .af-examples {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.6rem;
        margin: 0.75rem 0 1rem 0;
    }

    /* Style Streamlit buttons as cards */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        border: 1px solid rgba(14,165,233,0.2);
        border-radius: 10px;
        transition: all 0.2s ease;
        text-align: left;
        font-size: 0.85rem;
        padding: 0.6rem 0.8rem;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        border-color: rgba(14,165,233,0.6);
        background: rgba(14,165,233,0.06);
        transform: translateY(-1px);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(14,165,233,0.12);
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        opacity: 0.6;
        margin-bottom: 0.4rem;
    }

    /* Smaller metric values in sidebar */
    div[data-testid="stMetricValue"] { font-size: 1.3rem; }
    div[data-testid="stMetricLabel"] { font-size: 0.72rem; opacity: 0.7; }

    /* Chat bubbles */
    .stChatMessage { border-radius: 12px; }

    /* Metadata bar under assistant messages */
    .af-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: center;
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 0.4rem;
        padding: 0.4rem 0;
        border-top: 1px solid rgba(148,163,184,0.12);
    }
    .af-meta .af-pill {
        background: rgba(14,165,233,0.1);
        color: #7dd3fc;
        border-radius: 999px;
        padding: 0.1rem 0.55rem;
        font-size: 0.7rem;
        font-weight: 500;
    }
    .af-confidence-high { color: #4ade80; }
    .af-confidence-mid  { color: #fbbf24; }
    .af-confidence-low  { color: #f87171; }
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
    ("Drug Interactions", "Check interaction between warfarin and aspirin"),
    ("Symptom Triage", "I have a persistent headache with fever"),
    ("Find a Provider", "Find me a cardiologist"),
    ("Insurance", "Does Blue Cross PPO cover an MRI?"),
    ("Medication Info", "What are the side effects of metformin?"),
    ("FDA Recalls", "Scan patient P001's medications for FDA recalls"),
]


def main():
    init_session()

    # ── Branded header ──────────────────────────────────────────────────
    st.markdown("""
    <div class="af-header">
        <h1>AgentForge Healthcare AI</h1>
        <p class="af-sub" style="margin-bottom:0.5rem;">
            Nine tools. Five safeguards. Zero hallucinations.
        </p>
        <span class="af-badge">LangGraph</span>
        <span class="af-badge">Groq / Llama 3.3 70B</span>
        <span class="af-badge">9 Tools</span>
        <span class="af-badge">5-Layer Verification</span>
    </div>
    """, unsafe_allow_html=True)

    # Disclaimer (compact)
    st.info(
        "**For educational purposes only.** Not a substitute for professional medical advice. "
        "If experiencing a medical emergency, call **911** immediately.",
        icon="⚕️",
    )

    # ── Sidebar ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Tools")
        st.markdown(
            "**Core:** Drug Interactions · Symptoms · "
            "Providers · Appointments · Insurance · Medications\n\n"
            "**FDA Recall:** Watchlist · Recall Checker · Watchlist Scanner"
        )

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
            c2.metric("Errors", stats.get("error_count", 0))
            c1.metric("Avg Latency", f"{stats.get('avg_latency_ms', 0):.0f}ms")
            c2.metric("Avg Confidence", f"{stats.get('avg_confidence', 0):.0%}")

            fb = stats.get("feedback", {})
            if fb.get("thumbs_up", 0) or fb.get("thumbs_down", 0):
                st.caption(f"Feedback: {fb.get('thumbs_up', 0)} up / {fb.get('thumbs_down', 0)} down")

            total_cost = stats.get("total_cost_usd", 0)
            if total_cost > 0:
                st.caption(f"Est. cost: ${total_cost:.4f}")

        # Debug (collapsed by default)
        with st.expander("System Debug", expanded=False):
            st.caption(f"Session: {st.session_state.session_id[:8]}")
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
        # Welcome state with categorised example prompts
        st.markdown("#### Try asking:")
        cols = st.columns(2)
        for i, (label, question) in enumerate(EXAMPLE_QUESTIONS):
            col = cols[i % 2]
            with col:
                if st.button(
                    f"**{label}**\n{question}",
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
        parts.append(f"{latency:.0f}ms")
    if sources:
        parts.append(f"{len(sources)} source{'s' if len(sources) != 1 else ''}")

    st.markdown(
        f'<div class="af-meta">{" ".join(parts)}</div>',
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
                        tool_status.caption(f"Using tool: {data['content']}...")
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
