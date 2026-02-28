# AgentForge - Healthcare AI Agent System

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
[![Tests](https://github.com/Jojobeans1981/langchain-healthcare-tools/actions/workflows/tests.yml/badge.svg)](https://github.com/Jojobeans1981/langchain-healthcare-tools/actions/workflows/tests.yml)
![Coverage: 85%](https://img.shields.io/badge/coverage-85%25_safety--critical-brightgreen.svg)
![Tools: 9](https://img.shields.io/badge/tools-9_healthcare-orange.svg)
![Eval Cases: 100](https://img.shields.io/badge/eval_cases-100-blueviolet.svg)

> **Nine tools. Five safeguards. One-prompt clinical decision reports. Zero hallucinations.**

Small clinic pharmacists managing 200+ patients have no automated way to check drug interactions, triage symptoms, or detect FDA recalls across medication lists. AgentForge solves this — a conversational AI agent that integrates 4 real-world data sources (NIH RxNorm, FDA Enforcement, FDA Labels, OpenEMR REST API) into a single natural-language interface with 5-layer response verification. Every answer is grounded in tool output, checked for hallucinations, and blocked if it contains forbidden medical content.

**Live Demo:** [https://agentforge-0p0k.onrender.com/](https://agentforge-0p0k.onrender.com/)
**Developer:** Joe Panetta (Giuseppe) | Gauntlet AI Cohort 4, Week 2
**Test Results:** `evals/eval_results.json`

## Install

```bash
# Core library (tools + verification + observability)
pip install git+https://github.com/Jojobeans1981/langchain-healthcare-tools.git

# With web server (FastAPI + Streamlit UI)
pip install "langchain-healthcare-tools[server] @ git+https://github.com/Jojobeans1981/langchain-healthcare-tools.git"

# Development (editable install)
git clone https://github.com/Jojobeans1981/langchain-healthcare-tools.git
cd langchain-healthcare-tools
pip install -e ".[server,dev]"
```

## Use as a Library

Drop the tools, prompt, and verifier into any LangGraph agent:

```python
from app.tools import ALL_TOOLS
from app.agent.prompts import HEALTHCARE_AGENT_SYSTEM_PROMPT
from app.verification.verifier import verify_response, post_process_response

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

# Build a verified healthcare agent in 5 lines
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
agent = create_react_agent(llm, ALL_TOOLS, prompt=HEALTHCARE_AGENT_SYSTEM_PROMPT)
result = agent.invoke({"messages": [("user", "Check warfarin and aspirin interaction")]})

# Verify the response before showing to users
verification = verify_response(response_text, tools_used, original_query)
safe_response = post_process_response(response_text, verification)
```

The system prompt includes a **Clinical Decision Engine** — when users describe complex patient scenarios (multiple medications + symptoms + specialist needs), the agent autonomously orchestrates all relevant tools and produces a structured Clinical Decision Report.

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Healthcare Tools | 9 (drug interaction, symptom, provider, appointment, insurance, medication, watchlist, recall checker, recall scanner) |
| Unit Tests | 165 passing (tools, verifier, observability, memory, routes, drug recall, confidence fallback) |
| Eval Test Cases | 100 (24 happy path, 13 edge, 36 adversarial, 11 multi-step, 12 recall, 4 grounding) |
| Verification Types | 5 (hallucination, source grounding, confidence, domain, output) |
| LLM Provider | Groq/Llama 3.3 70B (primary) with Gemini Flash fallback |
| Cost Per Query | ~$0.00 (Groq free tier) |
| Single-Tool Latency | ~1-3 seconds |
| Multi-Step Latency | ~3-5 seconds |
| Streaming | Yes (SSE via FastAPI + Streamlit) |

---

## Architecture

```
                          +---------------------+
                          |   Streamlit Chat UI  |
                          |  (streaming tokens)  |
                          +----------+----------+
                                     |
                                     v
                          +---------------------+
                          |   FastAPI Backend    |
                          |  /api/chat           |
                          |  /api/chat/stream    |
                          |  /api/feedback       |
                          |  /api/dashboard      |
                          +----------+----------+
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
          +------------------+             +-------------------+
          | LangGraph ReAct  |             | 5-Layer           |
          | Agent            |             | Verification      |
          | (Groq/Llama 3.3) |             | System            |
          +--------+---------+             +-------------------+
                   |                       | 1. Hallucination  |
        +----------+----------+            | 2. Source Ground.  |
        |    |    |    |    | |            | 3. Confidence     |
        v    v    v    v    v v            | 4. Domain Rules   |
      +--+ +--+ +--+ +--+ +--+ +--+      | 5. Output Valid.  |
                                          +-------------------+
      |DI| |SL| |PS| |AA| |IC| |ML|
      +--+ +--+ +--+ +--+ +--+ +--+      +-------------------+
       |    |    |    |    |    |          | Observability     |
       v    v    v    v    v    v          | - LangSmith       |
     RxNorm CDC  Mock Mock Mock FDA       | - Custom Traces   |
     API   Data  Data Data Data API       | - Dashboard Stats |
                                          +-------------------+

DI = Drug Interaction    SL = Symptom Lookup     PS = Provider Search
AA = Appointment Avail.  IC = Insurance Coverage  ML = Medication Lookup
```

---

## 9 Healthcare Tools

| Tool | Data Source | Description |
|------|------------|-------------|
| `drug_interaction_check` | NIH RxNorm/RxNav API + 21-pair curated DB | Check interactions between 2+ medications. Severity levels: Low, Moderate, High, Contraindicated |
| `symptom_lookup` | CDC/NIH/Mayo Clinic curated DB | Map symptoms to possible conditions. 16 emergency keywords trigger immediate escalation |
| `provider_search` | Mock data + OpenEMR FHIR fallback | Find healthcare providers by specialty. 8 specialties, includes ratings and availability |
| `appointment_availability` | Mock calendar data | Check appointment slots by specialty and date range |
| `insurance_coverage_check` | 3 insurance plans (PPO/HMO/Medicare) | Coverage lookup with copays, deductibles, prior auth. 15+ CPT codes per plan |
| `medication_lookup` | FDA OpenFDA API + 16-drug mock fallback | Drug info: indications, warnings, contraindications, dosage forms, manufacturer |
| `manage_watchlist` | SQLite (patient_watchlist table) | CRUD for patient medication watchlists. Actions: add, list, remove, update. Soft deletes for audit history |
| `check_drug_recalls` | FDA openFDA Drug Enforcement API | Check active FDA recalls on any medication by brand or generic name. Returns up to 5 recent recalls |
| `scan_watchlist_recalls` | SQLite + FDA openFDA API | Cross-reference a patient's entire medication list against FDA recall database in one query |

All tools have **curated mock data fallbacks** — the system works fully offline without any external API dependencies.

---

## 5-Layer Verification System

Every response passes through 5 verification checks before reaching the user:

| Layer | What It Checks | Actions Taken |
|-------|---------------|---------------|
| **Hallucination Detection** | Source attribution, unsupported absolute claims (8 patterns), medical fact claims without tool backing | Flags risk score 0.0-1.0, adds source warning |
| **Source Grounding** | Verifies response references actual tool-specific data markers (e.g., "severity" for drug interactions, "condition" for symptoms) | Grounding failure increases hallucination risk, reduces confidence |
| **Confidence Scoring** | Multi-factor score with full breakdown: base 0.3 + tools (+0.25) + sources (+0.15) + disclaimer (+0.05) + multi-tool (+0.1) + grounding penalty - hallucination risk - violations. Capped at 0.4 when hallucination risk > 0.5 | Low confidence (<50%) adds warning to response |
| **Domain Constraints** | 22 emergency patterns (chest pain, overdose, suicidal ideation, anaphylaxis, etc.), 14 forbidden content patterns (dosage, diagnosis, stop medication, impersonation, lethal dose, dosage adjustment), 10 refusal exemption patterns, high-severity drug interactions | Emergency escalation notice, **active content blocking** replaces forbidden content with safe refusal |
| **Output Validation** | Empty/short responses, excessive length, tool result inclusion, error pattern detection | Invalid responses flagged, re-processed |

Post-processing automatically:
- **Blocks** forbidden content (replaces entire response with safe refusal)
- Adds medical disclaimer on all responses
- Adds emergency escalation notice when needed
- Adds low-confidence warning when confidence < 50%

---

## Observability

### LangSmith Integration
- Full trace logging: input -> reasoning -> tool calls -> verification -> output
- Latency breakdown per component (LLM, tool, verification)
- Token usage and cost tracking
- Project: `agentforge-healthcare`

### Custom Observability Module (`app/observability.py`)
Implements all 6 PRD observability requirements:

| Requirement | Implementation |
|-------------|---------------|
| **Trace Logging** | `TraceRecord` dataclass with full request lifecycle. Persisted immediately to `data/observability/traces.jsonl` (append-only). Restored on startup — survives container restarts |
| **Latency Tracking** | `RequestTracer` times LLM, tool, verification, and total latency per request |
| **Error Tracking** | Errors captured with category (e.g., `AuthenticationError`, `TimeoutError`). Error rates in dashboard |
| **Token Usage** | Input/output/total tokens tracked per request. Cost calculated per provider ($0.00 for Groq) |
| **Eval Results** | Historical eval runs stored in `data/observability/eval_history.jsonl`. Last 5 runs in dashboard |
| **User Feedback** | Thumbs up/down per response via trace_id. Stored in `data/observability/feedback.jsonl` |

### Live Dashboard (Sidebar)
The Streamlit sidebar displays real-time stats:
- Total requests, error count
- Average latency, average confidence
- Feedback summary (thumbs up/down)
- Estimated cost (per provider pricing)
- Tool usage breakdown

API endpoint: `GET /api/dashboard` returns aggregated stats.

---

## Testing

### Unit Tests (165 tests, no API keys needed)

```bash
cd agentforge
python -m pytest tests/ -v
```

| Test Module | Tests | What's Covered |
|-------------|-------|---------------|
| `test_tools.py` | 30 | Drug name resolution, procedure codes, insurance plan matching, symptom DB, medication mock data, interaction severity |
| `test_verifier.py` | 82 | Hallucination patterns, source grounding (5), confidence scoring + breakdown (9), 22 emergency regexes, 14 forbidden content patterns, active content blocking (4), refusal exemptions, progressive confidence cap, graduated domain penalty, long-response grounding, overlapping patterns, output validation, full pipeline + post-processing |
| `test_observability.py` | 8 | TraceRecord creation, RequestTracer lifecycle, error tracking, Groq zero-cost, response truncation, dashboard stats aggregation |
| `test_memory.py` | 10 | Session creation, isolation, clear, trim to max, keeps most recent messages |
| `test_routes.py` | 12 | Chat endpoint, verification pipeline, feedback up/down, dashboard stats, health, debug, input validation |
| `test_drug_recall.py` | 17 | Watchlist CRUD (7), FDA recall checker with retry/timeout (5), watchlist recall scanner with audit trail (5) |
| `test_confidence_fallback.py` | 6 | LLM fallback triggers, fallback skipping when confidence high, fallback error handling |

All 165 tests pass in <9 seconds with **zero external dependencies** — no API keys, no Docker, no database.

### Integration Eval Suite (100 test cases, requires live LLM)

```bash
cd agentforge
python -m evals.runner              # Run all 100 tests
python -m evals.runner --category adversarial --verbose
python -m evals.runner --json       # Load from JSON dataset
```

| Category | Test Cases | What's Tested |
|----------|-----------|---------------|
| **Happy Path** | 24 | Drug interactions (7), symptoms (5), providers (3), appointments (3), insurance (3), medication lookup (3) |
| **Edge Cases** | 13 | Non-existent drugs, vague input, invalid codes, off-topic queries, multi-drug input, unknown medication |
| **Adversarial/Safety** | 36 | Emergency escalation, prompt injection, dosage manipulation (5), conflicting meds (3), role exploitation (3), disclaimer bypass (3), overdose, stop medication |
| **Multi-Step** | 11 | Symptom->drug chain, provider->appointment chain, 3-tool chains, conditional referrals |
| **FDA Recall** | 12 | Watchlist CRUD, single-drug recall check, multi-drug recall, watchlist scan, recall-interaction cross-checks |
| **Source Grounding** | 4 | Drug interaction grounding, symptom grounding, medication lookup grounding, recall grounding |

Each test case validates:
- **Keyword hits**: Expected terms present in response
- **Tool selection**: Correct tools invoked by the agent
- **Latency**: Response time recorded per test

Results saved to `evals/eval_results.json` and recorded in the observability system.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a healthcare query. Returns: response, sources, confidence, tools_used, verification, trace_id, latency_ms, tokens |
| `POST` | `/api/chat/stream` | Stream response via SSE. Events: `token`, `tool_start`, `tool_end`, `done`, `error` |
| `POST` | `/api/feedback` | Submit thumbs up/down for a response (by trace_id) |
| `POST` | `/api/clear-session` | Clear conversation history for a session |
| `GET`  | `/api/dashboard` | Aggregated observability stats (requests, errors, latency, tokens, tool usage, feedback) |
| `GET`  | `/health` | Health check |
| `GET`  | `/debug` | System diagnostics (model, tools, provider status) |

### Example: Chat Request

```json
POST /api/chat
{
  "message": "Check interaction between warfarin and aspirin",
  "session_id": "abc-123"
}
```

### Example: Chat Response

```json
{
  "response": "Warfarin and aspirin have a HIGH severity interaction...",
  "sources": ["RxNorm/RxNav API", "FDA Drug Interaction Database"],
  "confidence": 0.75,
  "tools_used": ["drug_interaction_check"],
  "session_id": "abc-123",
  "trace_id": "a1b2c3d4",
  "latency_ms": 1842.5,
  "tokens": {"input": 1250, "output": 480, "total": 1730},
  "verification": {
    "has_sources": true,
    "confidence": 0.75,
    "needs_escalation": true,
    "hallucination_risk": 0.0,
    "domain_violations": [],
    "output_valid": true
  }
}
```

### Example: Streaming (SSE)

```
POST /api/chat/stream

data: {"type": "tool_start", "content": "drug_interaction_check"}
data: {"type": "tool_end", "content": "drug_interaction_check"}
data: {"type": "token", "content": "Warfarin"}
data: {"type": "token", "content": " and"}
data: {"type": "token", "content": " aspirin"}
...
data: {"type": "done", "content": {"tools_used": [...], "confidence": 0.75, ...}}
```

---

## Zero Setup Required — No OpenEMR Seeding Needed

Unlike other OpenEMR integrations, **AgentForge works out of the box with no database seeding, no OpenEMR Docker container, and no manual data setup.** Every tool uses a 3-tier data strategy that guarantees full functionality regardless of environment:

| Tier | Source | When Used |
| ---- | ------ | --------- |
| **1. Live OpenEMR** | OpenEMR REST API (OAuth2) | When a running OpenEMR instance is detected — pulls real patient, provider, appointment, and insurance data |
| **2. Live Public APIs** | FDA OpenFDA + NIH RxNorm | Always — drug lookups, interaction checks, and recall queries hit free federal APIs in real-time (no API keys needed) |
| **3. Built-in Clinical Data** | Curated mock datasets embedded in tool code | Automatic fallback when OpenEMR and/or public APIs are unreachable |

**How it works in practice:**

- `provider_search` → tries OpenEMR `/api/practitioner` → falls back to 8 built-in providers
- `medication_lookup` → tries FDA OpenFDA Label API → falls back to 16 curated medications
- `drug_interaction_check` → tries NIH RxNorm Interaction API → falls back to 21 curated drug pairs
- `check_drug_recalls` → queries FDA Enforcement API (always live, 99.9% uptime)
- `symptom_lookup` → 13 symptom categories with conditions, all local (no API needed)

The fallback is seamless and automatic — the user sees the same response format regardless of which tier served the data. Run `docker compose up` and start chatting immediately, or connect to a live OpenEMR instance for real patient data. Either way, all 9 tools work.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Groq API key (free: [console.groq.com](https://console.groq.com)) — primary LLM
- Google API key (optional fallback: [aistudio.google.com/apikey](https://aistudio.google.com/apikey))

### Setup

```bash
cd agentforge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env — set GROQ_API_KEY (primary), optionally GOOGLE_API_KEY (fallback)
```

### Run Locally

```bash
# Start FastAPI backend
uvicorn app.main:app --reload --port 8000

# In another terminal, start Streamlit UI
streamlit run ui/streamlit_app.py
```

### Run Tests

```bash
# Unit tests (no API key needed)
python -m pytest tests/ -v

# Integration evals (requires GROQ_API_KEY)
python -m evals.runner
python -m evals.runner --category adversarial --verbose
```

---

## Configuration

All configuration via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | LLM provider (`groq` or `gemini`) |
| `GROQ_API_KEY` | | Groq API key (primary, free tier) |
| `GOOGLE_API_KEY` | | Google Gemini API key (fallback) |
| `MODEL_NAME` | `llama-3.3-70b-versatile` | Model identifier |
| `MODEL_TEMPERATURE` | `0.1` | Response randomness (low = more deterministic) |
| `MODEL_MAX_TOKENS` | `2048` | Max output tokens |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | | LangSmith API key (optional) |
| `LANGCHAIN_PROJECT` | `agentforge-healthcare` | LangSmith project name |

---

## Project Structure

```
agentforge/
  app/
    agent/
      healthcare_agent.py   # LangGraph ReAct agent (chat + chat_stream)
      memory.py             # Conversation history (MemorySaver + trim)
      prompts.py            # System prompt with tool descriptions
    api/
      routes.py             # FastAPI endpoints (chat, stream, feedback, dashboard)
    tools/
      drug_interaction.py   # RxNorm API + 21-pair curated DB
      symptom_lookup.py     # CDC/NIH curated symptom DB
      provider_search.py    # Provider search with mock data
      appointment_availability.py  # Appointment slot lookup
      insurance_coverage.py # 3-plan insurance coverage
      medication_lookup.py  # FDA OpenFDA API + mock fallback
      drug_recall.py        # FDA recall checker + patient watchlist CRUD
    database.py             # SQLite setup for patient_watchlist table
    verification/
      verifier.py           # 5-layer verification with active content blocking
    observability.py        # Custom trace + dashboard module
    config.py               # Pydantic Settings from .env
    main.py                 # FastAPI app entry point
  tests/
    test_tools.py           # 30 tool unit tests
    test_verifier.py        # 82 verifier unit tests
    test_observability.py   # 8 observability unit tests
    test_memory.py          # 10 memory/session unit tests
    test_routes.py          # 12 API endpoint unit tests
    test_drug_recall.py     # 17 drug recall/watchlist unit tests
    test_confidence_fallback.py  # 6 confidence fallback unit tests
    test_openemr_live.py    # 7 live integration tests (skipped without OPENEMR_ENABLED=true)
  evals/
    test_cases.py           # 100 eval test case definitions
    runner.py               # Async eval runner with reporting
    healthcare_eval_dataset.json  # Published eval dataset
  ui/
    streamlit_app.py        # Streamlit chat UI with streaming
  data/
    observability/          # Trace logs, feedback, eval history (JSONL)
```

---

## Deployment

Deployed on **Render** (Starter plan, $7/month) with single-port architecture:
- Streamlit serves on `$PORT` (public)
- FastAPI runs internally on port 8000
- Both started via `start.sh`

Live at: [https://agentforge-0p0k.onrender.com/](https://agentforge-0p0k.onrender.com/)

---

## OpenEMR Integration

AgentForge connects to OpenEMR via its REST API with OAuth2 authentication:

- **REST API:** `/apis/default/api/` — practitioners, patients, appointments, insurance
- **OAuth2:** Password grant via `/oauth2/default/token` — auto-registers a client on first use
- **Docker dev env:** `docker/development-easy/` at `https://localhost:9300` (`admin`/`pass`)

**Enable live connection:**

```bash
# In agentforge/.env
OPENEMR_ENABLED=true
OPENEMR_BASE_URL=https://localhost:9300
```

When enabled, tools query OpenEMR first and fall back to mock data if unavailable. This means the system works identically in demo mode (no Docker) and live mode (with OpenEMR running).

**Run live integration tests:**

```bash
OPENEMR_ENABLED=true python -m pytest tests/test_openemr_live.py -v
```

Tests verify OAuth2 authentication, practitioner/patient queries, and tool-level integration with live data.

---

## Healthcare AI Eval Benchmark

AgentForge publishes a **100-case evaluation dataset** for benchmarking healthcare AI agents — the largest open-source healthcare agent eval we're aware of.

**File:** [`evals/healthcare_eval_dataset.json`](evals/healthcare_eval_dataset.json)

| Category | Cases | What It Tests |
|----------|-------|---------------|
| Happy Path | 24 | Standard drug interaction, symptom, provider, appointment, insurance, medication queries |
| Edge Cases | 13 | Missing data, boundary conditions, unusual inputs, unknown drugs, unknown medications |
| Adversarial | 36 | Prompt injection, dosage manipulation, role exploitation, disclaimer bypass |
| Multi-Step | 11 | Multi-tool reasoning chains, conditional referrals |
| FDA Recall | 12 | Watchlist CRUD, single/multi-drug recall checks, watchlist scanning |
| Source Grounding | 4 | Verifies responses reference actual tool-specific data markers |

**How to use it with your own agent:**

```python
import json

dataset = json.load(open("evals/healthcare_eval_dataset.json"))
for case in dataset["test_cases"]:
    response = your_agent.invoke(case["query"])
    # Check: correct tools called, expected keywords present, safety constraints met
```

Each case includes `query`, `expected_tools`, `expected_keywords`, `category`, and `expected_behavior`. Works with any LangChain-compatible agent.

---

## Open Source Contribution — A Complete Clinical Safety Platform

AgentForge isn't a collection of disconnected tools — it's an integrated clinical safety platform where every piece feeds into the next. Here's the pipeline:

```text
Patient message
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  CLINICAL DECISION ENGINE (prompt orchestration)            │
│  Detects complex scenarios → chains 5-7 tools automatically │
└────────────────────┬────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌─────────┐  ┌────────────┐  ┌──────────────┐
│ 9 Tools │  │ FDA Recall │  │ Drug         │
│ (RxNorm, │  │ Tracker    │  │ Interaction  │
│  FDA,    │  │ (live API  │  │ Checker      │
│  OpenEMR)│  │  + SQLite) │  │ (21 pairs)   │
└────┬─────┘  └─────┬──────┘  └──────┬───────┘
     │              │                │
     └──────────────┼────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  5-LAYER VERIFICATION                                       │
│  Hallucination ─► Source Grounding ─► Confidence ─►         │
│  Domain Rules ─► Output Validation                          │
│  Blocks unsafe content, flags low confidence, adds sources  │
└────────────────────┬────────────────────────────────────────┘
                     ▼
           Verified Clinical Report
```

**The key insight:** The recall tracker doesn't just check for recalls — it feeds into the Clinical Decision Engine, which cross-references recalls against drug interactions and symptom data, producing a single verified report. The verification system catches hallucinations across the entire pipeline, not just individual tool outputs. Everything is connected.

### What This Means for OpenEMR

OpenEMR is the world's most popular open-source EHR, used by clinics that can't afford enterprise pharmacy management systems ($50K+/year for First Databank, Medi-Span). AgentForge gives them:

| Capability | Enterprise Equivalent | AgentForge |
| --- | --- | --- |
| Drug interaction alerts | First Databank ($50K/yr) | `drug_interaction_check` — free, 21 curated pairs + live RxNorm API |
| FDA recall monitoring | Medi-Span ($30K/yr) | `scan_watchlist_recalls` — free, live FDA API, per-patient tracking |
| Clinical decision support | Epic CDS ($200K+/yr) | Clinical Decision Engine — 5-7 tools orchestrated per query, structured reports |
| Response safety | Manual pharmacist review | 5-layer automated verification with active content blocking |

Total cost: **$0.00/query** (Groq free tier) + **$7/month** hosting (Render).

### Shipped as a Reusable Package

Everything is pip-installable — any LangChain developer can build a verified healthcare agent in 5 lines:

```python
from app.tools import ALL_TOOLS
from app.agent.prompts import HEALTHCARE_AGENT_SYSTEM_PROMPT
from app.verification.verifier import verify_response, post_process_response
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(llm, ALL_TOOLS, prompt=HEALTHCARE_AGENT_SYSTEM_PROMPT)
```

The Clinical Decision Engine, recall tracker, verification system, and all 9 tools ship as one package. No cherry-picking components — the safety guarantees only work when the full pipeline is connected.

### Where to Find It

- **Standalone Package:** [github.com/Jojobeans1981/langchain-healthcare-tools](https://github.com/Jojobeans1981/langchain-healthcare-tools) — `pip install` ready
- **OpenEMR Integration:** [github.com/Jojobeans1981/AgentForge-private](https://github.com/Jojobeans1981/AgentForge-private) — `agentforge/` directory
- **100-Case Eval Dataset:** [`evals/healthcare_eval_dataset.json`](evals/healthcare_eval_dataset.json) — benchmark your own healthcare agent
- **Live Demo:** [agentforge-0p0k.onrender.com](https://agentforge-0p0k.onrender.com/) — try the Clinical Decision Engine card

---

## License

MIT
