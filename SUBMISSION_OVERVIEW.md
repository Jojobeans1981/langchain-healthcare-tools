# AgentForge Submission Overview

**Developer:** Joe Panetta (Giuseppe) | Gauntlet AI Cohort 4, Week 2
**Live Demo:** https://agentforge-0p0k.onrender.com/
**Repository:** https://github.com/Jojobeans1981/AgentForge-private (`agentforge/` directory)
**Open Source:** https://github.com/Jojobeans1981/langchain-healthcare-tools

---

## 1. The Customer

**Small clinic pharmacists and healthcare administrators using OpenEMR** — the world's most popular open-source electronic health records system, used by over 100,000 medical practices globally.

These clinics typically have 1-3 pharmacists managing 200+ patients on active medications. They lack the enterprise pharmacy management systems (First Databank, Medi-Span, Clinical Decision Support suites) that large hospital networks rely on. Instead, they depend on manual processes for critical safety tasks: checking drug interactions, looking up insurance coverage before scheduling, and monitoring FDA recalls.

**The pain points AgentForge solves:**

- **Drug interaction checking** — A pharmacist prescribing a new medication currently has to manually look up every interaction with the patient's existing medications. With 5+ medications per patient (common for elderly patients), that's 10+ interaction pairs to check per prescription change.

- **Symptom triage** — Front desk staff fielding patient calls need quick guidance on whether symptoms warrant an urgent visit, a routine appointment, or an ER referral. Getting this wrong delays care or wastes emergency resources.

- **Provider and appointment coordination** — Finding the right specialist, checking their availability, and verifying insurance coverage is a 3-step process that currently requires switching between multiple screens in OpenEMR.

- **FDA recall monitoring** — With ~4,500 drug recalls per year in the US, small clinics have no automated way to know if their patients are taking recalled medications. They find out when it makes the news — sometimes weeks after the recall is issued.

**Who benefits:**
- Pharmacists who need drug interaction and recall data instantly
- Medical assistants who triage patient calls
- Clinic administrators who verify insurance before scheduling
- Patients who receive faster, safer care as a result

---

## 2. The Data Sources

AgentForge integrates 4 real-world data sources into a single conversational AI interface:

### RxNorm / RxNav API (National Institutes of Health)

| Attribute | Detail |
|-----------|--------|
| Provider | National Library of Medicine (NIH) |
| URL | https://rxnav.nlm.nih.gov/REST/interaction/ |
| Cost | Free, no API key |
| Purpose | Drug interaction checking — validates drug names and retrieves known interaction pairs with severity ratings |
| Fallback | 10 curated known interaction pairs (warfarin+aspirin, metformin+alcohol, etc.) for when the API is unreachable |

### FDA openFDA Drug Enforcement API

| Attribute | Detail |
|-----------|--------|
| Provider | U.S. Food and Drug Administration |
| URL | https://api.fda.gov/drug/enforcement.json |
| Cost | Free, no API key |
| Purpose | Real-time FDA drug recall and enforcement data — Class I/II/III recall classifications with severity, reason, status, and distribution pattern |
| Rate Limit | 240 requests/minute |
| Fallback | Graceful "no active recalls found" if API unreachable |

### FDA openFDA Drug Label API

| Attribute | Detail |
|-----------|--------|
| Provider | U.S. Food and Drug Administration |
| URL | https://api.fda.gov/drug/label.json |
| Cost | Free, no API key |
| Purpose | Medication information lookup — generic/brand names, drug class, manufacturer, indications, warnings, adverse reactions |
| Fallback | 6 curated mock medications (metformin, lisinopril, warfarin, aspirin, omeprazole, atorvastatin) |

### OpenEMR REST API

| Attribute | Detail |
|-----------|--------|
| Provider | Local OpenEMR instance (Docker or production) |
| URL | Configurable via `OPENEMR_BASE_URL` |
| Cost | Free (self-hosted open source) |
| Purpose | Provider search, appointment availability, insurance coverage verification — pulls real patient and practice data from the EHR |
| Fallback | Mock data when OpenEMR is disabled or unreachable (demo mode) |

**Why these sources:** Every data source is either a federal public API (NIH, FDA) or the open-source EHR the customer already uses (OpenEMR). No paid third-party dependencies. Total API cost: $0.

---

