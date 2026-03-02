# Weekly Development Log — AgentForge Healthcare AI Agent

**Developer:** Joe Panetta (Giuseppe)
**Sprint:** Feb 23 - Mar 2, 2026 (7-day sprint)

---

## Day 0 — Pre-Search & Repo Exploration (Feb 23, Sun)

**Hours:** ~4 hours

**Activities:**
- Received AgentForge project assignment, chose Healthcare domain (OpenEMR)
- Ran 6 parallel Claude Code agents to explore the OpenEMR codebase:
  - REST API endpoints at `/apis/default/api/`
  - FHIR R4 resources (30+ available)
  - OAuth2 authentication flow
  - 282 database tables mapped
  - Service layer pattern (BaseService) identified
- Completed Pre-Search checklist (Phase 1-3)
- Made initial architecture decisions: LangGraph, Gemini Pro, LangSmith

**Key Decision:** Healthcare domain chosen because wrong answers can harm patients — forces rigorous verification, which is the core thesis of the project.

**Blockers:** None

---

## Day 1 — MVP Build (Feb 24, Mon)

**Hours:** ~12 hours

**Activities:**
- Built complete MVP in a single session with Claude Code:
  - FastAPI backend with `/api/chat`, `/api/chat/stream`, `/api/feedback`, `/api/dashboard` endpoints
  - 6 healthcare tools: drug_interaction_check, symptom_lookup, provider_search, appointment_availability, insurance_coverage_check, medication_lookup
  - LangGraph ReAct agent with conversation memory (MemorySaver)
  - Streamlit UI with chat interface, sidebar dashboard, feedback buttons
  - Custom observability module (TraceRecord, RequestTracer, dashboard stats)
  - 4-layer verification system (hallucination detection, confidence scoring, domain constraints, output validation)
  - 56 eval test cases (happy path, edge cases, adversarial, multi-step)
  - 124 unit tests (all passing, no API keys needed)
  - Deployed to Render (Dockerfile, single container)

**Critical Pivot:** Gemini Pro free tier quota exhausted immediately (429 RESOURCE_EXHAUSTED, limit: 0). Could not enable Google Cloud billing. Switched to Groq/Llama 3.3 70B Versatile (free, no credit card). Built multi-provider fallback architecture (Groq primary → Gemini fallback).

**Key Decision:** Mock data fallback for all 6 tools. Development and demos work without any external services. Tools transparently upgrade to live APIs when available.

**Blockers:** Gemini quota (resolved by switching to Groq)

---

## Day 2 — Bug Fixes & Safety Hardening (Feb 25, Tue)

**Hours:** ~6 hours

**Activities:**
- Fixed FORBIDDEN_PATTERNS blocking all valid responses — the regex for "recommend" was too aggressive, matching safe phrases like "I recommend consulting your doctor." Added refusal exemption patterns.
- Fixed system prompt injection failure on Render — LangGraph's `state_modifier` parameter silently failed. Switched to `ChatPromptTemplate` with `MessagesPlaceholder`.
- Fixed memory message duplication — MemorySaver checkpointer replayed prior messages. Fixed with unique thread_ids per request.
- Expanded emergency patterns from 15 to 22 (added coughing blood, vomiting blood, passing out, unresponsive, etc.)
- Added active content blocking — forbidden responses are now replaced entirely with safe refusals instead of just flagged.
- Added response-side emergency detection — scans the LLM's output text for emergency keywords and appends 911/988 notice even if the original query wasn't flagged.

**Key Decision:** Safety first. Every forbidden content match now actively blocks the response, not just flags it. This is non-negotiable for healthcare.

**Blockers:** None

---

## Day 3 — Bounty Feature & OpenEMR Integration (Feb 26, Wed)

**Hours:** ~8 hours

**Activities:**
- Built FDA Drug Recall Monitoring feature (bounty — $500 prize):
  - `manage_watchlist` — SQLite CRUD for patient medication tracking (add, list, remove, update with soft deletes)
  - `check_drug_recalls` — Query FDA openFDA Enforcement API for active recalls on any medication
  - `scan_watchlist_recalls` — Cross-reference a patient's entire medication list against FDA recall database
  - 17 unit tests for all 3 tools (mocked FDA API, temp DB, retry/timeout, audit trail)
  - 12 eval test cases for recall category (happy path + edge + adversarial + multi-step)
  - BOUNTY.md documentation
- Built OpenEMR REST API client (`app/openemr_client.py`) — sync OAuth2 client connecting provider_search, appointment_availability, and insurance_coverage tools to live OpenEMR data. Graceful fallback to mock data when OpenEMR unavailable.
- Added confidence-based LLM fallback — when primary LLM produces confidence < 0.7, auto-retries with fallback provider. Keeps the better response. Skips fallback for emergency escalations.
- Expanded eval suite from 56 to 100 test cases (added 20 adversarial + 12 recall + 4 grounding + 4 edge + 4 medication lookup cases)
- Expanded unit tests from 124 to 165 (added 36 verifier tests + 6 confidence fallback tests + 5 recall resilience tests)

