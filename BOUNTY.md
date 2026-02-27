# FDA Drug Recall Monitoring — Bounty Submission

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
| Schema | `patient_watchlist` table with soft deletes |
| FDA API | openFDA Drug Enforcement endpoint via httpx |
| Tools | 3 LangChain @tool decorated functions |
| Tests | 12 unit tests (mocked FDA API, temp DB) |
| Eval Cases | 6 new test cases in recall category |
| Error Handling | Graceful fallback if FDA API unavailable |

## Files Changed/Added

| File | Change |
|------|--------|
| `app/database.py` | **New** — SQLite setup + schema init |
| `app/tools/drug_recall.py` | **New** — 3 tools (manage_watchlist, check_drug_recalls, scan_watchlist_recalls) |
| `app/agent/healthcare_agent.py` | Register 3 new tools (6 → 9 total) |
| `app/agent/prompts.py` | Add tool descriptions to system prompt |
| `tests/test_drug_recall.py` | **New** — 12 unit tests |
| `evals/test_cases.py` | Add 6 recall eval cases (56 → 62 total) |
| `BOUNTY.md` | **New** — This document |
