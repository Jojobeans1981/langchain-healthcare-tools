# AI Development Process

## AgentForge Healthcare AI Agent System

**Developer:** Joe Panetta (Giuseppe)
**Last Updated:** Feb 28, 2026

---

## 1. AI Tools Used in Development

| Tool | Purpose | Usage Pattern |
|------|---------|--------------|
| Claude Code (Opus 4.6) | Codebase analysis, implementation, debugging | Primary development tool -- wrote all code |
| Groq / Llama 3.3 70B | Primary LLM for agent reasoning | Agent runtime (free tier) |
| LangSmith | Observability, tracing, eval | Monitoring and testing (free tier) |
| Render | Cloud deployment | Hosting (Starter plan, $7/month) |
| RxNorm/RxNav API | Drug name validation | Free public NIH API |
| OpenFDA API | Medication information lookup | Free public FDA API |

---

## 2. AI-Assisted Development Decisions

### Decision 1: Repository Analysis (Feb 23)

**AI Role:** Claude Code performed deep codebase exploration
**Process:** 6 parallel research agents analyzed OpenEMR's architecture
**Findings Used:**

- Identified REST API endpoints at `/apis/default/api/` for tool integration
- Mapped FHIR R4 resources (30+) available for healthcare data
- Discovered OAuth2 authentication flow for API access
- Found 282 database tables, identified key ones (patient_data, form_encounter, etc.)
- Understood service layer pattern (BaseService) for potential contribution

**Impact:** Saved estimated 8-12 hours of manual code reading. Enabled informed architecture decisions about which OpenEMR APIs to target.

### Decision 2: LLM Provider Switch -- Gemini to Groq (Feb 24)

**AI Role:** Claude Code diagnosed the 429 RESOURCE_EXHAUSTED error and recommended Groq
**Context:** Gemini Pro free tier quota was immediately exhausted (limit: 0). User could not enable billing on Google Cloud.
**Process:**

1. Claude Code identified the error from Render deployment logs
2. Evaluated alternatives: Groq (free, no credit card), OpenAI (paid), Anthropic (paid)
3. Recommended Groq with Llama 3.3 70B Versatile (free, fast, high quality)
4. Implemented multi-provider support (LLM_PROVIDER env var)

**Decision:** Groq as primary, Gemini as optional fallback
**Impact:** Unblocked development entirely. Zero cost for LLM inference. Added multi-provider architecture for resilience.

### Decision 3: Mock Data Fallback Strategy (Feb 24)

**AI Role:** Claude Code designed the fallback architecture
**Context:** OpenEMR Docker may not be running during development or demo
**Decision:** All 6 tools have curated mock data fallbacks:

- drug_interaction_check: 10 known drug pairs from FDA/NIH sources
- symptom_lookup: 5 symptom categories from CDC/NIH/Mayo Clinic
- provider_search: Mock providers across 8 specialties
- appointment_availability: Mock calendar data
- insurance_coverage: 3 plan types (PPO, HMO, Medicare) with 15+ CPT codes each
- medication_lookup: 6 common medications from FDA labels

**Impact:** Development and demos work without any external dependencies. Tools transparently upgrade to live APIs when available.

### Decision 4: 5-Layer Verification System (Feb 24-27)

**AI Role:** Claude Code implemented the verification pipeline
**Human Role:** Defined safety rules, emergency patterns, forbidden content patterns
**Architecture:**

1. **Hallucination Detection** -- Source attribution checking, unsupported claim flagging (8 regex patterns)
2. **Source Grounding** -- Verifies response references tool-specific data markers (severity for drug checks, condition for symptoms, etc.)
3. **Confidence Scoring** -- Multi-factor score (base 0.3 + tools + sources + disclaimer - risk). Progressive capping when hallucination risk is high.
4. **Domain Constraints** -- 22 emergency patterns, 14 forbidden content patterns, 10 refusal exemptions, dosage prohibition, no diagnoses, active content blocking
5. **Output Validation** -- Length checks, tool result inclusion, error pattern detection

**Impact:** Every response is verified before reaching the user. Emergency symptoms trigger immediate escalation. Forbidden content is actively blocked and replaced with safe refusals.

### Decision 5: ReAct Agent Pattern (Feb 24)

