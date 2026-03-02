# FDA Drug Recall Monitoring — Bounty Submission

**Developer:** Joe Panetta (Giuseppe) | Gauntlet AI Cohort 4, Week 2
**Live Demo:** [agentforge-0p0k.onrender.com](https://agentforge-0p0k.onrender.com/)
**Open Source Package:** [github.com/Jojobeans1981/langchain-healthcare-tools](https://github.com/Jojobeans1981/langchain-healthcare-tools)
**Release:** [v0.1.0](https://github.com/Jojobeans1981/langchain-healthcare-tools/releases/tag/v0.1.0)

---

## The Customer

Small clinic pharmacists using OpenEMR who manage hundreds of patients on active medications. They have no automated way to cross-reference patient medication lists against FDA drug recalls. Currently this is a manual process that risks patient safety.

A pharmacist responsible for 200+ patients would need to manually check the FDA website for each medication — an impractical task that often doesn't happen until a recall makes the news.

## The Data Source

**FDA openFDA Drug Recall Enforcement API** — https://api.fda.gov/drug/enforcement.json

| Attribute | Detail |
|-----------|--------|
| Provider | U.S. Food and Drug Administration |
| Cost | Free, no API key required |
| Data | Real-time FDA enforcement/recall actions |
| Coverage | Class I (most serious), Class II, Class III recalls |
| Fields Used | recall_number, reason_for_recall, classification, status, voluntary_mandated, distribution_pattern |
| Rate Limits | 240 requests/minute without API key |
| Fallback | Graceful "no results" response if API is unreachable |

## The Features

### 1. Patient Medication Watchlist (SQLite CRUD)

**Tool:** `manage_watchlist`

Add, list, update, and remove medications being tracked for individual patients. Backed by SQLite (`data/agentforge.db`) with the `patient_watchlist` table.

- **Add:** "Add metformin to watchlist for patient P001"
- **List:** "What medications is patient P001 taking?"
- **Update:** "Update notes for warfarin on patient P001's watchlist"
- **Remove:** "Remove aspirin from patient P002's watchlist"

Soft deletes (status = 'removed') preserve audit history. Duplicate entries are handled gracefully.

### 2. Drug Recall Checker

**Tool:** `check_drug_recalls`

Query the FDA openFDA API for active recalls on any medication by brand or generic name. Returns up to 5 most recent recall actions with:

- Recall number
- Classification with severity explanation (Class I/II/III)
- Reason for recall
- Status (Ongoing/Terminated/etc.)
- Voluntary vs. mandated
- Distribution pattern

### 3. Watchlist Recall Scanner

**Tool:** `scan_watchlist_recalls`

The key differentiator: cross-reference a patient's **entire** medication list against the FDA recall database in one query.

A pharmacist asks: *"Scan patient P001's medications for recalls"* and gets:

```
FDA Recall Scan for patient P001 — checking 4 medication(s):

⚠ METFORMIN: 2 recall(s) found
  - Class II (May cause temporary health problems): NDMA contamination above limits

✓ lisinopril: No active recalls
✓ aspirin: No active recalls
✓ atorvastatin: No active recalls

SUMMARY: 2 total recall(s) found across 4 medications. Review with prescribing physician.
```

## The Impact

- **~4,500 drug recalls per year** in the US (FDA data)
- **Class I recalls** can cause serious health consequences or death
- Small clinics lack enterprise pharmacy management systems (e.g., First Databank, Medi-Span)
- This feature turns OpenEMR + AgentForge into a **proactive patient safety system**
- A pharmacist can check all patients' medications against live FDA data in natural language — no manual FDA website searches

### Clinical Decision Engine Integration

The recall tools don't just work in isolation — they integrate into AgentForge's **Clinical Decision Engine**, which autonomously orchestrates 5-7 tools from a single patient description. When a patient ID is provided, the agent automatically includes FDA recall scanning in its comprehensive Clinical Decision Report alongside drug interactions, medication reviews, symptom triage, and provider recommendations. See the [README](README.md#clinical-decision-engine) for the full feature description.

### Before AgentForge

1. Pharmacist hears about a recall on the news
2. Manually searches FDA website
3. Manually cross-references against each patient's medication list
4. Manually contacts affected patients
5. Hours of work, high chance of missed patients

### After AgentForge

1. Pharmacist asks: "Scan patient P001's medications for recalls"
2. Gets instant, structured results with severity and recall details
3. Repeats for each patient or integrates into daily workflow
4. Minutes instead of hours, zero missed patients

## Technical Details

| Component | Implementation |
|-----------|---------------|
| Database | SQLite with WAL mode, `data/agentforge.db` |
| Schema | `patient_watchlist` table with soft deletes + `last_scanned` audit timestamp + `source` tracking (`manual`/`openemr`) |
| FDA API | openFDA Drug Enforcement endpoint via httpx (URL built manually to avoid `+OR+` percent-encoding — httpx `params={}` encodes `+` to `%2B`, breaking FDA's Lucene query syntax) |
| Resilience | Exponential backoff (3 retries: 0.5s, 1s, 2s) on transient failures (ConnectError, TimeoutException) |
| Rate Limiting | 100ms throttle between API calls during batch watchlist scans |
| Tools | 3 LangChain @tool decorated functions |
| OpenEMR Integration | Auto-syncs patient medications from OpenEMR REST API (`GET /patient/{pid}/medication`) into local watchlist before scanning. Requires numeric patient IDs — non-numeric IDs use local watchlist only. |
| REST Endpoints | 5 dedicated watchlist CRUD + sync + scan endpoints at `/api/watchlist/*` |
| Tests | 244 total (62+ unit + 23 LLM judge + 10 E2E pipeline + verification + thread safety + error transparency + behavioral) |
| Eval Cases | 12 recall + 4 source grounding + 10 adversarial = 26 recall-related eval cases |
| Error Handling | Transparent error messaging: distinguishes "no recalls" from "API error/timeout/rate limited". HTTP 5xx errors retry with backoff. |

## OpenEMR REST API Integration

The watchlist tools integrate directly with OpenEMR's REST API, fulfilling the bounty requirement that **"your agent must be able to access the data source through the open source project's API."**

### How It Works

1. **Automatic Sync**: When OpenEMR is enabled (`OPENEMR_ENABLED=true`), `scan_watchlist_recalls` and `manage_watchlist(action="list")` automatically sync the patient's OpenEMR medication list into the local watchlist before processing. This means a pharmacist's scan always includes the latest prescriptions from the EHR.

2. **API Bridge**: `app/tools/watchlist_sync.py` calls `GET /apis/default/api/patient/{pid}/medication` via the existing OAuth2-authenticated `OpenEMRClient` to fetch medications. Each medication's `title` field is extracted and upserted into the SQLite watchlist with `source='openemr'`.

3. **Source Tracking**: Every watchlist entry has a `source` field (`"openemr"` or `"manual"`) so pharmacists can see which medications came from the EHR vs. manually added:

```
Medication watchlist for patient 1 (4 medications):
- metformin [OpenEMR] (notes: Auto-synced from OpenEMR) [last scanned: 2026-03-01T10:00:00+00:00]
- lisinopril [OpenEMR] (notes: Auto-synced from OpenEMR) [never scanned]
- warfarin (notes: manually added by pharmacist) [never scanned]
```

4. **REST Endpoints**: Direct CRUD via FastAPI (bypasses the chat agent for programmatic use):
   - `GET /api/watchlist/{patient_id}` — list medications
   - `POST /api/watchlist/{patient_id}` — add medication
   - `DELETE /api/watchlist/{patient_id}/{medication}` — remove medication
   - `POST /api/watchlist/{patient_id}/sync` — sync from OpenEMR
   - `POST /api/watchlist/{patient_id}/scan` — scan for recalls

5. **Graceful Degradation**: When OpenEMR is disabled or unreachable, all tools work identically to the standalone version. The integration is additive-only — zero breaking changes.

### Patient ID Mapping

| Scenario | Patient ID | OpenEMR Lookup |
|----------|-----------|----------------|
| OpenEMR enabled, numeric ID | `"1"`, `"42"` | Yes — fetches from `/patient/{id}/medication` |
| OpenEMR enabled, legacy ID | `"P001"` | No — non-numeric IDs skip OpenEMR, use local watchlist only |
| OpenEMR disabled | Any | No — all operations use local watchlist only |

### Data Flow

```
Pharmacist: "Scan patient 1's medications for recalls"
    │
    ▼
scan_watchlist_recalls("1")
    │
    ├─── 1. Sync from OpenEMR ───► GET /apis/default/api/patient/1/medication
    │         │                         └─ Returns: metformin, lisinopril, aspirin
    │         └─ Upsert into SQLite (source='openemr')
    │
    ├─── 2. Read unified watchlist from SQLite
    │         └─ metformin [OpenEMR], lisinopril [OpenEMR], aspirin [OpenEMR], warfarin [manual]
    │
    └─── 3. Check each against FDA ───► api.fda.gov/drug/enforcement.json
              └─ Returns structured recall report with source tags
```

## LLM-as-Judge Semantic Verification

Beyond regex-based verification, AgentForge includes an **LLM-as-judge** layer that semantically evaluates agent responses for safety violations that pattern matching cannot catch.

**File:** `app/verification/llm_judge.py`

### How It Works

After the 5-layer regex verification runs, a fast LLM call (Groq Llama 3.3 70B, 0 temperature) evaluates the response for:

| Check | What It Catches |
|-------|-----------------|
| `prescribes_dosage` | Specific dosage recommendations in any voice (active, passive, informational) |
| `makes_diagnosis` | Diagnostic statements ("you have diabetes", "consistent with hypertension") |
| `contradicts_tool` | Response dismisses or downplays tool findings (e.g., tool says "high severity" but response says "no significant risk") |
| `provides_harmful_info` | Lethal dose information, self-harm instructions, advising to stop prescribed medication |
| `impersonates_provider` | Speaking as a doctor, nurse, or pharmacist ("as your doctor", "I prescribe") |

### Design Principles

- **Fast:** 3-second timeout via `asyncio.wait_for` — never blocks the response pipeline
- **Cheap:** ~200 input tokens, ~50 output tokens per judgment
- **Structured:** Returns JSON with boolean flags, not free text
- **Additive-only:** Only raises flags and penalties — never overrides or removes regex-based findings
- **Fault-tolerant:** If no API key, timeout, or LLM error → falls back to regex-only verification with zero degradation

### Integration

The judge runs in both `chat()` and `chat_stream()` after `verify_response()` and before `post_process_response()`. Results are applied via `apply_judge_to_verification()` which:
- Adds domain violations for dosage/diagnosis/harmful info/impersonation
- Fails source grounding if the response contradicts tool output
- Increases hallucination risk proportional to violation severity
- Reduces confidence score (0.1 penalty per violation)

## End-to-End Pipeline Tests

**File:** `tests/test_e2e_pipeline.py`

Unlike the unit tests (which mock external APIs), the E2E tests exercise the **full pipeline** with **real FDA API calls** and real SQLite database operations — testing the actual system behavior a pharmacist would experience.

| Test | What It Verifies |
|------|-----------------|
| `test_recall_check_passes_verification` | Real FDA API response passes source grounding |
| `test_watchlist_crud_passes_verification` | Add → list → remove round-trip with verification |
| `test_scan_with_real_fda_api` | Batch scan against live FDA + verification pass |
| `test_verification_blocks_unsafe_responses` | Unsafe dosage recommendation is blocked by post-processing |
| `test_emergency_escalation_always_prepended` | Chest pain query gets 911 notice at the top |
| `test_hallucinated_response_gets_low_confidence` | "100% safe and guaranteed" gets low confidence score |
| `test_full_pipeline_safe_interaction_query` | Well-sourced response with disclaimer passes all checks |
| `test_add_then_verify_database_row` | Tool output matches exact database row (patient_id, medication_name, notes, status, source) |
| `test_remove_is_soft_delete_in_database` | Remove sets status='removed', doesn't delete the row |
| `test_scan_updates_last_scanned_timestamp` | Scanning sets last_scanned from NULL to a timestamp |

## Resilience & Production Hardening

**Exponential Backoff:** `_fetch_fda_recalls()` retries transient failures (connection errors, timeouts) up to 3 times with 0.5s → 1s → 2s backoff. HTTP errors (4xx/5xx) fail immediately since retrying won't help.

**Rate-Limit Throttling:** `scan_watchlist_recalls()` inserts a 100ms delay between FDA API calls when scanning multiple medications. The FDA allows 240 requests/minute without an API key — this throttle ensures a 20-medication scan stays well under the limit.

**Audit Trail:** Every medication gets a `last_scanned` timestamp updated after each recall scan. When listing a patient's watchlist, the pharmacist sees when each medication was last checked:

```
Medication watchlist for patient P001 (3 medications):
- metformin (notes: diabetes) [last scanned: 2026-02-28T14:30:00+00:00]
- lisinopril [last scanned: 2026-02-28T14:30:01+00:00]
- aspirin [never scanned]
```

This lets clinics identify medications that haven't been checked recently — critical for compliance.

## Scale Analysis

A clinic with **200 patients × 5 medications each = 1,000 FDA API calls** for a full clinic-wide scan.

| Metric | Value |
|--------|-------|
| FDA rate limit | 240 requests/min (no API key) |
| Throttle delay | 100ms between calls |
| Per-patient scan (5 meds) | ~0.5s (plus API latency) |
| Full clinic (200 patients) | ~2-3 minutes |
| API cost | $0.00 (free public API) |

With an API key, the rate limit increases to 480 req/min, cutting scan time in half.

## Test Coverage

| Category | Count | Description |
|----------|-------|-------------|
| Watchlist CRUD | 7 | Add, duplicate, list, empty list, remove, remove nonexistent, update notes |
| FDA API | 5 | Happy path, 404, connection error, timeout, retry with backoff |
| Batch Scan | 5 | Full scan, empty watchlist, partial failure, last_scanned update, case insensitivity |
| OpenEMR Sync | 8 | Sync adds meds, skips duplicates, unavailable fallback, non-numeric ID skip, empty list, API error, scan+sync, list source tags |
| OpenEMR Live | 10 | OAuth2 auth, practitioners, patients, appointments, provider search, appointment availability, patient medications, watchlist sync, scan with sync |
| REST Endpoints | 6 | Add/list, duplicate 409, delete, delete 404, sync 503, scan |
| Verification | 17 | Negation grounding, passive voice, refusal bypass, output validation, confidence recalibration |
| Thread Safety | 3 | Concurrent session access, different sessions, clear-and-access race |
| Error Transparency | 4 | FDA 500/429/timeout error messages, 5xx retry verification |
| DB Behavioral | 7 | Persist verification, soft delete, empty input rejection, special chars |
| LLM-as-Judge | 23 | JudgeResult state, JSON parsing, mocked LLM calls (safe/violation/timeout/error/malformed), apply_judge_to_verification |
| E2E Pipeline | 10 | Real FDA API calls, full tool→verification→post-processing pipeline, database state consistency |
| **Unit Total** | **95+** | All mocked — no API keys or running OpenEMR needed |
| **E2E Total** | **10** | Real FDA API calls — requires internet access |
| Eval: Happy Path | 6 | Add, check, scan, list, remove, multi-drug |
| Eval: Edge Case | 2 | Non-existent drug, empty watchlist |
| Eval: Adversarial | 13 | Prompt injection, prescription bait, destructive request, authority claims, hypothetical framing, translation bypass, system prompt extraction, emotional pressure, toxic dose requests |
| Eval: Multi-Step | 1 | Add medications then scan |
| Eval: Source Grounding | 1 | Recall grounding verification (response must reference recall-specific data markers) |
| **Eval Total** | **23** | Via `python -m evals.runner --category recall` |

## Files Changed/Added

| File | Change |
|------|--------|
| `app/database.py` | **Updated** — SQLite setup + schema init + `last_scanned` + `source` column migrations |
| `app/tools/drug_recall.py` | **Updated** — 3 tools with retry logic, throttling, audit timestamps, OpenEMR auto-sync |
| `app/tools/watchlist_sync.py` | **New** — OpenEMR medication sync bridge (`sync_medications_from_openemr`, `fetch_openemr_medications`) |
| `app/api/watchlist_routes.py` | **New** — 5 REST endpoints for watchlist CRUD + sync + scan |
| `app/main.py` | **Updated** — Register watchlist router |
| `app/tools/__init__.py` | **Updated** — `__all__` exports for all 9 tools (clean `from app.tools import ...` imports) |
| `app/agent/healthcare_agent.py` | Register 3 new tools (6 → 9 total) + wire LLM-as-judge into chat/stream pipeline |
| `app/agent/prompts.py` | Add tool descriptions to system prompt |
| `app/verification/llm_judge.py` | **New** — LLM-as-judge semantic verification (Groq Llama 3.3 70B, 3s timeout, additive-only) |
| `tests/test_drug_recall.py` | **Updated** — 17 unit tests + fixture isolation for OpenEMR sync |
| `tests/test_watchlist_sync.py` | **New** — 8 unit tests for OpenEMR sync layer |
| `tests/test_watchlist_routes.py` | **New** — 6 unit tests for REST API endpoints |
| `tests/test_llm_judge.py` | **New** — 23 unit tests for LLM-as-judge (JudgeResult, JSON parsing, mocked LLM calls, apply_judge) |
| `tests/test_e2e_pipeline.py` | **New** — 10 end-to-end tests with real FDA API calls + database state verification |
| `evals/test_cases.py` | Add 12 recall + 4 grounding + 10 adversarial injection eval cases |
| `evals/healthcare_eval_dataset.json` | **Updated** — 110-case eval dataset (was 56, added recall + grounding + adversarial) |
| `tests/test_openemr_live.py` | **Updated** — 10 live integration tests (added watchlist sync, patient medications, scan with sync) |
| `docker/development-easy/docker-compose.yml` | **Updated** — Added `OPENEMR_ENABLED`, credentials, and `GROQ_API_KEY` to AgentForge service |
| `pyproject.toml` | **Updated** — Split core vs server optional deps |
| `BOUNTY.md` | **Updated** — This document (added OpenEMR integration section, demo instructions) |

## Deliverables

Everything a reviewer needs to verify this bounty:

### Quick Verify (30 seconds)

```bash
# Clone and install
git clone https://github.com/Jojobeans1981/langchain-healthcare-tools.git
cd langchain-healthcare-tools
pip install -e ".[dev]"

# Verify tool imports
python -c "from app.tools import manage_watchlist, check_drug_recalls, scan_watchlist_recalls; print('3 bounty tools: OK')"

# Run bounty-specific unit tests (17 tests, no API key needed)
python -m pytest tests/test_drug_recall.py -v
```

### Full OpenEMR Integration Demo (2 minutes)

```bash
# From the repo root
cd docker/development-easy
docker compose up --detach --wait

# OpenEMR is now running at https://localhost:9300 (admin/pass)
# AgentForge is at http://localhost:8501 (Streamlit UI)
# AgentForge API is at http://localhost:8500 (Swagger at /docs)
```

Open http://localhost:8501 and ask:
- **"Scan patient 1's medications for recalls"** — AgentForge auto-syncs medications from OpenEMR, then scans each against the live FDA API. Medications from OpenEMR show `[OpenEMR]` tags.
- **"What medications is patient 1 taking?"** — Lists all medications with source tracking (`[OpenEMR]` vs manual).

Or run the live integration tests:

```bash
cd agentforge
OPENEMR_ENABLED=true OPENEMR_BASE_URL=https://localhost:9300 python -m pytest tests/test_openemr_live.py -v
```

### What's Shipped

| Deliverable | Location | How to Verify |
|-------------|----------|---------------|
| 3 bounty tools | `app/tools/drug_recall.py` | `python -c "from app.tools import manage_watchlist, check_drug_recalls, scan_watchlist_recalls; print('OK')"` |
| 28 unit tests | `tests/test_drug_recall.py` | `python -m pytest tests/test_drug_recall.py -v` (all 28 pass, <8s) |
| 23 LLM judge tests | `tests/test_llm_judge.py` | `python -m pytest tests/test_llm_judge.py -v` (all 23 pass, no API key needed) |
| 10 E2E pipeline tests | `tests/test_e2e_pipeline.py` | `python -m pytest tests/test_e2e_pipeline.py -v` (real FDA API, requires internet) |
| 23 recall eval cases | `evals/test_cases.py` | `python -m evals.runner --category recall` (requires LLM API key) |
| 110-case eval dataset | `evals/healthcare_eval_dataset.json` | Open file — 110 entries, 6 categories, 9 tools |
| Live demo | [agentforge-0p0k.onrender.com](https://agentforge-0p0k.onrender.com/) | Ask: "Check if metformin has been recalled by the FDA" |
| Open source package | [github.com/Jojobeans1981/langchain-healthcare-tools](https://github.com/Jojobeans1981/langchain-healthcare-tools) | `pip install git+https://github.com/Jojobeans1981/langchain-healthcare-tools.git` |
| Release v0.1.0 | [GitHub Releases](https://github.com/Jojobeans1981/langchain-healthcare-tools/releases/tag/v0.1.0) | `.whl` and `.tar.gz` attached |

### Full Test Suite (244 tests, all passing)

```bash
python -m pytest tests/ -v    # 244 passed in ~20 seconds
```

## Known Limitations

- **Patient ID format:** OpenEMR sync requires numeric patient IDs (matching OpenEMR's internal `patient.pid`). Clinics using alphanumeric IDs should use manual watchlist management.
- **Drug interaction database:** Local interaction database covers ~21 common drug pairs. Less common pairs fall back to RxNorm API lookup.
- **FDA API dependency:** Recall checks require internet access. If the FDA API is down, the tool reports the failure clearly rather than returning false negatives.
- **Verification scope:** The verification layer catches common safety violations (dosage recommendations, unauthorized diagnoses, unsourced claims) but is not a substitute for clinical review.
- **Rate limiting:** In-memory rate limiting resets on server restart. Production deployments with multiple workers should use a shared store (e.g., Redis).
- **Inactive medication filtering:** OpenEMR medications with a past `enddate` are filtered out during sync. Medications with unparseable dates are included as a safety measure.
- **LLM judge availability:** The LLM-as-judge layer requires a Groq or Google API key. When unavailable, the system falls back to regex-only verification with no degradation. The judge adds ~100-300ms latency per response.
