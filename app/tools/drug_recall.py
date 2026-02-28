"""FDA Drug Recall Monitoring tools for AgentForge.

Provides patient medication watchlist management (SQLite CRUD)
and real-time FDA drug recall checking via the openFDA API.
"""

import logging
import time
from datetime import datetime, timezone

import httpx
from langchain_core.tools import tool

from app.database import get_db

logger = logging.getLogger(__name__)

FDA_RECALL_URL = "https://api.fda.gov/drug/enforcement.json"

CLASSIFICATION_MAP = {
    "Class I": "Most Serious — may cause death or serious health consequences",
    "Class II": "May cause temporary or medically reversible health problems",
    "Class III": "Not likely to cause adverse health consequences",
}


# ===================================================================
# Tool 1: Patient Medication Watchlist (CRUD)
# ===================================================================


@tool
def manage_watchlist(action: str, patient_id: str, medication_name: str = "", notes: str = "") -> str:
    """Manage a patient's medication watchlist. Use when users want to add, remove, list, or update medications being tracked for a patient.

    Args:
        action: One of 'add', 'list', 'remove', or 'update'.
        patient_id: The patient identifier (e.g., 'P001').
        medication_name: The medication name (required for add/remove/update).
        notes: Optional notes about the medication (used with add/update).
    """
    action = action.strip().lower()

    if action == "add":
        return _watchlist_add(patient_id, medication_name, notes)
    elif action == "list":
        return _watchlist_list(patient_id)
    elif action == "remove":
        return _watchlist_remove(patient_id, medication_name)
    elif action == "update":
        return _watchlist_update(patient_id, medication_name, notes)
    else:
        return f"Unknown action '{action}'. Valid actions: add, list, remove, update."


def _watchlist_add(patient_id: str, medication_name: str, notes: str) -> str:
    if not medication_name:
        return "Error: medication_name is required for 'add' action."
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO patient_watchlist (patient_id, medication_name, added_date, notes) VALUES (?, ?, ?, ?)",
            (patient_id, medication_name.strip().lower(), datetime.now(timezone.utc).isoformat(), notes),
        )
        conn.commit()
        return f"Added '{medication_name}' to watchlist for patient {patient_id}."
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return f"'{medication_name}' is already on the watchlist for patient {patient_id}."
        return f"Error adding to watchlist: {e}"
    finally:
        conn.close()


def _watchlist_list(patient_id: str) -> str:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT medication_name, added_date, notes, last_scanned FROM patient_watchlist WHERE patient_id = ? AND status = 'active' ORDER BY added_date",
            (patient_id,),
        ).fetchall()
        if not rows:
            return f"No medications on watchlist for patient {patient_id}."
        lines = [f"Medication watchlist for patient {patient_id} ({len(rows)} medications):"]
        for row in rows:
            entry = f"- {row['medication_name']}"
            if row["notes"]:
                entry += f" (notes: {row['notes']})"
            scanned = row["last_scanned"]
            if scanned:
                entry += f" [last scanned: {scanned}]"
            else:
                entry += " [never scanned]"
            lines.append(entry)
        return "\n".join(lines)
    finally:
        conn.close()


def _watchlist_remove(patient_id: str, medication_name: str) -> str:
    if not medication_name:
        return "Error: medication_name is required for 'remove' action."
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE patient_watchlist SET status = 'removed' WHERE patient_id = ? AND medication_name = ? AND status = 'active'",
            (patient_id, medication_name.strip().lower()),
        )
        conn.commit()
        if cursor.rowcount > 0:
            return f"Removed '{medication_name}' from watchlist for patient {patient_id}."
        return f"'{medication_name}' was not found on the active watchlist for patient {patient_id}."
    finally:
        conn.close()


def _watchlist_update(patient_id: str, medication_name: str, notes: str) -> str:
    if not medication_name:
        return "Error: medication_name is required for 'update' action."
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE patient_watchlist SET notes = ? WHERE patient_id = ? AND medication_name = ? AND status = 'active'",
            (notes, patient_id, medication_name.strip().lower()),
        )
        conn.commit()
        if cursor.rowcount > 0:
            return f"Updated notes for '{medication_name}' on patient {patient_id}'s watchlist."
        return f"'{medication_name}' was not found on the active watchlist for patient {patient_id}."
    finally:
        conn.close()


# ===================================================================
# Tool 2: FDA Drug Recall Checker
# ===================================================================


