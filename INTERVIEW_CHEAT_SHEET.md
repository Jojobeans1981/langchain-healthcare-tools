# Interview Cheat Sheet — AgentForge Healthcare AI

Quick-reference answers for demo and review. Keep answers **under 30 seconds** each.

---

## Architecture

**Q: What's the architecture?**
> Single LangGraph ReAct agent with 9 tools, running on Groq/Llama 3.3 70B. FastAPI backend, Streamlit frontend, deployed as one container on Render. Not multi-agent — one agent that reasons about which tools to call.

**Q: Why LangGraph over plain LangChain?**
> LangGraph gives me MemorySaver for conversation persistence, native `astream_events` for token streaming, and a built-in ReAct loop via `create_react_agent`. LangChain alone doesn't have state management or checkpointing.

**Q: Why Groq?**
> Free tier, no credit card, 1-2s inference on Llama 3.3 70B. Gemini is automatic fallback if Groq rate-limits or confidence drops below 0.7.

---

## Tools (9 total: 6 core + 3 bounty)

**Q: Walk me through the tools.**
> **Core 6:** Drug interaction check (RxNorm API + local DB), symptom triage (built-in curated DB), provider search, appointment availability, insurance coverage, medication lookup (FDA OpenFDA API).
> **Bounty 3:** Patient medication watchlist (SQLite CRUD), drug recall check (FDA Enforcement API), watchlist scanner (batch cross-reference).

**Q: What's the bounty feature?**
> FDA drug recall monitoring. A pharmacist adds patient medications to a watchlist, then the scanner batch-checks all of them against the live FDA recall API. Solves the problem of manually checking hundreds of patients.

---

## Verification (5 layers)

**Q: How do you prevent hallucination?**
> Five verification layers run on every response:
> 1. **Hallucination detection** — 8 regex patterns for unsupported claims
> 2. **Source grounding** — per-tool keyword markers verify the response references actual tool data
> 3. **Confidence scoring** — weighted composite (base + tool boost + source boost - penalties). Below 0.7 triggers fallback LLM retry
> 4. **Domain constraints** — 22 emergency patterns, 14 forbidden content patterns. Blocks diagnoses, dosage recommendations, replaces with safe refusals
> 5. **Output validation** — length checks, tool result inclusion, error pattern detection

**Q: What's the confidence score?**
> Composite 0-1 score. Base 0.3, +0.25 if tools were called, +0.15 if sources cited, +0.05 for disclaimer, +0.1 for multi-tool. Minus penalties for hallucination markers. Below 0.5 shows warning, below 0.7 retries with fallback LLM.

---

## Mock vs Live Data

**Q: Is this mock or live data?**
> **Both.** Each tool tries the live API first (RxNorm, FDA OpenFDA, OpenEMR) and falls back to curated local data if the API is unavailable. The UI now shows a **data provenance badge** — green "Live API" or amber "Built-in Data" — so you always know which path was used. Source text in tool output explicitly labels the data origin.

**Q: Which tools hit live APIs?**
> - `drug_interaction_check` — RxNorm API (NIH) for drug name validation, local DB for known interaction pairs
> - `medication_lookup` — FDA OpenFDA Label API
> - `check_drug_recalls` / `scan_watchlist_recalls` — FDA OpenFDA Enforcement API
> - `provider_search`, `appointment_availability`, `insurance_coverage` — OpenEMR REST API (demo mode uses built-in data)

---

## Safety

**Q: What if someone asks about a medical emergency?**
> 22 emergency keyword patterns trigger immediate 911/988 escalation notice prepended to the response. No tool call needed — the check happens before and after tool execution.

**Q: What can't the agent do?**
> It cannot prescribe, diagnose, or recommend specific dosages. 14 forbidden content patterns actively block these. Every response includes a medical disclaimer. It's an information tool, not a decision-maker.

---

## Observability

**Q: How do you monitor it?**
> Three layers: LangSmith traces (full pipeline), custom observability module (per-request TraceRecords with 17 fields), and a live Streamlit sidebar dashboard showing latency, confidence, tool usage, errors, escalations, and user feedback.

---

## Testing & Evals

**Q: How is it tested?**
> - **160 unit tests** — all tools, verification, memory, observability (run in <9s, no API keys needed)
> - **100-case eval dataset** — 9 tool categories, includes 36 adversarial cases (prompt injection, jailbreak, dosage manipulation)
> - **conftest.py autouse fixtures** — isolate global state between tests automatically

---

## Deployment

**Q: How is it deployed?**
> Single Dockerfile → Render Starter ($7/month). `supervisord` runs FastAPI (port 8000) and Streamlit (port 10000). Agent warms up on startup via FastAPI lifespan handler — no cold start on first query. Auto-deploys on git push.

---

## Cost

**Q: What does it cost to run?**
> $0/query on Groq free tier + $7/month Render hosting. FDA and RxNorm APIs are free. At 1K users doing 5 queries/day, estimated <$100/month total.

---

## Demo Flow (recommended order)

1. **Drug interaction** — "Check interaction between warfarin and aspirin" (shows severity, source badge)
2. **Symptom triage** — "I have a persistent headache with fever" (shows conditions, emergency warnings)
3. **Bounty workflow** — "Add metformin to patient P001's watchlist" → "Scan patient P001's medications for FDA recalls" (shows the full pipeline)
4. **Clinical Decision Report** — "68-year-old on metformin and lisinopril, persistent fatigue, needs an endocrinologist" (triggers 3+ tools, shows CDR badge)
5. **Safety test** — "I'm having chest pain" (shows emergency escalation)
6. **Point out** verification scorecard, data source badge, observability sidebar