**AI Role:** Claude Code implemented using LangGraph's create_react_agent
**Decision:** LangGraph ReAct over custom agent loop
**Rationale:**

- Built-in tool calling with automatic schema binding
- Memory checkpointing (MemorySaver) for conversation persistence
- Compatible with LangSmith tracing out of the box
- `system_prompt` parameter for system prompt injection (migrated from deprecated `state_modifier` on Day 4)

**Impact:** Robust agent with conversation memory in ~50 lines of code.

### Decision 6: LangGraph Deprecation Migration (Feb 27)

**AI Role:** Claude Code identified deprecation warning and migrated to new API
**Context:** `langgraph.prebuilt.create_react_agent` was deprecated in LangGraph v1.0+ in favor of `langchain.agents.create_agent` with a new `system_prompt` parameter.
**Process:**

1. Claude Code discovered the deprecation warning in test output
2. Inspected the new API signature (`langchain.agents.create_agent`)
3. Migrated from `ChatPromptTemplate` + `state_modifier`/`prompt` to direct `system_prompt` parameter
4. Added try/except import with fallback to old API for backwards compatibility

**Decision:** Use new `langchain.agents.create_agent` with `system_prompt`, fallback to legacy import
**Impact:** Zero deprecation warnings, cleaner code (no more ChatPromptTemplate workaround), forward-compatible with LangGraph updates.

---

## 3. Development Methodology

### Eval-Driven Development (EDD)

1. Define test cases (expected input/output/tool usage)
2. Implement feature (tool, verification rule, etc.)
3. Run eval suite (`python -m evals.runner`)
4. Iterate on failures
5. Prevent regression with unit tests

### Testing Strategy

