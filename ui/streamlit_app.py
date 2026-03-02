import os
import uuid

import httpx
import streamlit as st

# Configuration — supports environment variable override for production
API_BASE_URL = os.environ.get("AGENTFORGE_API_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="AgentForge Healthcare AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
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
        opacity: 0.08;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 220'%3E%3Cdefs%3E%3ClinearGradient id='wm' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0%25' stop-color='%230ea5e9'/%3E%3Cstop offset='100%25' stop-color='%2338bdf8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Ctext x='300' y='110' text-anchor='middle' font-family='Inter,system-ui,sans-serif' font-weight='900' font-size='82' fill='url(%23wm)' letter-spacing='-2'%3EAGENTFORGE%3C/text%3E%3Ctext x='300' y='175' text-anchor='middle' font-family='Inter,system-ui,sans-serif' font-weight='600' font-size='32' fill='%230ea5e9' letter-spacing='10'%3EHEALTHCARE AI%3C/text%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
    }
    /* ── Gauntlet AI G4 badge (bottom-right, real element) ── */
    .af-gauntlet-badge {
        position: fixed;
        bottom: 16px;
        right: 18px;
        pointer-events: none;
        z-index: 99999;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        text-align: right;
        line-height: 1.3;
    }
    .af-gauntlet-badge .af-g-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2.5px;
        color: rgba(148, 163, 184, 0.6);
        text-transform: uppercase;
    }
    .af-gauntlet-badge .af-g-cohort {
        display: inline-block;
        margin-top: 2px;
        font-size: 13px;
        font-weight: 900;
        color: rgba(14, 165, 233, 0.7);
        border: 1.5px solid rgba(14, 165, 233, 0.4);
        border-radius: 10px;
        padding: 1px 10px;
        letter-spacing: 1px;
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

    /* ── Dot grid background ── */
    .stApp::after {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: 0.18;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='28'%3E%3Ccircle cx='1' cy='1' r='0.9' fill='%230ea5e9' fill-opacity='0.45'/%3E%3C/svg%3E");
        background-repeat: repeat;
        background-size: 28px 28px;
        mask-image: radial-gradient(ellipse 80% 70% at 50% 50%, black 20%, transparent 100%);
        -webkit-mask-image: radial-gradient(ellipse 80% 70% at 50% 50%, black 20%, transparent 100%);
    }

    /* ── Custom scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track {
        background: rgba(15,23,42,0.3);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, rgba(14,165,233,0.35) 0%, rgba(59,130,246,0.25) 100%);
        border-radius: 4px;
        transition: background 0.2s ease;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, rgba(14,165,233,0.6) 0%, rgba(59,130,246,0.45) 100%);
        box-shadow: 0 0 6px rgba(14,165,233,0.3);
    }
    ::-webkit-scrollbar-corner { background: transparent; }

    /* Firefox scrollbar */
    * { scrollbar-width: thin; scrollbar-color: rgba(14,165,233,0.3) rgba(15,23,42,0.3); }

    /* ── Smooth scrolling ── */
    html, .main { scroll-behavior: smooth; }

    /* ── Ensure content layers sit above decorative backgrounds ── */
    .main .block-container,
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    .stMainBlockContainer,
    .stChatFloatingInputContainer {
        position: relative;
        z-index: 2;
    }

    /* ── Tighter spacing + constrain width for wide layout ── */
    .stMainBlockContainer {
        padding-top: 1rem;
        max-width: 52rem;
        margin-left: auto;
        margin-right: auto;
    }

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
    /* Staggered animation delays for the example cards */
    div[data-testid="stVerticalBlock"] > div:nth-child(1) button[kind="secondary"] { animation-delay: 0s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(2) button[kind="secondary"] { animation-delay: 0.08s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(3) button[kind="secondary"] { animation-delay: 0.16s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(4) button[kind="secondary"] { animation-delay: 0.24s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(5) button[kind="secondary"] { animation-delay: 0.32s; }
    div[data-testid="stVerticalBlock"] > div:nth-child(6) button[kind="secondary"] { animation-delay: 0.40s; }

    /* ── Featured Clinical Decision Engine card ── */
    button[kind="secondary"].af-featured-btn,
    div[data-testid="stVerticalBlock"] > div:first-child button[kind="secondary"] {
        background: linear-gradient(135deg, rgba(14,165,233,0.10), rgba(139,92,246,0.10));
        border: 1px solid rgba(139,92,246,0.25);
        font-size: 0.85rem;
        padding: 1rem 1.2rem;
        position: relative;
    }
    div[data-testid="stVerticalBlock"] > div:first-child button[kind="secondary"]:hover {
        border-color: rgba(139,92,246,0.5);
        background: linear-gradient(135deg, rgba(14,165,233,0.15), rgba(139,92,246,0.15));
        box-shadow:
            0 0 0 1px rgba(139,92,246,0.3),
            0 8px 32px rgba(139,92,246,0.15),
            inset 0 1px 0 rgba(255,255,255,0.06);
        transform: translateY(-3px);
    }

    /* Clinical Decision Report pill */
    .af-pill-cdr {
        background: rgba(139,92,246,0.15);
        color: #c4b5fd;
        border: 1px solid rgba(139,92,246,0.3);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.68rem;
        font-weight: 600;
    }

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
        padding: 0.16rem 0.65rem;
        font-size: 0.65rem;
        font-weight: 600;
        transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    .af-meta .af-pill:hover {
        background: rgba(14,165,233,0.2);
        border-color: rgba(14,165,233,0.4);
        transform: scale(1.07) translateY(-1px);
        box-shadow: 0 2px 8px rgba(14,165,233,0.15);
    }
    /* Vertical separator between meta groups */
    .af-meta-sep {
        width: 1px;
        height: 14px;
        background: rgba(148,163,184,0.12);
        border-radius: 1px;
        flex-shrink: 0;
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
    /* ── Tool detail cards (sidebar) ── */
    .af-tool-card {
        background: rgba(14,165,233,0.04);
        border: 1px solid rgba(14,165,233,0.1);
        border-radius: 10px;
        padding: 0.55rem 0.65rem;
        margin-bottom: 0.4rem;
        transition: all 0.25s ease;
    }
    .af-tool-card:hover {
        border-color: rgba(14,165,233,0.25);
        background: rgba(14,165,233,0.08);
    }
    .af-tool-card.af-bounty-card {
        border-color: rgba(251,191,36,0.15);
        background: rgba(251,191,36,0.04);
    }
    .af-tool-card.af-bounty-card:hover {
        border-color: rgba(251,191,36,0.3);
        background: rgba(251,191,36,0.08);
    }
    .af-tool-card-header {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        margin-bottom: 0.2rem;
    }
    .af-tool-card-icon {
        font-size: 0.85rem;
        line-height: 1;
    }
    .af-tool-card-name {
        font-size: 0.72rem;
        font-weight: 700;
        color: #e2e8f0;
        letter-spacing: 0.01em;
    }
    .af-bounty-card .af-tool-card-name {
        color: #fbbf24;
    }
    .af-tool-card-desc {
        font-size: 0.62rem;
        color: #64748b;
        line-height: 1.4;
        margin-bottom: 0.25rem;
    }
    .af-tool-card-example {
        font-size: 0.58rem;
        color: #0ea5e9;
        font-style: italic;
        opacity: 0.8;
        line-height: 1.3;
    }
    .af-bounty-card .af-tool-card-example {
        color: #fbbf24;
    }
    .af-tool-card-example::before {
        content: "Try: ";
        font-weight: 600;
        font-style: normal;
        opacity: 0.7;
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
    @keyframes inputGlowPulse {
        0%, 100% { box-shadow: 0 0 0 3px rgba(14,165,233,0.08), 0 4px 20px rgba(14,165,233,0.08); }
        50%       { box-shadow: 0 0 0 4px rgba(14,165,233,0.16), 0 6px 28px rgba(14,165,233,0.14); }
    }
    .stChatInput {
        transition: all 0.3s ease;
    }
    .stChatInput > div {
        border-radius: 16px !important;
        transition: all 0.3s ease;
    }
    .stChatInput textarea {
        border-radius: 14px;
        font-size: 0.88rem;
        padding: 0.85rem 1.1rem;
        background: rgba(15,23,42,0.65) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(14,165,233,0.15) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 8px rgba(0,0,0,0.15) !important;
    }
    .stChatInput textarea:focus {
        border-color: rgba(14,165,233,0.5) !important;
        background: rgba(15,23,42,0.8) !important;
        animation: inputGlowPulse 2s ease infinite;
        outline: none !important;
    }
    /* Send button */
    .stChatInput button {
        border-radius: 10px !important;
        background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important;
        border: none !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 2px 8px rgba(14,165,233,0.3) !important;
    }
    .stChatInput button:hover {
        transform: scale(1.08) !important;
        box-shadow: 0 4px 16px rgba(14,165,233,0.45) !important;
    }
    .stChatInput button:active {
        transform: scale(0.96) !important;
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
        /* Reduce backdrop blur on mobile for performance */
        .stChatMessage, .af-example-card, .af-tool-card, .af-sidebar-section {
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
        }
        /* Watermark smaller on mobile */
        .stApp::before {
            width: 95vw;
            height: 40vh;
            opacity: 0.05;
        }
    }

    /* Tablet: 641px–900px */
    @media (min-width: 641px) and (max-width: 900px) {
        .af-header h1 {
            font-size: 1.6rem;
        }
        .af-examples-grid {
            grid-template-columns: 1fr 1fr;
        }
        .af-tool-grid {
            grid-template-columns: 1fr 1fr;
        }
        .block-container {
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
    }

    /* Touch devices: larger tap targets */
    @media (hover: none) and (pointer: coarse) {
        .af-pill, .af-tool-chip {
            padding: 0.3rem 0.8rem !important;
            font-size: 0.75rem !important;
        }
        .stChatInput textarea {
            font-size: 16px !important; /* Prevents iOS auto-zoom on focus */
        }
        /* Disable hover-only animations on touch */
        .af-example-card:hover,
        .af-tool-card:hover,
        .af-tool-chip:hover {
            transform: none !important;
        }
    }

    /* ══════════════════════════════════════════════════════════════════
       §11  GLASSMORPHISM DEPTH LAYER
              Upgraded blur, layered shadows, inner-light border edge
       ══════════════════════════════════════════════════════════════════ */

    /* --- Chat bubbles: deeper glass + layered shadow --- */
    .stChatMessage {
        backdrop-filter: blur(20px) saturate(1.4) !important;
        -webkit-backdrop-filter: blur(20px) saturate(1.4) !important;
        box-shadow:
            0 4px 24px rgba(0,0,0,0.25),
            inset 0 1px 0 rgba(255,255,255,0.06) !important;
    }
    .stChatMessage:has([data-testid="chatAvatarIcon-user"]) {
        background: rgba(14,165,233,0.04) !important;
        border-color: rgba(14,165,233,0.15) !important;
    }
    .stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {
        background: rgba(16,185,129,0.04) !important;
        border-color: rgba(16,185,129,0.15) !important;
    }
    .stChatMessage:hover {
        box-shadow:
            0 8px 32px rgba(0,0,0,0.3),
            0 0 0 1px rgba(148,163,184,0.08),
            inset 0 1px 0 rgba(255,255,255,0.09) !important;
    }

    /* --- Example cards: richer depth --- */
    .af-example-card {
        backdrop-filter: blur(18px) saturate(1.3) !important;
        -webkit-backdrop-filter: blur(18px) saturate(1.3) !important;
        box-shadow:
            0 2px 16px rgba(0,0,0,0.2),
            inset 0 1px 0 rgba(255,255,255,0.05) !important;
    }
    .af-example-card:hover {
        box-shadow:
            0 0 0 1px rgba(14,165,233,0.25),
            0 12px 40px rgba(14,165,233,0.14),
            inset 0 1px 0 rgba(255,255,255,0.09) !important;
    }

    /* --- Tool cards (sidebar): frosted + micro-elevation --- */
    .af-tool-card {
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        box-shadow:
            0 1px 8px rgba(0,0,0,0.18),
            inset 0 1px 0 rgba(255,255,255,0.04) !important;
    }
    .af-tool-card:hover {
        box-shadow:
            0 4px 20px rgba(14,165,233,0.12),
            inset 0 1px 0 rgba(255,255,255,0.07) !important;
        transform: translateY(-1px);
    }
    .af-tool-card.af-bounty-card:hover {
        box-shadow:
            0 4px 20px rgba(251,191,36,0.12),
            inset 0 1px 0 rgba(255,255,255,0.07) !important;
    }

    /* --- Sidebar section blocks --- */
    .af-sidebar-section {
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        box-shadow:
            0 2px 12px rgba(0,0,0,0.2),
            inset 0 1px 0 rgba(255,255,255,0.05) !important;
    }
    .af-sidebar-section:hover {
        box-shadow:
            0 4px 24px rgba(14,165,233,0.1),
            inset 0 1px 0 rgba(255,255,255,0.08) !important;
    }

    /* --- Metadata bar + verification badges --- */
    .af-meta, .af-verification {
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        box-shadow:
            0 1px 8px rgba(0,0,0,0.15),
            inset 0 1px 0 rgba(255,255,255,0.04) !important;
    }

    /* --- Tool active chip (spinner) --- */
    .af-tool-active {
        backdrop-filter: blur(16px) !important;
        box-shadow:
            0 2px 12px rgba(14,165,233,0.15),
            inset 0 1px 0 rgba(255,255,255,0.05) !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       §10b  FEEDBACK ICON BUTTONS — bounce + glow state transitions
       ══════════════════════════════════════════════════════════════════ */
    @keyframes thumbBounce {
        0%   { transform: scale(1); }
        30%  { transform: scale(1.35) rotate(-8deg); }
        55%  { transform: scale(0.92) rotate(4deg); }
        75%  { transform: scale(1.1) rotate(-2deg); }
        100% { transform: scale(1) rotate(0deg); }
    }
    /* Feedback columns: shrink wrapper padding */
    div[data-testid="stHorizontalBlock"] > div:first-child button,
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background: rgba(15,23,42,0.5) !important;
        border: 1px solid rgba(148,163,184,0.1) !important;
        border-radius: 10px !important;
        width: 36px !important;
        height: 36px !important;
        min-height: 36px !important;
        padding: 0 !important;
        font-size: 1rem !important;
        line-height: 1 !important;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        backdrop-filter: blur(12px) !important;
    }
    div[data-testid="stHorizontalBlock"] > div:first-child button:hover {
        background: rgba(74,222,128,0.1) !important;
        border-color: rgba(74,222,128,0.3) !important;
        box-shadow: 0 4px 14px rgba(74,222,128,0.2) !important;
        transform: scale(1.12) !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {
        background: rgba(248,113,113,0.1) !important;
        border-color: rgba(248,113,113,0.3) !important;
        box-shadow: 0 4px 14px rgba(248,113,113,0.2) !important;
        transform: scale(1.12) !important;
    }
    div[data-testid="stHorizontalBlock"] > div:first-child button:active,
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button:active {
        animation: thumbBounce 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both !important;
    }

    /* ══════════════════════════════════════════════════════════════════
       §11  EXAMPLE CARD GRADIENT BORDER + SHINE SWEEP
       ══════════════════════════════════════════════════════════════════ */
    @keyframes cardShine {
        0%   { background-position: -200% center; opacity: 0; }
        10%  { opacity: 1; }
        90%  { opacity: 1; }
        100% { background-position: 200% center; opacity: 0; }
    }
    /* Gradient-border wrapper technique using pseudo-element */
    .af-example-card::before {
        content: "";
        position: absolute;
        inset: -1px;
        border-radius: 15px;
        background: linear-gradient(135deg,
            rgba(14,165,233,0),
            rgba(14,165,233,0.5),
            rgba(139,92,246,0.3),
            rgba(14,165,233,0)
        );
        background-size: 300% 300%;
        z-index: -1;
        opacity: 0;
        transition: opacity 0.35s ease;
    }
    .af-example-card:hover::before {
        opacity: 1;
        animation: bgShift 3s ease infinite;
    }
    @keyframes bgShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    /* Shine streak on hover */
    .af-example-card .af-example-shine {
        position: absolute;
        inset: 0;
        border-radius: 14px;
        background: linear-gradient(
            105deg,
            transparent 30%,
            rgba(255,255,255,0.06) 50%,
            transparent 70%
        );
        background-size: 200% 100%;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
    }
    .af-example-card:hover .af-example-shine {
        opacity: 1;
        animation: cardShine 0.8s ease both;
    }

    /* ══════════════════════════════════════════════════════════════════
       §11a  SIDEBAR POLISH — status indicator sonar, hover lift, metrics
       ══════════════════════════════════════════════════════════════════ */
    @keyframes sonarRing {
        0%   { transform: scale(1);   opacity: 0.6; }
        100% { transform: scale(2.8); opacity: 0; }
    }
    /* Status bar — frosted glass + sonar dot */
    .af-sidebar-status {
        backdrop-filter: blur(16px) !important;
        box-shadow: 0 1px 8px rgba(74,222,128,0.08), inset 0 1px 0 rgba(255,255,255,0.04) !important;
        transition: border-color 0.3s ease !important;
        position: relative;
    }
    .af-sidebar-status:hover {
        border-color: rgba(74,222,128,0.3) !important;
        box-shadow: 0 2px 16px rgba(74,222,128,0.12), inset 0 1px 0 rgba(255,255,255,0.06) !important;
    }
    /* Sonar ring behind the live dot */
    .af-sidebar-status .af-live-dot {
        position: relative;
    }
    .af-sidebar-status .af-live-dot::after {
        content: "";
        position: absolute;
        inset: -1px;
        border-radius: 50%;
        background: #4ade80;
        animation: sonarRing 2s ease-out infinite;
    }
    /* Metrics: brighter values */
    div[data-testid="stMetricValue"] {
        background: linear-gradient(135deg, #e2e8f0, #7dd3fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ══════════════════════════════════════════════════════════════════
       §11b  THINKING INDICATOR — three pulsing dots
       ══════════════════════════════════════════════════════════════════ */
    @keyframes dotBounce {
        0%, 80%, 100% { transform: translateY(0);   opacity: 0.35; }
        40%            { transform: translateY(-7px); opacity: 1; }
    }
    .af-thinking {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 0.65rem 1rem;
        background: rgba(14,165,233,0.06);
        border: 1px solid rgba(14,165,233,0.14);
        border-radius: 12px;
        backdrop-filter: blur(16px);
        box-shadow: 0 2px 12px rgba(14,165,233,0.1), inset 0 1px 0 rgba(255,255,255,0.05);
        animation: fadeInUp 0.25s ease both;
    }
    .af-thinking-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #38bdf8;
        letter-spacing: 0.04em;
        margin-right: 4px;
    }
    .af-thinking-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #38bdf8;
    }
    .af-thinking-dot:nth-child(2) { animation: dotBounce 1.4s ease infinite 0s; }
    .af-thinking-dot:nth-child(3) { animation: dotBounce 1.4s ease infinite 0.2s; }
    .af-thinking-dot:nth-child(4) { animation: dotBounce 1.4s ease infinite 0.4s; }

    /* ══════════════════════════════════════════════════════════════════
       §12  ENTRANCE ANIMATIONS — header, sidebar sections, metadata
       ══════════════════════════════════════════════════════════════════ */
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-16px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeInScale {
        from { opacity: 0; transform: scale(0.96); }
        to   { opacity: 1; transform: scale(1); }
    }
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    /* Header fades in from above */
    .af-header {
        animation: fadeInDown 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
    }
    /* Sidebar sections slide in from left, staggered */
    .af-sidebar-section:nth-child(1) { animation: slideInLeft 0.4s ease both 0.05s; }
    .af-sidebar-section:nth-child(2) { animation: slideInLeft 0.4s ease both 0.12s; }
    .af-sidebar-section:nth-child(3) { animation: slideInLeft 0.4s ease both 0.19s; }
    .af-sidebar-section:nth-child(4) { animation: slideInLeft 0.4s ease both 0.26s; }
    .af-sidebar-section:nth-child(5) { animation: slideInLeft 0.4s ease both 0.33s; }
    /* Tool cards in sidebar cascade in */
    .af-tool-card:nth-child(1) { animation: fadeInUp 0.35s ease both 0.1s; }
    .af-tool-card:nth-child(2) { animation: fadeInUp 0.35s ease both 0.17s; }
    .af-tool-card:nth-child(3) { animation: fadeInUp 0.35s ease both 0.24s; }
    .af-tool-card:nth-child(4) { animation: fadeInUp 0.35s ease both 0.31s; }
    .af-tool-card:nth-child(5) { animation: fadeInUp 0.35s ease both 0.38s; }
    .af-tool-card:nth-child(6) { animation: fadeInUp 0.35s ease both 0.45s; }
    /* Metadata bar scales in after message lands */
    .af-meta {
        animation: fadeInScale 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both 0.2s;
    }
    .af-verification {
        animation: fadeInScale 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both 0.3s;
    }
    /* Gauntlet badge slides in from bottom-right */
    .af-gauntlet-badge {
        animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both 0.8s;
    }

    /* ══════════════════════════════════════════════════════════════════
       §99  HIDE STREAMLIT CHROME — footer and deploy btn only
            NOTE: stToolbar and stHeader intentionally kept visible
            so the sidebar hamburger toggle remains accessible
       ══════════════════════════════════════════════════════════════════ */
    footer { display: none !important; }
    footer::after { display: none !important; }
    .stDeployButton { display: none !important; }
    /* Remove blank top padding Streamlit adds for the hidden header */
    .block-container {
        padding-top: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)


def check_backend_ready() -> bool:
    """Check if the backend API is reachable."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{API_BASE_URL.replace('/api', '')}/health")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def init_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # One-time backend readiness check
    if "backend_checked" not in st.session_state:
        st.session_state.backend_checked = True
        if not check_backend_ready():
            st.toast("Backend is starting up — first query may take a few seconds", icon="⏳")


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
        st.toast("Feedback could not be sent — backend unavailable", icon="⚠️")


def get_dashboard_stats() -> dict | None:
    """Fetch observability dashboard stats."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{API_BASE_URL}/dashboard")
            if resp.status_code == 200:
                return resp.json()
    except httpx.ConnectError:
        pass  # Dashboard stats are non-critical; sidebar gracefully hides when None
    return None


EXAMPLE_QUESTIONS = [
    ("💊", "Drug Interactions", "Check interaction between warfarin and aspirin"),
    ("🤒", "Symptom Triage", "I have a persistent headache with fever"),
    ("🩺", "Find a Provider", "Find me a cardiologist"),
    ("🛡️", "Insurance", "Does Blue Cross PPO cover an MRI?"),
    ("💉", "Medication Info", "What are the side effects of metformin?"),
    ("⚠️", "FDA Recalls", "Scan patient P001's medications for FDA recalls"),
]

# Featured complex scenario for the Clinical Decision Engine
CLINICAL_DECISION_EXAMPLE = (
    "🏥",
    "Clinical Decision Report",
    "68-year-old on metformin and lisinopril, persistent fatigue, needs an endocrinologist",
)


def main():
    init_session()

    # ── Ambient aurora background ─────────────────────────────────────
    st.markdown(
        '<div class="af-aurora"></div><div class="af-aurora-2"></div>'
        '<div class="af-gauntlet-badge">'
        '<div class="af-g-label">GAUNTLET AI</div>'
        '<div><span class="af-g-cohort">G4</span></div>'
        '</div>',
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
            <div class="af-tool-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">💊</span>
                    <span class="af-tool-card-name">Drug Interactions</span>
                </div>
                <div class="af-tool-card-desc">Check interactions between 2+ medications with severity ratings</div>
                <div class="af-tool-card-example">"Check interaction between warfarin and aspirin"</div>
            </div>
            <div class="af-tool-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">🤒</span>
                    <span class="af-tool-card-name">Symptom Triage</span>
                </div>
                <div class="af-tool-card-desc">Match symptoms to possible conditions with urgency levels</div>
                <div class="af-tool-card-example">"I have a persistent headache with fever"</div>
            </div>
            <div class="af-tool-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">💉</span>
                    <span class="af-tool-card-name">Medication Lookup</span>
                </div>
                <div class="af-tool-card-desc">Get dosage, side effects, and warnings for any drug</div>
                <div class="af-tool-card-example">"What are the side effects of metformin?"</div>
            </div>
            <div class="af-tool-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">🩺</span>
                    <span class="af-tool-card-name">Provider Search</span>
                </div>
                <div class="af-tool-card-desc">Find healthcare providers by specialty or name</div>
                <div class="af-tool-card-example">"Find me a cardiologist"</div>
            </div>
            <div class="af-tool-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">📅</span>
                    <span class="af-tool-card-name">Appointments</span>
                </div>
                <div class="af-tool-card-desc">Check appointment availability by specialty and date</div>
                <div class="af-tool-card-example">"Any dermatology openings this week?"</div>
            </div>
            <div class="af-tool-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">🛡️</span>
                    <span class="af-tool-card-name">Insurance Coverage</span>
                </div>
                <div class="af-tool-card-desc">Check if a procedure is covered by an insurance plan</div>
                <div class="af-tool-card-example">"Does Blue Cross PPO cover an MRI?"</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Bounty — FDA Recalls")
        st.markdown("""
        <div class="af-sidebar-section">
            <div class="af-tool-card af-bounty-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">📋</span>
                    <span class="af-tool-card-name">Medication Watchlist</span>
                </div>
                <div class="af-tool-card-desc">Add, list, remove, or update medications tracked per patient</div>
                <div class="af-tool-card-example">"Add metformin to patient P001's watchlist"</div>
            </div>
            <div class="af-tool-card af-bounty-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">🔍</span>
                    <span class="af-tool-card-name">Recall Check</span>
                </div>
                <div class="af-tool-card-desc">Query the live FDA API for recalls on a specific drug</div>
                <div class="af-tool-card-example">"Are there any FDA recalls on lisinopril?"</div>
            </div>
            <div class="af-tool-card af-bounty-card">
                <div class="af-tool-card-header">
                    <span class="af-tool-card-icon">⚠️</span>
                    <span class="af-tool-card-name">Watchlist Scanner</span>
                </div>
                <div class="af-tool-card-desc">Batch scan all watchlist meds against FDA recall database</div>
                <div class="af-tool-card-example">"Scan patient P001's medications for recalls"</div>
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
                st.toast("Backend unavailable — clearing local session only", icon="ℹ️")
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

        # Featured Clinical Decision Engine card (full-width, above the grid)
        cdr_icon, cdr_label, cdr_question = CLINICAL_DECISION_EXAMPLE
        if st.button(
            f"{cdr_icon} **{cdr_label}** — Comprehensive multi-tool analysis\n{cdr_question}",
            key="welcome_clinical",
            use_container_width=True,
        ):
            st.session_state.pending_example = cdr_question
            st.rerun()

        for i, (icon, label, question) in enumerate(EXAMPLE_QUESTIONS):
            if st.button(
                f"{icon} {label} — {question}",
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
    SEP = '<span class="af-meta-sep"></span>'
    pills_html = "".join(f'<span class="af-pill">⚡ {t}</span>' for t in tools)
    parts = []
    # Clinical Decision Report indicator for multi-tool responses
    if len(tools) >= 3:
        parts.append('<span class="af-pill-cdr">🏥 Clinical Decision Report</span>')
        parts.append(SEP)
    if tools:
        parts.append(pills_html)
        parts.append(SEP)
    conf_pct = int(confidence * 100)
    parts.append(
        f'<span class="af-conf-gauge"><span class="af-conf-fill {gauge_cls}" style="width:{conf_pct}%"></span></span>'
        f'<span class="{conf_cls}">🎯 {confidence:.0%}</span>'
    )
    if latency:
        parts.append(SEP)
        parts.append(f'<span class="af-latency">⏱ {latency:.0f}ms</span>')
    if sources:
        parts.append(f"📎 {len(sources)} source{'s' if len(sources) != 1 else ''}")

    # Data provenance badge — detect live API vs built-in database
    source_text = " ".join(str(s) for s in sources).lower() if sources else ""
    if "live" in source_text or "rxnorm api" in source_text or "openfda" in source_text:
        parts.append(SEP)
        parts.append('<span class="af-pill" style="background:rgba(16,185,129,0.2);color:#10b981;border-color:rgba(16,185,129,0.3)">🟢 Live API</span>')
    elif "built-in" in source_text or "agentforge" in source_text or "curated" in source_text:
        parts.append(SEP)
        parts.append('<span class="af-pill" style="background:rgba(245,158,11,0.2);color:#f59e0b;border-color:rgba(245,158,11,0.3)">📦 Built-in Data</span>')
    elif sources:
        parts.append(SEP)
        parts.append('<span class="af-pill" style="background:rgba(99,102,241,0.2);color:#818cf8;border-color:rgba(99,102,241,0.3)">✓ Verified Source</span>')

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
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
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
                    elif event_type == "clarify":
                        yield data["content"]
                    elif event_type == "error":
                        error_content = data.get("content", "")
                        if "failed to call" in error_content.lower() or "failed_generation" in error_content.lower():
                            yield (
                                "I wasn't sure how to process that request. Could you try rephrasing? "
                                "For example:\n\n"
                                "- \"I have asthma symptoms\" or \"I've been coughing and wheezing\"\n"
                                "- \"What are the side effects of albuterol?\"\n"
                                "- \"Find me a pulmonologist\"\n\n"
                                "**Disclaimer:** This information is for educational purposes only and does not "
                                "constitute medical advice. Always consult a qualified healthcare professional "
                                "for personalized medical guidance."
                            )
                        else:
                            yield f"\n\nSomething went wrong. Please try rephrasing your question."
    except httpx.ConnectError:
        yield "Cannot connect to backend. Please try again in a moment."
    except Exception:
        yield "Something went wrong. Please try rephrasing your question or start a new conversation."

    # Store metadata on session state for retrieval after streaming
    st.session_state._stream_metadata = metadata
    st.session_state._stream_full_text = full_text


def _process_message(message: str):
    """Process a user message and get agent response with streaming."""
    st.session_state.messages.append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.markdown(message)

    with st.chat_message("assistant"):
        _thinking = st.empty()
        _thinking.markdown(
            '<div class="af-thinking">'
            '<span class="af-thinking-label">Thinking</span>'
            '<span class="af-thinking-dot"></span>'
            '<span class="af-thinking-dot"></span>'
            '<span class="af-thinking-dot"></span>'
            '</div>',
            unsafe_allow_html=True,
        )
        result = send_message(message)
        _thinking.empty()

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
            error_msg = (
                "I wasn't sure how to process that request. Could you try rephrasing? "
                "For example, try asking about specific symptoms, medications, or providers."
            )
            st.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
