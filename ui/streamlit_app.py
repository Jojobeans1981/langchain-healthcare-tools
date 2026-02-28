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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ══════════════════════════════════════════════════════════════════
       §1  GLOBAL · GLASS-MORPHISM DESIGN SYSTEM
       ══════════════════════════════════════════════════════════════════ */
    .stApp {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        line-height: 1.6;
        letter-spacing: 0.01em;
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

    /* ══════════════════════════════════════════════════════════════════
       §2  AMBIENT AURORA BACKGROUND
       ══════════════════════════════════════════════════════════════════ */
    @keyframes auroraShift {
        0%   { transform: translate(-50%,-50%) rotate(0deg) scale(1); opacity: 0.035; }
        25%  { transform: translate(-50%,-50%) rotate(90deg) scale(1.15); opacity: 0.05; }
        50%  { transform: translate(-50%,-50%) rotate(180deg) scale(0.95); opacity: 0.03; }
        75%  { transform: translate(-50%,-50%) rotate(270deg) scale(1.1); opacity: 0.045; }
        100% { transform: translate(-50%,-50%) rotate(360deg) scale(1); opacity: 0.035; }
    }
    .af-aurora {
        position: fixed;
        top: 40%;
        left: 55%;
        width: 70vw;
        height: 70vw;
        max-width: 900px;
        max-height: 900px;
        pointer-events: none;
        z-index: 0;
        border-radius: 50%;
        background: radial-gradient(ellipse at center,
            rgba(14,165,233,0.12) 0%,
            rgba(59,130,246,0.08) 25%,
            rgba(139,92,246,0.05) 50%,
            transparent 70%
        );
        filter: blur(80px);
        animation: auroraShift 30s ease-in-out infinite;
    }
    @keyframes auroraShift2 {
        0%   { transform: translate(-50%,-50%) rotate(180deg) scale(0.9); opacity: 0.025; }
        50%  { transform: translate(-50%,-50%) rotate(360deg) scale(1.1); opacity: 0.04; }
        100% { transform: translate(-50%,-50%) rotate(540deg) scale(0.9); opacity: 0.025; }
    }
    .af-aurora-2 {
        position: fixed;
        top: 60%;
        left: 30%;
        width: 50vw;
        height: 50vw;
        max-width: 650px;
        max-height: 650px;
        pointer-events: none;
        z-index: 0;
        border-radius: 50%;
        background: radial-gradient(ellipse at center,
            rgba(16,185,129,0.08) 0%,
            rgba(14,165,233,0.05) 40%,
            transparent 70%
        );
        filter: blur(70px);
        animation: auroraShift2 25s ease-in-out infinite;
    }

    /* ── Custom scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(14,165,233,0.2);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(14,165,233,0.35);
    }

    /* ── Smooth scrolling ── */
    html, .main { scroll-behavior: smooth; }

    /* ── Tighter spacing ── */
    .stMainBlockContainer { padding-top: 1rem; }

    /* ══════════════════════════════════════════════════════════════════
       §3  ANIMATED GRADIENT HEADER
       ══════════════════════════════════════════════════════════════════ */
    @keyframes headerShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    @keyframes badgeDotPulse {
        0%, 100% { box-shadow: 0 0 4px rgba(14,165,233,0.4); }
        50%      { box-shadow: 0 0 10px rgba(14,165,233,0.8), 0 0 20px rgba(14,165,233,0.3); }
    }
    @keyframes statusPulse {
        0%, 100% { box-shadow: 0 0 4px rgba(74,222,128,0.4); }
        50%      { box-shadow: 0 0 10px rgba(74,222,128,0.8), 0 0 20px rgba(74,222,128,0.3); }
    }
    .af-header {
        background: linear-gradient(135deg, #0c1220 0%, #0f2847 25%, #0c1e3a 50%, #112240 75%, #0c1220 100%);
        background-size: 400% 400%;
        animation: headerShift 12s ease infinite;
        border: 1px solid rgba(14,165,233,0.2);
        border-radius: 16px;
        padding: 1.6rem 1.8rem;
        margin-bottom: 0.75rem;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(16px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 4px 24px rgba(0,0,0,0.3),
            0 0 0 1px rgba(14,165,233,0.08);
    }
    .af-header::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(ellipse at 20% 50%, rgba(14,165,233,0.1) 0%, transparent 60%);
        pointer-events: none;
    }
    .af-header::after {
        content: "";
        position: absolute;
        top: 0; left: -100%; right: 0; bottom: 0;
        width: 300%;
        background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.02) 45%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.02) 55%, transparent 100%);
        animation: shimmer 8s ease-in-out infinite;
        pointer-events: none;
    }
    .af-header h1 {
        margin: 0 0 0.3rem 0;
        font-size: clamp(1.4rem, 3.5vw, 1.85rem);
        font-weight: 900;
        background: linear-gradient(90deg, #e2e8f0 0%, #0ea5e9 30%, #8b5cf6 60%, #38bdf8 80%, #e2e8f0 100%);
        background-size: 300% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.03em;
        line-height: 1.2;
        animation: shimmer 6s ease infinite;
        position: relative;
        z-index: 1;
    }
    .af-header .af-tagline {
        font-size: 0.82rem;
        color: #64748b;
        margin: 0 0 0.75rem 0;
        font-weight: 500;
        letter-spacing: 0.02em;
        position: relative;
        z-index: 1;
    }
    .af-badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        position: relative;
        z-index: 1;
    }
    .af-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(14,165,233,0.08);
        color: #38bdf8;
        border: 1px solid rgba(14,165,233,0.18);
        border-radius: 999px;
        padding: 0.22rem 0.7rem;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        backdrop-filter: blur(8px);
        transition: all 0.25s ease;
    }
    .af-badge:hover {
        background: rgba(14,165,233,0.14);
        border-color: rgba(14,165,233,0.35);
        transform: translateY(-1px);
        box-shadow: 0 2px 12px rgba(14,165,233,0.15);
    }
    .af-badge .af-badge-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #0ea5e9;
        animation: badgeDotPulse 2s ease infinite;
    }
    .af-badge-status {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(74,222,128,0.06);
        color: #4ade80;
        border: 1px solid rgba(74,222,128,0.18);
        border-radius: 999px;
        padding: 0.22rem 0.7rem;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .af-badge-status .af-status-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #4ade80;
        animation: statusPulse 2s ease infinite;
    }

    /* ══════════════════════════════════════════════════════════════════
       §4 + §5  EXAMPLE QUESTION CARDS WITH STAGGERED ENTRANCE
       ══════════════════════════════════════════════════════════════════ */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .af-examples-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.55rem;
        margin: 0.5rem 0 1rem 0;
    }
    .af-example-card {
        background: rgba(15,23,42,0.4);
        border: 1px solid rgba(14,165,233,0.12);
        border-radius: 14px;
        padding: 0.9rem 1.1rem;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(12px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    .af-example-card:hover {
        border-color: rgba(14,165,233,0.5);
        background: rgba(15,23,42,0.6);
        transform: translateY(-3px);
        box-shadow:
            0 0 0 1px rgba(14,165,233,0.25),
            0 8px 32px rgba(14,165,233,0.12),
            inset 0 1px 0 rgba(255,255,255,0.06);
    }
    .af-example-card::after {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 0% 0%, rgba(14,165,233,0.08) 0%, transparent 50%);
        pointer-events: none;
        transition: opacity 0.3s ease;
    }
    .af-example-card:hover::after {
        background: radial-gradient(circle at 0% 0%, rgba(14,165,233,0.14) 0%, transparent 60%);
    }
    .af-example-icon {
        font-size: 1.3rem;
        margin-bottom: 0.3rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.2rem;
        height: 2.2rem;
        border-radius: 10px;
        background: rgba(14,165,233,0.08);
        border: 1px solid rgba(14,165,233,0.12);
    }
    .af-example-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.2rem;
    }
    .af-example-text {
        font-size: 0.82rem;
        color: #94a3b8;
        line-height: 1.4;
    }
    .af-example-arrow {
        position: absolute;
        right: 0.8rem;
        top: 50%;
        transform: translateY(-50%) translateX(8px);
        opacity: 0;
        color: #38bdf8;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }
    .af-example-card:hover .af-example-arrow {
        opacity: 0.6;
        transform: translateY(-50%) translateX(0);
    }

    /* ── Staggered entrance for Streamlit buttons (example cards) ── */
    div[data-testid="stVerticalBlock"] button[kind="secondary"] {
        border: 1px solid rgba(14,165,233,0.12);
        border-radius: 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: left;
        font-size: 0.82rem;
        padding: 0.8rem 1rem;
        background: rgba(15,23,42,0.4);
        backdrop-filter: blur(12px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        animation: fadeInUp 0.5s ease both;
    }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover {
        border-color: rgba(14,165,233,0.5);
        background: rgba(14,165,233,0.08);
        transform: translateY(-3px);
        box-shadow:
            0 0 0 1px rgba(14,165,233,0.25),
            0 8px 32px rgba(14,165,233,0.12),
            inset 0 1px 0 rgba(255,255,255,0.06);
    }
    /* Staggered animation delays for the 6 example cards */
    div[data-testid="stVerticalBlock"] > div:nth-child(1) button[kind="secondary"] { animation-delay: 0s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(2) button[kind="secondary"] { animation-delay: 0.08s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(3) button[kind="secondary"] { animation-delay: 0.16s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(4) button[kind="secondary"] { animation-delay: 0.24s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(5) button[kind="secondary"] { animation-delay: 0.32s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(6) button[kind="secondary"] { animation-delay: 0.40s; }

    /* ══════════════════════════════════════════════════════════════════
       §6  POLISHED CHAT BUBBLES
       ══════════════════════════════════════════════════════════════════ */
    @keyframes messageSlideIn {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .stChatMessage {
        border-radius: 16px;
        border: 1px solid rgba(148,163,184,0.06);
        padding: 1.1rem;
        animation: messageSlideIn 0.35s ease both;
        backdrop-filter: blur(8px);
        transition: border-color 0.2s ease;
    }
    .stChatMessage:hover {
        border-color: rgba(148,163,184,0.12);
    }
    /* User message accent */
    .stChatMessage:has([data-testid="chatAvatarIcon-user"]) {
        border-left: 3px solid rgba(14,165,233,0.4);
        background: rgba(14,165,233,0.02);
    }
    /* Assistant message accent */
    .stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {
        border-left: 3px solid rgba(16,185,129,0.4);
        background: rgba(16,185,129,0.02);
    }
    .stChatMessage [data-testid="chatAvatarIcon-user"] {
        background: linear-gradient(135deg, #0ea5e9, #38bdf8);
        box-shadow: 0 2px 8px rgba(14,165,233,0.3);
    }
    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
        background: linear-gradient(135deg, #10b981, #34d399);
        box-shadow: 0 2px 8px rgba(16,185,129,0.3);
    }

    /* ══════════════════════════════════════════════════════════════════
       §7  ENHANCED TOOL ACTIVITY INDICATOR
       ══════════════════════════════════════════════════════════════════ */
    @keyframes toolSpin {
        to { transform: rotate(360deg); }
    }
    @keyframes toolPulse {
        0%, 100% { opacity: 0.7; }
        50% { opacity: 1; }
    }
    @keyframes toolProgressSweep {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    .af-tool-active {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.78rem;
        color: #38bdf8;
        font-weight: 600;
        animation: toolPulse 1.5s ease infinite;
        padding: 0.5rem 0.8rem;
        background: rgba(14,165,233,0.06);
        border: 1px solid rgba(14,165,233,0.15);
        border-radius: 10px;
        backdrop-filter: blur(8px);
        position: relative;
        overflow: hidden;
    }
    .af-tool-active::before {
        content: "";
        width: 14px; height: 14px;
        border-radius: 50%;
        border: 2px solid rgba(14,165,233,0.2);
        border-top-color: #0ea5e9;
        animation: toolSpin 0.8s linear infinite;
        flex-shrink: 0;
    }
    .af-tool-active::after {
        content: "";
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #0ea5e9, #38bdf8, transparent);
        background-size: 200% 100%;
        animation: toolProgressSweep 1.5s ease-in-out infinite;
    }

    /* ══════════════════════════════════════════════════════════════════
       §8  CONFIDENCE GAUGE + METADATA BAR
       ══════════════════════════════════════════════════════════════════ */
    .af-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        align-items: center;
        font-size: 0.72rem;
        color: #64748b;
        margin-top: 0.5rem;
        padding: 0.55rem 0.75rem;
        border-top: 1px solid rgba(148,163,184,0.08);
        background: rgba(15,23,42,0.35);
        backdrop-filter: blur(12px);
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.04);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    .af-meta .af-pill {
        background: rgba(14,165,233,0.1);
        color: #7dd3fc;
        border: 1px solid rgba(14,165,233,0.18);
        border-radius: 999px;
        padding: 0.14rem 0.6rem;
        font-size: 0.65rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .af-meta .af-pill:hover {
        background: rgba(14,165,233,0.18);
        border-color: rgba(14,165,233,0.35);
    }
    .af-meta .af-latency {
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.65rem;
        color: #475569;
    }
    .af-confidence-high { color: #4ade80; font-weight: 600; }
    .af-confidence-mid  { color: #fbbf24; font-weight: 600; }
    .af-confidence-low  { color: #f87171; font-weight: 600; }

    /* Confidence gauge bar */
    .af-conf-gauge {
        display: inline-block;
        width: 56px;
        height: 5px;
        background: rgba(148,163,184,0.12);
        border-radius: 3px;
        overflow: hidden;
        vertical-align: middle;
        margin-right: 0.3rem;
        position: relative;
    }
    .af-conf-fill {
        display: block;
        height: 100%;
        border-radius: 3px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .af-conf-fill-high {
        background: linear-gradient(90deg, #10b981, #4ade80);
        box-shadow: 0 0 6px rgba(74,222,128,0.4);
    }
    .af-conf-fill-mid {
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
        box-shadow: 0 0 6px rgba(251,191,36,0.4);
    }
    .af-conf-fill-low {
        background: linear-gradient(90deg, #ef4444, #f87171);
        box-shadow: 0 0 6px rgba(248,113,113,0.4);
    }

    /* ══════════════════════════════════════════════════════════════════
       §9  VERIFICATION BADGES
       ══════════════════════════════════════════════════════════════════ */
    .af-verification {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.35rem;
        padding: 0.45rem 0.65rem;
        background: rgba(15,23,42,0.35);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 8px;
        font-size: 0.64rem;
        color: #64748b;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    .af-v-item {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.1rem 0.45rem;
        border-radius: 999px;
        background: rgba(148,163,184,0.06);
        border: 1px solid rgba(148,163,184,0.08);
        transition: all 0.2s ease;
        font-weight: 500;
    }
    .af-v-item:hover {
        background: rgba(148,163,184,0.1);
    }
    .af-v-pass {
        color: #4ade80;
        background: rgba(74,222,128,0.06);
        border-color: rgba(74,222,128,0.15);
    }
    .af-v-warn {
        color: #fbbf24;
        background: rgba(251,191,36,0.06);
        border-color: rgba(251,191,36,0.15);
    }
    .af-v-fail {
        color: #f87171;
        background: rgba(248,113,113,0.06);
        border-color: rgba(248,113,113,0.15);
    }

    /* ══════════════════════════════════════════════════════════════════
       §10  SIDEBAR VISUAL OVERHAUL
       ══════════════════════════════════════════════════════════════════ */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(14,165,233,0.1);
        background: linear-gradient(180deg, rgba(12,18,32,0.97) 0%, rgba(15,23,42,0.97) 100%);
        backdrop-filter: blur(20px);
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        opacity: 0.5;
        margin-bottom: 0.4rem;
        font-weight: 700;
    }
    /* Gradient divider to replace plain st.divider */
    section[data-testid="stSidebar"] hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(14,165,233,0.25) 50%, transparent 100%);
        margin: 0.6rem 0;
    }
    .af-sidebar-section {
        background: rgba(14,165,233,0.04);
        border: 1px solid rgba(14,165,233,0.1);
        border-radius: 12px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        backdrop-filter: blur(8px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
        transition: border-color 0.2s ease;
    }
    .af-sidebar-section:hover {
        border-color: rgba(14,165,233,0.2);
    }
    .af-tool-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.35rem;
    }
    .af-tool-chip {
        font-size: 0.68rem;
        color: #94a3b8;
        background: rgba(14,165,233,0.06);
        border: 1px solid rgba(14,165,233,0.1);
        border-radius: 8px;
        padding: 0.3rem 0.5rem;
        text-align: center;
        font-weight: 500;
        transition: all 0.25s ease;
        cursor: default;
    }
    .af-tool-chip:hover {
        background: rgba(14,165,233,0.12);
        border-color: rgba(14,165,233,0.25);
        color: #bae6fd;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(14,165,233,0.1);
    }
    .af-tool-chip.af-bounty {
        color: #fbbf24;
        background: rgba(251,191,36,0.06);
        border-color: rgba(251,191,36,0.15);
    }
    .af-tool-chip.af-bounty:hover {
        background: rgba(251,191,36,0.12);
        border-color: rgba(251,191,36,0.3);
        color: #fde68a;
        box-shadow: 0 2px 8px rgba(251,191,36,0.1);
    }

    /* ── Sidebar status indicator ── */
    .af-sidebar-status {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.65rem;
        margin-bottom: 0.5rem;
        border-radius: 8px;
        font-size: 0.7rem;
        font-weight: 600;
        color: #4ade80;
        background: rgba(74,222,128,0.04);
        border: 1px solid rgba(74,222,128,0.12);
    }
    .af-sidebar-status .af-live-dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        background: #4ade80;
        animation: statusPulse 2s ease infinite;
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
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 4px rgba(14,165,233,0.3);
    }
    .af-tool-bar-fill.af-bounty-bar {
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
        box-shadow: 0 0 4px rgba(251,191,36,0.3);
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
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
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

    /* ══════════════════════════════════════════════════════════════════
       §11  DISCLAIMER BAR (glass-morphism)
       ══════════════════════════════════════════════════════════════════ */
    .af-disclaimer {
        background: rgba(234,179,8,0.05);
        border: 1px solid rgba(234,179,8,0.15);
        border-radius: 12px;
        padding: 0.65rem 1rem;
        font-size: 0.75rem;
        color: #a3a3a3;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        backdrop-filter: blur(12px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    .af-disclaimer strong { color: #fbbf24; }

    /* ══════════════════════════════════════════════════════════════════
       §12  WELCOME HEADING + CHAT INPUT
       ══════════════════════════════════════════════════════════════════ */
    @keyframes welcomeFadeIn {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .af-welcome {
        text-align: center;
        margin: 1.5rem 0 0.5rem 0;
        animation: welcomeFadeIn 0.6s ease both;
    }
    .af-welcome h2 {
        font-size: clamp(1.1rem, 3vw, 1.35rem);
        font-weight: 800;
        background: linear-gradient(135deg, #e2e8f0, #f8fafc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        line-height: 1.3;
    }
    .af-welcome p {
        font-size: 0.82rem;
        color: #64748b;
        margin: 0.35rem 0 0 0;
        font-weight: 400;
    }

    /* Chat input */
    .stChatInput {
        transition: all 0.3s ease;
    }
    .stChatInput textarea {
        border-radius: 14px;
        font-size: 0.88rem;
        padding: 0.8rem 1rem;
        background: rgba(15,23,42,0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(14,165,233,0.12);
        transition: all 0.3s ease;
    }
    .stChatInput textarea:focus {
        border-color: rgba(14,165,233,0.4);
        box-shadow:
            0 0 0 3px rgba(14,165,233,0.1),
            0 4px 16px rgba(14,165,233,0.08);
    }

    /* ══════════════════════════════════════════════════════════════════
       §13  REDUCED MOTION SUPPORT
       ══════════════════════════════════════════════════════════════════ */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }

    /* ══════════════════════════════════════════════════════════════════
       §14  RESPONSIVE LAYOUT
       ══════════════════════════════════════════════════════════════════ */
    @media (max-width: 640px) {
        .af-examples-grid {
            grid-template-columns: 1fr;
        }
        .af-badge-row {
            gap: 0.25rem;
        }
        .af-badge {
            font-size: 0.62rem;
            padding: 0.18rem 0.5rem;
        }
        .af-header {
            padding: 1.2rem 1rem;
        }
        .af-header h1 {
            font-size: 1.3rem;
        }
        .af-tool-grid {
            grid-template-columns: 1fr;
        }
        div[data-testid="stVerticalBlock"] button[kind="secondary"] {
            min-height: 44px;
        }
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

    # ── Ambient aurora background ─────────────────────────────────────
    st.markdown(
        '<div class="af-aurora"></div><div class="af-aurora-2"></div>',
        unsafe_allow_html=True,
    )

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
            <span class="af-badge-status"><span class="af-status-dot"></span> System Online</span>
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
        st.markdown(
            '<div class="af-sidebar-status"><span class="af-live-dot"></span> AgentForge Active</div>',
            unsafe_allow_html=True,
        )
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

    # Confidence gauge fill class
    if confidence >= 0.7:
        gauge_cls = "af-conf-fill-high"
    elif confidence >= 0.5:
        gauge_cls = "af-conf-fill-mid"
    else:
        gauge_cls = "af-conf-fill-low"

    # Build HTML metadata bar
    pills_html = "".join(f'<span class="af-pill">{t}</span>' for t in tools)
    parts = []
    if tools:
        parts.append(pills_html)
    conf_pct = int(confidence * 100)
    parts.append(
        f'<span class="af-conf-gauge"><span class="af-conf-fill {gauge_cls}" style="width:{conf_pct}%"></span></span>'
        f'<span class="{conf_cls}">{confidence:.0%}</span>'
    )
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