**Key Decision:** The bounty feature solves a real problem — small clinic pharmacists managing 200+ patients have no automated way to cross-reference medication lists against FDA recalls. This turns OpenEMR + AgentForge into a proactive patient safety system.

**Blockers:** None

---

## Day 4 — Production Polish & Critical Fixes (Feb 27, Thu)

**Hours:** ~10 hours

**Activities:**
- Fixed Gemini fallback — Gemini 1.5 Flash was retired (404). Updated to Gemini 2.5 Flash.
- Fixed FDA API returning 404 on all queries — httpx was URL-encoding `+OR+` to `%2BOR%2B` in the openFDA search query. The FDA API requires literal `+` as the OR operator. Fixed by building the URL string manually instead of using httpx's `params={}` dict.
- Fixed LLM not echoing tool output data — added tool output collection from ToolMessages in the non-streaming path, and multiple extraction strategies for the streaming path's `on_tool_end` events.
- Fixed tripled tool output in streaming — three independent display layers were all firing: (1) `on_tool_end` injecting into stream, (2) LLM echoing tool data, (3) Streamlit `backend_response` fallback. Removed layers 1 and 3, keeping only LLM echo as the display path.
- Fixed token counting always showing 0 in streaming — `on_chat_model_end` event carries `usage_metadata` as a Python dict (not object), so `getattr()` returned 0. Added `isinstance(usage, dict)` check using `.get()`. Now correctly reports input/output/total tokens.
- Fixed LangGraph deprecation warning — migrated from `langgraph.prebuilt.create_react_agent` (deprecated) to `langchain.agents.create_agent` with new `system_prompt` parameter. Added try/except import with fallback to old API for backwards compatibility. Zero warnings.
- Fixed 3 failing critical evals (7/10 → 10/10) — Groq/Llama outputs unicode typographic right single quote (U+2019 `'`) instead of ASCII apostrophe, so `"can't"` didn't match substring `"can't"`. Added unicode normalization + keyword synonym dictionary to eval runner.
- Fixed observability data lost on restart — changed trace persistence from batched (every 10th) to immediate (every trace appended to JSONL). Added `_load_persisted_data()` to restore traces and feedback from disk on startup. Dashboard now survives Render container restarts.
- Fixed token cost calculation — was hardcoded to Gemini pricing. Added provider detection ($0.00 for Groq free tier).
- Increased `model_max_tokens` from 1024 to 2048 for more complete responses.
- Strengthened tool descriptions with "You MUST use this tool" language for Gemini compatibility.
- Strengthened source grounding in system prompt — "user cannot see tool outputs directly — they ONLY see what you write."
- Created public open source repository: `langchain-healthcare-tools`
- Wrote all documentation: AGENT_ARCHITECTURE.md, AI_COST_ANALYSIS.md, AI_DEVELOPMENT_PROCESS.md, BOUNTY.md, PRE_SEARCH.md
- Updated all docs to reflect final state: 165 tests, 5-layer verification, 10/10 critical evals (100%)

**Key Learnings:**
1. The FDA API bug was subtle — the search query `openfda.brand_name:"metformin"+OR+openfda.generic_name:"metformin"` worked perfectly in curl but failed via httpx because `params={}` percent-encodes `+` to `%2B`. The FDA API uses Lucene-style query syntax where `+` is an operator, not an encoded space.
2. LangGraph's `astream_events` v2 returns `usage_metadata` as a plain Python dict, not a dataclass — `getattr(usage, "input_tokens", 0)` silently returns 0 on dicts. Always check `isinstance()` before choosing attribute access vs `.get()`.
3. Unicode normalization is critical for eval robustness — LLMs emit typographic characters (smart quotes, em dashes) that break naive string matching. `ord("'") == 8217` vs `ord("'") == 39`.

**Blockers:** Groq rate limits (100K TPD free tier exhausted, upgraded to Developer plan). Gemini free tier (20 requests/day).

---

## Day 5 — UI Overhaul, Robustness Hardening & Final Eval (Feb 28, Fri)

**Hours:** ~10 hours

