# Agent Architecture Document
## AgentForge Healthcare AI Agent System

---

## 1. Domain & Use Cases

**Domain:** Healthcare (OpenEMR integration)

**Why Healthcare:** Wrong answers can harm patients. Healthcare has well-defined verification requirements (drug interactions, dosage limits), established authoritative data sources (FDA, RxNorm, OpenEMR), and measurable safety metrics. The high-stakes nature forces rigorous verification — the core thesis of AgentForge.

**Problems Solved:**
- **Drug interaction safety:** Cross-reference medication pairs against known interactions with severity ratings
- **Symptom triage:** Natural language symptoms mapped to possible conditions with urgency levels and emergency escalation
- **Provider discovery:** Find specialists by specialty/location with available appointment slots
- **Insurance verification:** Check procedure coverage before scheduling to reduce claim denials
- **FDA recall monitoring (Bounty):** Cross-reference patient medication watchlists against live FDA recall data for small clinic pharmacists

---

## 2. Agent Architecture

**Framework:** LangGraph `create_react_agent` (ReAct pattern)

**Why LangGraph:** Started with LangChain (per Pre-Search), upgraded to LangGraph for built-in checkpointer (memory), streaming support, and native ReAct loop. Low-risk upgrade since LangGraph extends LangChain.

**Reasoning Flow:**
1. Receive natural language query
2. Reason about which tool(s) to call (chain-of-thought via Llama 3.3 70B)
3. Execute tool(s) and observe structured results
4. Decide if more tools needed (multi-step)
5. Synthesize final response grounded in tool output
6. Run 5-layer verification before returning

**LLM Stack:**
- **Primary:** Groq / Llama 3.3 70B Versatile (free, ~1-2s inference)
- **Fallback:** Gemini 1.5 Flash (auto-failover on rate limit or confidence < 0.7)
- **Pivot:** Pre-Search planned Gemini Pro primary, but quota exhausted Day 1 → switched to Groq

**9 Tools:**

| Tool | Data Source | Fallback |
|------|-----------|----------|
| drug_interaction_check | RxNorm/RxNav (NIH) | 10 known pairs |
| symptom_lookup | Internal KB | 5 symptom categories |
| provider_search | OpenEMR REST API | Mock providers |
| appointment_availability | OpenEMR REST API | Mock slots |
| insurance_coverage_check | OpenEMR REST API | Mock plans |
| medication_lookup | FDA OpenFDA API | 6 mock medications |
| manage_watchlist | SQLite | — |
| check_drug_recalls | FDA Enforcement API | — |
| scan_watchlist_recalls | FDA + SQLite | — |

**Memory:** LangGraph MemorySaver with unique thread_ids per request (`{session_id}-{trace_id}`) preventing message duplication.

---

## 3. Verification Strategy

5 verification types implemented (requirement: 3+):

| Type | What It Does | Why |
|------|-------------|-----|
| Hallucination Detection | Flags claims not grounded in tool output via TOOL_GROUNDING_MARKERS | Unsourced healthcare claims are dangerous |
| Confidence Scoring | Weighted composite (tool_grounding 0.30, hallucination 0.25, domain 0.20, source 0.15, length 0.10). < 0.7 triggers fallback LLM | Surfaces uncertainty, enables automatic retry |
| Domain Constraints | FORBIDDEN_PATTERNS block prescribing/diagnosing. 30 emergency patterns trigger 911/988 escalation | Non-negotiable safety rails |
| Output Validation | Schema checks, format validation, completeness | Ensures structured responses |
| Source Grounding | Verifies response references actual tool data | Prevents fabricated medical info |

**Post-processing safety net:** `post_process_response()` runs after verification on both streaming and non-streaming paths — final regex catch for dangerous content.

---

## 4. Eval Results

**Dataset:** 80 test cases across 6 categories:

| Category | Count | Description |
|----------|-------|-------------|
| Happy Path | 21 | Drug interactions, symptoms, providers, medications |
| Edge Case | 12 | Missing data, boundary conditions, ambiguous queries |
| Adversarial | 26 | Prompt injection, jailbreak, medical manipulation |
| Multi-Step | 11 | Symptom → provider → appointment chains |
| Recall | 6 | Watchlist CRUD, FDA API integration |
| Grounding | 4 | Source attribution, hallucination detection |

Each case includes: input query, expected tool calls, expected keywords, and pass/fail criteria.

**Unit Tests (160 passing, 6.04s, Feb 27 2026):**

| Test File | Tests | What It Covers |
|-----------|-------|---------------|
| test_confidence_fallback.py | 6 | LLM fallback triggers, error handling |
| test_drug_recall.py | 12 | Watchlist CRUD, FDA API, recall scanner |
| test_memory.py | 10 | Session management, history trimming |
| test_observability.py | 8 | Tracing, latency, token tracking |
| test_routes.py | 12 | Chat, stream, feedback, dashboard endpoints |
| test_tools.py | 24 | Drug interactions, insurance, symptoms, medications |
| test_verifier.py | 88 | All 5 verification layers, safety patterns, content blocking |
| **TOTAL** | **160** | **All pass, zero failures** |

**Integration Eval Results — Critical Smoke Tests (Feb 27, 2026):**

| Category | Cases | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| Happy Path | 5 | 3 | 2 | 60.0% |
| Adversarial | 3 | 2 | 1 | 66.7% |
| Multi-Step | 2 | 2 | 0 | 100.0% |
| **TOTAL** | **10** | **7** | **3** | **70.0%** |

**Average latency:** 1.88s per query (Groq/Llama 3.3 70B)

**Failure analysis:** All 3 failures are keyword-matching strictness — the LLM paraphrased instead of echoing exact terms. Tools were invoked correctly and responses were medically appropriate. Full 80-case suite available via `python -m evals.runner`.

---

## 5. Observability Setup

**Stack:** Custom module (`app/observability.py`) + LangSmith integration

| Capability | Implementation |
|-----------|---------------|
| Trace Logging | TraceRecord (17 fields) persisted to JSONL per request |
| Latency Tracking | 4-way: `llm_latency_ms`, `tool_latency_ms`, `verification_latency_ms`, `total_latency_ms` |
| Error Tracking | `error` + `error_type` categorized (tool_error, llm_error, verification_failure) |
| Token Usage | `input_tokens`, `output_tokens`, `cost_estimate` per request |
| Eval Results | `eval_history` with pass rates and category breakdown |
| User Feedback | Thumbs up/down via `/api/feedback`, stored per trace_id |

**Dashboard:** `GET /api/dashboard` powers Streamlit sidebar with live stats.

**Key Insights From Observability:**
- Discovered FORBIDDEN_PATTERNS blocking all valid responses (confidence was 0.0)
- Identified system prompt injection failure via logs (`state_modifier not supported`)
- Found memory duplication bug through trace analysis

---

## 6. Open Source Contribution

**Type:** New Agent Package

**Package:** `langchain-healthcare-tools`
- 9 healthcare-specific LangChain tools for any LangGraph/LangChain agent
- 5-layer medical verification system
- 80-case eval dataset for healthcare agent benchmarking
- MIT licensed

**Install from GitHub:**
```bash
pip install git+https://github.com/Jojobeans1981/AgentForge-private.git#subdirectory=agentforge
```

**Bounty:** FDA Drug Recall Monitoring — 3 tools cross-referencing patient medication lists against live FDA recall data. Documented in BOUNTY.md.

**Deployed:** https://agentforge-0p0k.onrender.com/