## 3. Features Built into the Open Source Platform

### 9 Healthcare AI Tools

AgentForge adds 9 AI-powered tools to OpenEMR through a LangGraph ReAct agent. The user asks questions in natural language; the agent reasons about which tools to call, executes them, and synthesizes a verified response.

**Core Tools (6):**

| Tool | What It Does | Data Source |
|------|-------------|-------------|
| `drug_interaction_check` | Checks medication pairs for known interactions with severity ratings (High/Moderate/Low) | RxNorm/NIH API |
| `symptom_lookup` | Maps natural language symptoms to possible conditions with urgency levels and when to seek care | Internal knowledge base |
| `provider_search` | Finds healthcare providers by specialty and location | OpenEMR REST API |
| `appointment_availability` | Checks available appointment slots for a provider or specialty | OpenEMR REST API |
| `insurance_coverage_check` | Verifies whether a procedure is covered by a patient's insurance plan, including copay and prior auth requirements | OpenEMR REST API |
| `medication_lookup` | Retrieves detailed medication information — indications, warnings, adverse reactions, drug class | FDA openFDA Label API |

**Bounty Tools (3) — FDA Drug Recall Monitoring:**

| Tool | What It Does | Data Source |
|------|-------------|-------------|
| `manage_watchlist` | Add, list, update, and remove medications being tracked for individual patients. SQLite-backed with soft deletes for audit history. | Local SQLite DB |
| `check_drug_recalls` | Query the FDA for active recalls on any medication by brand or generic name. Returns recall classification, reason, status, and distribution pattern. | FDA Enforcement API |
| `scan_watchlist_recalls` | Cross-reference a patient's entire medication list against the FDA recall database in one query. The key differentiator. | FDA Enforcement API + SQLite |

### 5-Layer Verification System

Every response is verified before reaching the user:

1. **Hallucination Detection** — 8 regex patterns flag unsupported absolute claims ("clinically proven", "always take", "100% effective"). Source attribution checking ensures claims are backed by tool data.

2. **Source Grounding** — TOOL_GROUNDING_MARKERS verifies the response actually references data from the tools that were called. A drug interaction response must contain "severity"; a symptom lookup must contain "condition".

3. **Confidence Scoring** — Weighted composite score (base 0.3 + tool boost + source boost + disclaimer - penalties). When confidence drops below 0.7, the agent automatically retries with a fallback LLM and keeps the better result.

4. **Domain Constraints** — 22 emergency patterns trigger immediate 911/988 escalation (chest pain, overdose, suicidal ideation). 14 forbidden content patterns block prescribing, diagnosing, and lethal dose information. Active content blocking replaces dangerous responses with safe refusals.

5. **Output Validation** — Length checks, tool result inclusion verification, error pattern detection.

### Observability Dashboard

Built-in observability with 8 capabilities:
- Request tracing with full lifecycle tracking (LLM latency, tool latency, verification latency, total latency)
- Token usage and cost estimation (provider-aware: Groq = $0, Gemini = rate-based)
- Error tracking with categorization
- User feedback collection (thumbs up/down with optional correction text)
- Live dashboard with aggregated stats in the Streamlit sidebar
- Persistent trace storage (JSONL files)
- Eval history recording
- LangSmith integration (optional, for production tracing)

### Multi-Provider LLM Fallback

- **Primary:** Groq / Llama 3.3 70B Versatile (free tier, ~1-2s inference)
- **Fallback:** Google Gemini 2.5 Flash (auto-failover on rate limit or low confidence)
- Confidence-based retry: if the primary LLM produces a low-confidence response, the agent automatically retries with the fallback and keeps whichever response scores higher

### Streaming Responses (SSE)