**Activities:**
- **Glass-morphism UI overhaul** — Complete visual redesign of Streamlit app with frosted-glass cards, aurora background animation, animated gradient header with shimmer effect, staggered entrance animations on welcome cards, confidence gauge visualization, chat bubble polish, custom scrollbar, and responsive mobile layout. All CSS-only, no new dependencies.
- **Expanded clinical databases** — Drug interactions 11→21 known pairs, medications 6→16 mock entries, symptom categories 5→13 with urgency levels. Added RxNorm/NIH live API integration for unknown drug pairs with automatic fallback to local database.
- **60+ symptom synonyms** — Added `SYMPTOM_SYNONYMS` dictionary mapping condition names and colloquial terms to symptom category keys (e.g., "asthma"→"cough", "migraine"→"headache", "tummy ache"→"stomach pain"). Enables natural language symptom queries that previously caused tool call failures.
- **Sidebar tool cards** — Replaced simple tool chip grid with detailed cards showing tool name, description, and example prompt for each of 9 tools. Users can see exactly what commands the AI understands.
- **Graceful error recovery (3-layer defense):**

  1. Added `failed_generation` and `failed to call` patterns to `_should_try_fallback()` so Groq tool call failures automatically trigger Gemini retry
  2. Set `handle_tool_error = True` on all 9 tools so LangGraph can self-recover from individual tool failures
  3. Added `clarify` event type — when all retries fail, users see friendly messages with example queries instead of raw API errors
- **Watermark brightness fix** — Bumped AGENTFORGE and Gauntlet G4 watermark z-index (0→1) and opacity (0.04→0.08, 0.10→0.18) to render above aurora background.
- **Zero-setup documentation** — Added prominent "Zero Setup Required — No OpenEMR Seeding Needed" sections to README.md and SUBMISSION_OVERVIEW.md explaining 3-tier data strategy.
- **Documentation accuracy sweep** — Updated all stale fallback counts across AGENT_ARCHITECTURE.md, README.md, and SUBMISSION_OVERVIEW.md to match actual expanded databases.
- **Comprehensive final submission evaluation:**
  - 165/165 unit tests passing (8.28s)
  - Python syntax OK on all 9 key source files
  - 100 eval cases covering all 9 tools
  - 27/27 BOUNTY.md criteria verified MET
  - Docker multi-stage build verified
  - Live demo URL responsive

**Key Decision:** The "failed_generation" error from Groq required defense-in-depth. A single fix wasn't enough — we needed synonym matching (prevent the bad tool call), fallback triggering (retry with Gemini), tool error handling (let the agent recover), AND user-facing clarification (graceful last resort). Four layers for one error class.

**Blockers:** Groq "failed_generation" errors on ambiguous symptom queries (resolved with 4-layer fix described above).

---

## Day 6-7 — Demo, Social Post, Final Submission (Mar 1-2)

**Planned:**
- Record 3-5 minute demo video showing:
  - Agent responding to healthcare queries
  - Drug recall bounty feature end-to-end
  - Eval results
  - Observability dashboard
- Post on X/LinkedIn tagging @GauntletAI
- Final testing and polish
- Submit all deliverables

---

## Sprint Summary

| Metric | Result |
|--------|--------|
| Tools built | 9 (6 core + 3 bounty) |
| Unit tests | 165 passing (<9s, zero external dependencies) |
| Eval cases | 100 (24 happy, 13 edge, 36 adversarial, 11 multi-step, 12 recall, 4 grounding) |
| Verification types | 5 (hallucination, source grounding, confidence, domain, output) |
| LLM providers | 2 (Groq primary, Gemini fallback) with 3-layer error recovery |
| Clinical data | 21 drug interaction pairs, 16 medications, 13 symptom categories, 60+ symptom synonyms |
| Zero-setup | Works out of the box — no OpenEMR seeding, no API keys, no database setup |
| Bounty criteria | 27/27 MET (100%) |
| Total dev cost | ~$17.25 (Claude Code) + $7/mo (Render Starter) + $0 (Groq + LangSmith) |
| Deployed | https://agentforge-0p0k.onrender.com/ |
| Open source | https://github.com/Jojobeans1981/langchain-healthcare-tools |

### Lessons Learned

1. **Always test API query encoding** — The FDA API 404 bug cost hours. Always verify that your HTTP library sends queries exactly as the API expects.
2. **Multi-provider LLM from Day 1** — Gemini quota exhaustion on Day 1 would have been catastrophic without quick Groq pivot. Build fallback support early.
3. **Mock data is essential** — Enables development, demos, and testing without external dependencies. Tools should transparently upgrade to live APIs.
4. **Safety verification is the product** — In healthcare, the verification layer IS the value proposition. A reliable agent with solid verification beats a flashy agent that hallucinates.
5. **Observability catches bugs** — Discovered forbidden pattern false positives, system prompt injection failure, and memory duplication all through observability data.
6. **Defense-in-depth for LLM errors** — A single error handling strategy is never enough. The "failed_generation" bug required 4 independent fixes (synonym matching, fallback triggering, tool error recovery, user clarification) because LLM failures are non-deterministic and manifest differently each time.
7. **Symptom synonyms matter** — Users say "asthma" not "cough with wheezing." Natural language mapping between condition names and symptom categories is essential for real-world usability.
