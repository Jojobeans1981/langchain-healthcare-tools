# AgentForge - Healthcare AI Agent System

**Production-ready healthcare AI agent** powered by LangChain/LangGraph + Groq/Llama 3.3, with 6 specialized medical tools, 4-layer response verification, full observability, and streaming responses. Built as an open source contribution to the OpenEMR ecosystem.

**Live Demo:** [https://agentforge-0p0k.onrender.com/](https://agentforge-0p0k.onrender.com/)
**Developer:** Joe Panetta (Giuseppe) | Gauntlet AI Cohort 4, Week 2

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Healthcare Tools | 9 (drug interaction, symptom, provider, appointment, insurance, medication, watchlist, recall checker, recall scanner) |
| Unit Tests | 124 passing (tools, verifier, observability, memory, routes, drug recall) |
| Eval Test Cases | 80 (21 happy path, 12 edge, 26 adversarial, 11 multi-step, 6 recall, 4 grounding) |
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
          | LangGraph ReAct  |             | 4-Layer           |
          | Agent            |             | Verification      |
          | (Groq/Llama 3.3) |             | System            |
          +--------+---------+             +-------------------+
                   |                       | 1. Hallucination  |
        +----------+----------+            | 2. Confidence     |
        |    |    |    |    | |            | 3. Domain Rules   |
        v    v    v    v    v v            | 4. Output Valid.  |
      +--+ +--+ +--+ +--+ +--+ +--+      +-------------------+
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
| `drug_interaction_check` | NIH RxNorm/RxNav API + 10-pair curated DB | Check interactions between 2+ medications. Severity levels: Low, Moderate, High, Contraindicated |
| `symptom_lookup` | CDC/NIH/Mayo Clinic curated DB | Map symptoms to possible conditions. 16 emergency keywords trigger immediate escalation |
| `provider_search` | Mock data + OpenEMR FHIR fallback | Find healthcare providers by specialty. 8 specialties, includes ratings and availability |
| `appointment_availability` | Mock calendar data | Check appointment slots by specialty and date range |
| `insurance_coverage_check` | 3 insurance plans (PPO/HMO/Medicare) | Coverage lookup with copays, deductibles, prior auth. 15+ CPT codes per plan |
| `medication_lookup` | FDA OpenFDA API + 6-drug mock fallback | Drug info: indications, warnings, contraindications, dosage forms, manufacturer |
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
| **Domain Constraints** | 23 emergency patterns (chest pain, overdose, suicidal ideation, anaphylaxis, etc.), 12 forbidden content patterns (dosage, diagnosis, stop medication, impersonation, lethal dose), high-severity drug interactions | Emergency escalation notice, **active content blocking** replaces forbidden content with safe refusal |
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
| **Trace Logging** | `TraceRecord` dataclass with full request lifecycle. Persisted to `data/observability/traces.jsonl` |
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

### Unit Tests (124 tests, no API keys needed)

```bash
cd agentforge
python -m pytest tests/ -v
```

| Test Module | Tests | What's Covered |
|-------------|-------|---------------|
| `test_tools.py` | 30 | Drug name resolution, procedure codes, insurance plan matching, symptom DB, medication mock data, interaction severity |
| `test_verifier.py` | 52 | Hallucination patterns, source grounding (5), confidence scoring + breakdown (9), 23 emergency regexes, 12 forbidden content patterns, active content blocking (4), output validation, full pipeline + post-processing |
| `test_observability.py` | 8 | TraceRecord creation, RequestTracer lifecycle, error tracking, Groq zero-cost, response truncation, dashboard stats aggregation |
| `test_memory.py` | 10 | Session creation, isolation, clear, trim to max, keeps most recent messages |
| `test_routes.py` | 12 | Chat endpoint, verification pipeline, feedback up/down, dashboard stats, health, debug, input validation |
| `test_drug_recall.py` | 12 | Watchlist CRUD (7), FDA recall checker with mocked API (3), watchlist recall scanner (2) |

All 124 tests pass with **zero external dependencies** — no API keys, no Docker, no database.

### Integration Eval Suite (80 test cases, requires live LLM)

```bash
cd agentforge
python -m evals.runner              # Run all 80 tests
python -m evals.runner --category adversarial --verbose
python -m evals.runner --json       # Load from JSON dataset
```

| Category | Test Cases | What's Tested |
|----------|-----------|---------------|
| **Happy Path** | 21 | Drug interactions (7), symptoms (5), providers (3), appointments (3), insurance (3) |
| **Edge Cases** | 12 | Non-existent drugs, vague input, invalid codes, off-topic queries, multi-drug input |
| **Adversarial/Safety** | 26 | Emergency escalation, prompt injection, dosage manipulation (5), conflicting meds (3), role exploitation (3), disclaimer bypass (3), overdose, stop medication |
| **Multi-Step** | 11 | Symptom->drug chain, provider->appointment chain, 3-tool chains, conditional referrals |
| **FDA Recall** | 6 | Watchlist CRUD, single-drug recall check, multi-drug recall, watchlist scan |
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
| `MODEL_MAX_TOKENS` | `1024` | Max output tokens |
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
      drug_interaction.py   # RxNorm API + 10-pair curated DB
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
    test_verifier.py        # 52 verifier unit tests
    test_observability.py   # 8 observability unit tests
    test_memory.py          # 10 memory/session unit tests
    test_routes.py          # 12 API endpoint unit tests
    test_drug_recall.py     # 12 drug recall/watchlist unit tests
  evals/
    test_cases.py           # 80 eval test case definitions
    runner.py               # Async eval runner with reporting
    healthcare_eval_dataset.json  # Published eval dataset
  ui/
    streamlit_app.py        # Streamlit chat UI with streaming
  data/
    observability/          # Trace logs, feedback, eval history (JSONL)
```

---

## Deployment

Deployed on **Render** (free tier) with single-port architecture:
- Streamlit serves on `$PORT` (public)
- FastAPI runs internally on port 8000
- Both started via `start.sh`

Live at: [https://agentforge-0p0k.onrender.com/](https://agentforge-0p0k.onrender.com/)

---

## OpenEMR Integration

AgentForge is designed to integrate with OpenEMR via its REST/FHIR APIs:
- **REST API:** `/apis/default/api/` — patients, encounters, appointments, providers
- **FHIR R4:** `/apis/default/fhir/` — 30+ FHIR resources (Patient, Medication, etc.)
- **OAuth2:** `/oauth2/default/` — authentication for API access
- **Docker dev env:** `docker/development-easy/` at `localhost:8300` (`admin`/`pass`)

Currently uses mock data with transparent fallback to live OpenEMR APIs when available.

---

## Open Source Contribution

AgentForge is an open source contribution to the OpenEMR ecosystem, adding AI-powered healthcare agent capabilities to the world's most popular open source electronic health records platform.

### What We Released

| Contribution | Description |
|---|---|
| **Healthcare Agent Package** | Complete LangGraph-based ReAct agent with 9 domain-specific tools, deployed as a reusable module within OpenEMR (`agentforge/` directory) |
| **Eval Dataset** | 80 healthcare-specific test cases published at `evals/healthcare_eval_dataset.json` — includes happy path, edge cases, adversarial inputs, multi-step reasoning, FDA recall, and source grounding scenarios for community benchmarking |
| **Verification Framework** | 5-layer response verification system (hallucination detection, source grounding, confidence scoring, domain constraints, output validation) with active content blocking, reusable for any healthcare AI application |
| **Observability Module** | Custom tracing, latency tracking, token usage, and dashboard stats module (`app/observability.py`) |

### Where to Find It

- **Repository:** [github.com/Jojobeans1981/AgentForge-private](https://github.com/Jojobeans1981/AgentForge-private) — `agentforge/` directory
- **Eval Dataset:** `agentforge/evals/healthcare_eval_dataset.json`
- **Live Demo:** [agentforge-0p0k.onrender.com](https://agentforge-0p0k.onrender.com/)

---

## License

MIT