def _fetch_fda_recalls(drug_name: str, max_retries: int = 3) -> list[dict]:
    """Fetch recall data from the FDA openFDA API for a given drug name.

    Uses exponential backoff (0.5s, 1s, 2s) on transient failures.
    """
    search_term = drug_name.strip()
    # Build URL manually — httpx encodes + as %2B which breaks the FDA API's OR operator
    url = (
        f'{FDA_RECALL_URL}'
        f'?search=openfda.brand_name:"{search_term}"+OR+openfda.generic_name:"{search_term}"'
        f'&limit=5'
    )
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                recalls = []
                for r in results:
                    classification = r.get("classification", "Unknown")
                    recalls.append({
                        "recall_number": r.get("recall_number", "N/A"),
                        "reason": r.get("reason_for_recall", "No reason provided"),
                        "classification": classification,
                        "severity": CLASSIFICATION_MAP.get(classification, "Unknown severity"),
                        "status": r.get("status", "Unknown"),
                        "voluntary_mandated": r.get("voluntary_mandated", "Unknown"),
                        "distribution": r.get("distribution_pattern", "Unknown"),
                    })
                return recalls
        except httpx.HTTPStatusError as e:
            logger.warning("FDA API HTTP error for '%s': %s", drug_name, e)
            return []  # Non-transient — don't retry
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            if attempt < max_retries - 1:
                backoff = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                logger.info("FDA API retry %d/%d for '%s' (backoff %.1fs)", attempt + 1, max_retries, drug_name, backoff)
                time.sleep(backoff)
                continue
            logger.warning("FDA API failed after %d retries for '%s': %s", max_retries, drug_name, e)
            return []
        except Exception as e:
            logger.warning("FDA API unavailable for '%s': %s", drug_name, e)
            return []
    return []  # Should not reach here, but safety net


@tool
def check_drug_recalls(drug_name: str) -> str:
    """Query the FDA openFDA enforcement API for active recall actions on a medication. This tool makes a live API call to the FDA and returns real recall data including classification, reason, and status. You MUST use this tool for any question about drug recalls, FDA safety alerts, or medication enforcement actions.

    Args:
        drug_name: The medication name to check (e.g. 'metformin', 'warfarin', 'lisinopril').
    """
    recalls = _fetch_fda_recalls(drug_name)

    if not recalls:
        return f"No active recalls found for '{drug_name}' in the FDA enforcement database."

    lines = [f"FDA Recall Report for '{drug_name}' — {len(recalls)} recall(s) found:\n"]
    for i, r in enumerate(recalls, 1):
        lines.append(f"Recall #{i}:")
        lines.append(f"  Recall Number: {r['recall_number']}")
        lines.append(f"  Classification: {r['classification']} — {r['severity']}")
        lines.append(f"  Reason: {r['reason']}")
        lines.append(f"  Status: {r['status']}")
        lines.append(f"  Voluntary/Mandated: {r['voluntary_mandated']}")
        lines.append(f"  Distribution: {r['distribution']}")
        lines.append("")

    lines.append("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    lines.append("Source: FDA openFDA Drug Enforcement API (https://api.fda.gov)")
    return "\n".join(lines)


# ===================================================================
# Tool 3: Watchlist Recall Scanner
# ===================================================================


@tool
def scan_watchlist_recalls(patient_id: str) -> str:
    """Query the FDA openFDA enforcement API for recalls on ALL medications in a patient's watchlist. This tool reads the patient's medication watchlist from the database, then checks each medication against live FDA recall data. You MUST use this tool when asked to scan or check a patient's medications for recalls.

    Args:
        patient_id: The patient identifier (e.g., 'P001').
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT medication_name FROM patient_watchlist WHERE patient_id = ? AND status = 'active'",
            (patient_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return f"No medications on watchlist for patient {patient_id}. Add medications first using manage_watchlist."

    medications = [row["medication_name"] for row in rows]
    lines = [f"FDA Recall Scan for patient {patient_id} — checking {len(medications)} medication(s):\n"]

    recalls_found = 0
    scan_conn = get_db()
    try:
        for i, med in enumerate(medications):
            # Throttle between API calls to respect 240 req/min rate limit
            if i > 0:
                time.sleep(0.1)
            recalls = _fetch_fda_recalls(med)
            # Update last_scanned timestamp for audit trail
            scan_conn.execute(
                "UPDATE patient_watchlist SET last_scanned = ? WHERE patient_id = ? AND medication_name = ? AND status = 'active'",
                (datetime.now(timezone.utc).isoformat(), patient_id, med),
            )
            if recalls:
                recalls_found += len(recalls)
                lines.append(f"⚠ {med.upper()}: {len(recalls)} recall(s) found")
                for r in recalls:
                    lines.append(f"  - {r['classification']} ({r['severity']}): {r['reason'][:100]}")
            else:
                lines.append(f"✓ {med}: No active recalls")
            lines.append("")
        scan_conn.commit()
    finally:
        scan_conn.close()

    if recalls_found > 0:
        lines.append(f"SUMMARY: {recalls_found} total recall(s) found across {len(medications)} medications. Review with prescribing physician.")
    else:
        lines.append(f"SUMMARY: All {len(medications)} medications are clear — no active FDA recalls found.")

    lines.append("\n[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]")
    lines.append("Source: FDA openFDA Drug Enforcement API (https://api.fda.gov)")
    return "\n".join(lines)