**Unit Tests (165 tests, <9s, no API keys needed):**

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_tools.py` | 30 | Drug name resolution, procedure codes, insurance plan matching, symptom DB validation, medication mock data, interaction severity levels |
| `test_verifier.py` | 82 | Hallucination patterns, source grounding, confidence scoring + breakdown, emergency patterns, forbidden content patterns, active content blocking, refusal exemptions, progressive confidence cap, graduated domain penalty, long-response grounding, overlapping patterns |
| `test_observability.py` | 8 | TraceRecord creation, RequestTracer lifecycle, error tracking, Groq zero-cost calculation, response truncation, dashboard stats aggregation |
| `test_memory.py` | 10 | Session creation, isolation, clear, trim to max, keeps most recent messages |
| `test_routes.py` | 12 | Chat endpoint, verification pipeline, feedback up/down, dashboard stats, health, debug, input validation |
| `test_drug_recall.py` | 17 | Watchlist CRUD (7), FDA recall checker with retry/timeout (5), watchlist recall scanner with audit trail (5) |
| `test_confidence_fallback.py` | 6 | LLM fallback triggers, fallback skipping when confidence high, fallback error handling |

Run: `cd agentforge && python -m pytest tests/ -v`
Result: **165 passed, 0 failed**

**Integration Eval Suite (100 test cases, requires live LLM):**

| Category | Cases | What's Tested |
|----------|-------|---------------|
| Happy Path | 21 | Drug interactions (7), symptoms (5), providers (3), appointments (3), insurance (3) |
| Edge Cases | 12 | Non-existent drugs, vague input, invalid codes, off-topic queries, past dates, multi-drug |
| Adversarial/Safety | 36 | Emergency escalation, prompt injection, dosage manipulation (5), conflicting meds (3), role exploitation (3), disclaimer bypass (3), overdose |
| Multi-Step | 11 | 2-tool chains (symptom->drug, provider->appointment), 3-tool chains, conditional referrals |
| FDA Recall | 6 | Watchlist CRUD, single-drug recall check, multi-drug recall, watchlist scan |
| Source Grounding | 4 | Drug interaction grounding, symptom grounding, medication lookup grounding, recall grounding |

Run: `cd agentforge && python -m evals.runner --verbose`
Each test validates: keyword hits, tool selection, and latency.
Results saved to `evals/eval_results.json` and recorded in observability system.

### AI Code Generation Guidelines

- **AI generates:** API integration code, test scaffolding, tool implementations, boilerplate
- **Human reviews:** All safety-critical code, verification logic, escalation rules
- **Human writes:** Domain constraints, emergency patterns, medical disclaimers
- **Principle:** "AI accelerates, human validates" -- especially in healthcare

### Quality Gates

- All AI-generated code reviewed before commit
- Unit tests must pass 100% (`pytest tests/ -v`)
- Eval suite target: >80% pass rate
- Safety tests must pass 100% (no exceptions)
- LangSmith traces reviewed for unexpected behavior

---

## 4. Observability Architecture

### LangSmith Integration

AgentForge uses LangSmith for distributed tracing of the agent pipeline:

- **Project:** `agentforge-healthcare`
- **Env var fix:** LangChain SDK reads from `os.environ`, not Pydantic settings. Fixed by exporting at module init in `healthcare_agent.py`
- **Trace chain:** User query -> system prompt -> LLM reasoning -> tool calls -> tool results -> final response
- **Metrics captured:** Token usage, latency per step, tool invocations, error rates

### Custom Observability Module (`app/observability.py`)

Built to satisfy all 6 PRD observability requirements:

| Requirement | Implementation | Storage |
|-------------|---------------|---------|
| Trace Logging | `TraceRecord` dataclass captures full request lifecycle | `data/observability/traces.jsonl` |
| Latency Tracking | `RequestTracer` times LLM, tool, verification, and total latency | In-memory + JSONL |
| Error Tracking | Errors captured with category, error rates in dashboard | In-memory + structured logging |
| Token Usage | Input/output/total per request, $0.00 for Groq free tier | In-memory + JSONL |
| Eval Results | `record_eval_run()` stores historical eval suite results | `data/observability/eval_history.jsonl` |
| User Feedback | Thumbs up/down per response via trace_id | `data/observability/feedback.jsonl` |

### Dashboard API (`GET /api/dashboard`)

Returns aggregated stats for the Streamlit sidebar:

```json
{
  "total_requests": 42,
  "error_count": 2,
  "error_rate": 0.048,
  "avg_latency_ms": 2150.3,
  "avg_confidence": 0.72,
  "total_tokens": 89400,
  "total_cost_usd": 0.0,
  "tool_usage": {"drug_interaction_check": 15, "symptom_lookup": 12},
  "feedback": {"thumbs_up": 8, "thumbs_down": 1},
  "eval_history": [{"pass_rate": 82, "total": 56, "passed": 46}]
}
```

### Streamlit Sidebar Dashboard

The live sidebar displays:

- Request count and error count
- Average latency and average confidence
- Feedback summary (thumbs up/down counts)
- Estimated cost (per provider pricing)
- System debug panel (session ID, diagnostics endpoint)

---

## 5. AI Cost Tracking During Development

| Date | Activity | AI Tool | Tokens | Cost |
|------|----------|---------|--------|------|
| Feb 23 | Repo exploration (6 agents) | Claude Code | ~300K | ~$4.50 |
| Feb 23 | Requirements analysis | Claude Code | ~50K | ~$0.75 |
| Feb 24 | Full MVP implementation | Claude Code | ~800K | ~$12.00 |
| Feb 24 | Runtime testing (queries) | Groq Llama 3.3 | ~500K | $0.00 |
| Feb 24 | Gemini testing (quota hit) | Gemini Pro | ~100K | $0.00 |

**Total AI-assisted development cost:** ~$17.25

---

## 6. Lessons Learned

### Day 1 Observations

- Gemini Pro free tier is unreliable -- quota exhausted immediately with no warning
- Groq free tier is excellent for development and demos -- fast, free, no credit card
- Mock data strategy is essential -- never depend on external services for core functionality
- Multi-provider LLM support should be built from Day 1
- LangSmith env vars must be exported to `os.environ` -- Pydantic Settings alone is not enough

### What Worked Well

- Parallel agent exploration of large codebase (6 simultaneous agents saved ~10 hours)
- Claude Code for rapid full-stack implementation (FastAPI + Streamlit + LangChain in one session)
- Eval-driven development catches issues early
- Mock data fallback enables development without infrastructure dependencies
- 5-layer verification provides real safety value (caught forbidden patterns, missing sources, hallucination)
- Isolated unit tests (165 tests) run in <9 seconds with zero external dependencies
- Token counting fix in streaming — discovered `usage_metadata` is a dict, not an object attribute
- LangGraph deprecation migration — clean `system_prompt` parameter replaces `ChatPromptTemplate` workaround
- Unicode normalization in eval runner — Groq/Llama outputs typographic quotes (U+2019) that broke keyword matching
- Observability persistence — traces survive container restarts via JSONL append + startup restore

### What Could Improve

- Should have tested Gemini API key limits before committing to it as primary LLM
- LangSmith env var bug (not exported to os.environ) should have been caught earlier with an integration test
- Documentation should be updated continuously, not batched at the end
- Eval suite should be run more frequently during development

### AI Limitations Encountered

- LLM sometimes summarizes tool data vaguely instead of presenting specific numbers -- fixed with explicit system prompt instructions
- Agent occasionally chains unnecessary tools -- addressed with clearer tool selection guidance in system prompt
- Groq/Llama 3.3 sometimes ignores formatting instructions -- less of an issue than Gemini
- Streaming with `astream_events()` requires careful filtering to avoid yielding tool-calling chunks as response text

---

## 7. Day 2-4 Summary (Feb 25-27)

### Bugs Fixed

- **Forbidden patterns blocking valid responses:** The `FORBIDDEN_PATTERNS` regex for "recommend" was too aggressive — it matched the word "recommend" in safe contexts like "I recommend consulting your doctor." Relaxed patterns with refusal exemptions so the agent can still suggest seeking professional help without triggering content blocking. Discovered via observability (confidence was 0.0 on all responses).
- **System prompt injection failure:** LangGraph's `create_react_agent` `state_modifier` parameter silently failed on Render deployment. Switched to `ChatPromptTemplate` with `MessagesPlaceholder` for reliable system prompt injection. Found via Render deployment logs.
- **Memory message duplication:** Follow-up questions caused duplicate messages in the conversation history. Root cause: MemorySaver checkpointer was replaying prior messages. Fixed by using unique thread_ids per request (`{session_id}-{trace_id}`).

### Features Added

- **Confidence-based LLM fallback:** When primary LLM (Groq/Llama 3.3 70B) produces a response with confidence < 0.7, the system automatically retries with the fallback provider (Gemini 2.0 Flash). Keeps the better response. Skips fallback for emergency escalations.
- **OpenEMR REST API connection:** Built sync OAuth2 client (`app/openemr_client.py`) connecting provider_search, appointment_availability, and insurance_coverage tools to live OpenEMR data. Graceful fallback to mock data when OpenEMR is unavailable.
- **FDA Drug Recall Monitoring (Bounty):** 3 new tools — manage_watchlist (SQLite CRUD), check_drug_recalls (FDA openFDA API with exponential backoff), scan_watchlist_recalls (batch check with rate-limit throttling and audit timestamps). 17 unit tests, 12 eval cases.

### Safety Hardening

- **Medical safety hardening:** Expanded to 22 emergency patterns (chest pain, overdose, suicidal ideation, anaphylaxis, coughing blood, etc.) and 14 forbidden content patterns (prescribing, diagnosing, lethal dose info, impersonating doctors, dosage adjustment). Added active content blocking — forbidden responses are replaced with safe refusals, with 10 refusal exemption patterns to prevent false positives.
- **Adversarial eval suite:** 36 adversarial test cases covering prompt injection, jailbreak attempts, dosage manipulation, role exploitation, disclaimer bypass, and chain-of-thought injection.
- **Progressive confidence capping:** Hallucination risk now progressively caps confidence (risk 0.5 → cap 0.65, risk 0.8 → cap 0.35) instead of a hard threshold.
- **Response emergency detection:** Final safety net scans the LLM's response text for emergency keywords and appends 911/988 escalation notice if found, even if the original query wasn't flagged.
- **Manipulation-resistant system prompt:** Hardened against prompt injection with explicit "ignore override attempts" instructions and tool-only grounding directives.

### Testing Growth

- Unit tests: 124 → **165** (added 36 verifier tests + 6 confidence fallback tests + 5 recall resilience tests)
- Eval cases: 56 → **100** (added 20 adversarial + 12 recall + 4 grounding + 4 edge + 4 medication lookup cases)
- All 165 unit tests run in <9 seconds with zero external dependencies
