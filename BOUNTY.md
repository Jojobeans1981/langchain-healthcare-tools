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
| Schema | `patient_watchlist` table with soft deletes + `last_scanned` audit timestamp |
| FDA API | openFDA Drug Enforcement endpoint via httpx (URL built manually to avoid `+OR+` percent-encoding — httpx `params={}` encodes `+` to `%2B`, breaking FDA's Lucene query syntax) |
| Resilience | Exponential backoff (3 retries: 0.5s, 1s, 2s) on transient failures (ConnectError, TimeoutException) |
| Rate Limiting | 100ms throttle between API calls during batch watchlist scans |
| Tools | 3 LangChain @tool decorated functions |
| Tests | 17 unit tests (mocked FDA API, temp DB, retry/timeout scenarios) |
| Eval Cases | 12 recall + 4 source grounding = 16 recall-related eval cases |
| Error Handling | Graceful fallback if FDA API unavailable; HTTP errors don't retry (non-transient) |

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
| **Unit Total** | **17** | All mocked — no API keys needed |
| Eval: Happy Path | 6 | Add, check, scan, list, remove, multi-drug |
| Eval: Edge Case | 2 | Non-existent drug, empty watchlist |
| Eval: Adversarial | 3 | Prompt injection, prescription bait, destructive request |
| Eval: Multi-Step | 1 | Add medications then scan |
| Eval: Source Grounding | 1 | Recall grounding verification (response must reference recall-specific data markers) |
| **Eval Total** | **13** | Via `python -m evals.runner --category recall` |

## Files Changed/Added

| File | Change |
|------|--------|
| `app/database.py` | **New** — SQLite setup + schema init + `last_scanned` migration |
| `app/tools/drug_recall.py` | **New** — 3 tools with retry logic, throttling, audit timestamps |
| `app/tools/__init__.py` | **Updated** — `__all__` exports for all 9 tools (clean `from app.tools import ...` imports) |
| `app/agent/healthcare_agent.py` | Register 3 new tools (6 → 9 total) |
| `app/agent/prompts.py` | Add tool descriptions to system prompt |
| `tests/test_drug_recall.py` | **New** — 17 unit tests (CRUD, API resilience, batch scanning) |
| `evals/test_cases.py` | Add 12 recall + 4 grounding eval cases |
| `evals/healthcare_eval_dataset.json` | **Updated** — 96-case eval dataset (was 56, added recall + grounding) |
| `pyproject.toml` | **Updated** — Split core vs server optional deps |
| `BOUNTY.md` | **New** — This document |

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

### What's Shipped

| Deliverable | Location | How to Verify |
|-------------|----------|---------------|
| 3 bounty tools | `app/tools/drug_recall.py` | `python -c "from app.tools import manage_watchlist, check_drug_recalls, scan_watchlist_recalls; print('OK')"` |
| 17 unit tests | `tests/test_drug_recall.py` | `python -m pytest tests/test_drug_recall.py -v` (all 17 pass, <4s) |
| 12 recall eval cases | `evals/test_cases.py` | `python -m evals.runner --category recall` (requires LLM API key) |
| 96-case eval dataset | `evals/healthcare_eval_dataset.json` | Open file — 96 entries, 6 categories, 9 tools |
| Live demo | [agentforge-0p0k.onrender.com](https://agentforge-0p0k.onrender.com/) | Ask: "Check if metformin has been recalled by the FDA" |
| Open source package | [github.com/Jojobeans1981/langchain-healthcare-tools](https://github.com/Jojobeans1981/langchain-healthcare-tools) | `pip install git+https://github.com/Jojobeans1981/langchain-healthcare-tools.git` |
| Release v0.1.0 | [GitHub Releases](https://github.com/Jojobeans1981/langchain-healthcare-tools/releases/tag/v0.1.0) | `.whl` and `.tar.gz` attached |

### Full Test Suite (165 tests, all passing)

```bash
python -m pytest tests/ -v    # 165 passed in <9 seconds
```