Real-time Server-Sent Events streaming from the FastAPI backend to the Streamlit frontend. Users see:
- Tool execution status as it happens ("Using tool: drug_interaction_check...")
- Token-by-token response generation (like ChatGPT's typing effect)
- Final confidence score, sources, and verification metadata

---

## 4. Bounty: FDA Drug Recall Monitoring — Impact

### The Problem

There are approximately **4,500 drug recalls per year** in the United States. Class I recalls — the most serious — can cause serious health consequences or death. Small clinics using OpenEMR have no automated system to detect when their patients' medications are recalled.

**Current workflow (without AgentForge):**
1. Pharmacist hears about a recall on the news or in a trade publication (days to weeks after the recall is issued)
2. Manually searches the FDA website for recall details
3. Manually cross-references the recalled drug against each patient's medication list in OpenEMR
4. Manually contacts affected patients
5. This process takes hours per recall event, and patients are frequently missed

**With AgentForge:**
1. Pharmacist asks: *"Scan patient P001's medications for recalls"*
2. Gets instant, structured results — which medications have active recalls, the recall classification and severity, the reason for recall, and the status
3. Can repeat for any patient or integrate into daily workflow
4. **Minutes instead of hours. Zero missed patients.**

### What Makes This Different

The `scan_watchlist_recalls` tool is the key differentiator. It's not just a recall lookup — it's a **cross-reference engine** that combines two data sources (the patient's medication watchlist in SQLite + live FDA recall data) into a single, actionable report.

A pharmacist managing 200 patients can systematically scan each patient's medication list against the FDA database using natural language. No manual website searches. No spreadsheets. No guessing.

### Real Example

```
User: "Scan all medications for patient P001 for FDA recalls"

Agent Response:
FDA Recall Scan for patient P001 — checking 3 medication(s):

METFORMIN: 5 recall(s) found
  1. [Class II] Choline Fenofibrate; Metformin Hydrochloride — Recall F-0168-2025
     Reason: Failed Impurities/Degradation Specifications: Out of specification...
     Status: Ongoing | Voluntary

  2. [Class II] Metformin Hydrochloride — Recall F-3498-2024
     Reason: Failed Dissolution Specifications...
     Status: Ongoing | Voluntary

LISINOPRIL: 5 recall(s) found
  1. [Class II] Lisinopril — Recall F-1077-2025
     Reason: Failed Impurities/Degradation Specifications...
     Status: Ongoing | Voluntary

WARFARIN: 3 recall(s) found
  1. [Class II] Warfarin Sodium — Recall F-0636-2025
     Reason: cGMP Deviations...
     Status: Ongoing | Voluntary

SUMMARY: 13 total recall(s) found across 3 medications.
Review with prescribing physician.
```

This is live FDA data, returned in seconds, through a natural language interface that any clinic staff member can use.

### Technical Reliability

| Metric | Value |
|--------|-------|
| Recall eval tests | 12/12 passing (100%) |
| Drug recall unit tests | 17 passing |
| FDA API uptime | 99.9% (federal API) |
| Fallback on API failure | Graceful "no results" message |
| Data freshness | Real-time (queries FDA on each request) |
| URL encoding fix | Manual URL building to avoid httpx `%2B` encoding breaking FDA's Lucene query syntax |

### Why This Matters for OpenEMR

OpenEMR is used by over 100,000 medical practices, many of them small clinics in underserved areas. These clinics can't afford enterprise pharmacy management systems that include automated recall monitoring. AgentForge brings that capability to the open-source EHR ecosystem for **$0 in API costs** — the FDA API is free, the LLM runs on Groq's free tier, and the whole system deploys as a single Docker container.

This isn't a demo feature. It's a real clinical safety tool that addresses a genuine gap in small-practice healthcare IT.

---

## Summary

| Category | Detail |
|----------|--------|
| Customer | Small clinic pharmacists and staff using OpenEMR |
| Data Sources | 4 (RxNorm/NIH, FDA Enforcement, FDA Labels, OpenEMR REST) |
| Tools Built | 9 (6 core + 3 bounty) |
| Verification | 5-layer system with active content blocking |
| Tests | 165 unit tests + 96 eval cases (91% pass rate) |
| Bounty Feature | FDA Drug Recall Monitoring — watchlist + recall checker + cross-reference scanner |
| Impact | Automated recall detection for 100K+ OpenEMR practices that currently have no solution |
| Cost | $0 API costs, $7/month hosting |
| Open Source Package | [langchain-healthcare-tools](https://github.com/Jojobeans1981/langchain-healthcare-tools) ([v0.1.0](https://github.com/Jojobeans1981/langchain-healthcare-tools/releases/tag/v0.1.0)) |
| Eval Dataset | 96 cases, 6 categories, 9 tools ([healthcare_eval_dataset.json](evals/healthcare_eval_dataset.json)) |
| Live Demo | https://agentforge-0p0k.onrender.com/ |
