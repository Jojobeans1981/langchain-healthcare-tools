"""OpenEMR medication sync for the patient watchlist.

Bridges the OpenEMR REST API medication data with the local SQLite watchlist.
When OpenEMR is available, syncs patient medications into the watchlist
so they can be scanned against the FDA recall database.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Standardized return type for sync operations (Phase 5C)."""
    synced: int = 0
    skipped: int = 0
    total: int = 0
    medications: list[str] = field(default_factory=list)
    source: str = "unavailable"
    reason: str = ""

    def to_dict(self) -> dict:
        d = {"synced": self.synced, "skipped": self.skipped, "total": self.total,
             "medications": self.medications, "source": self.source}
        if self.reason:
            d["reason"] = self.reason
        return d


def _get_openemr_client():
    """Lazy import to avoid circular dependencies and allow mocking."""
    from app.openemr_client import openemr
    return openemr


def is_openemr_available() -> bool:
    """Check if OpenEMR integration is enabled and reachable."""
    if not settings.openemr_enabled:
        return False
    try:
        return _get_openemr_client().is_available()
    except Exception:
        return False


def fetch_openemr_medications(patient_id: str) -> list[dict] | None:
    """Fetch medications from OpenEMR for a patient.

    Args:
        patient_id: The patient identifier. Must be numeric for OpenEMR.

    Returns:
        List of medication dicts with 'title' (medication name), 'begdate',
        'enddate', etc. Returns None if OpenEMR is unavailable or patient
        not found. Returns empty list if patient exists but has no medications.
    """
    if not is_openemr_available():
        return None
    if not patient_id.isdigit():
        logger.info("Patient ID '%s' is not numeric — skipping OpenEMR lookup", patient_id)
        return None
    try:
        client = _get_openemr_client()
        result = client.get_patient_medications(int(patient_id))
        if result is None:
            return None
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.warning("OpenEMR medication fetch failed for patient %s: %s", patient_id, e)
        return None


def sync_medications_from_openemr(patient_id: str) -> dict:
    """Sync medications from OpenEMR into the local watchlist.

    Performs an upsert: inserts new medications from OpenEMR without
    duplicating existing entries (manual or previously synced).

    Args:
        patient_id: The patient identifier.

    Returns:
        Dict with keys: 'synced' (int), 'skipped' (int), 'total' (int),
        'medications' (list[str]), 'source' (str), optionally 'reason' (str).
    """
    # Handle non-numeric patient IDs explicitly (Phase 2D)
    if not patient_id.strip().isdigit() and is_openemr_available():
        return {
            "synced": 0, "skipped": 0, "total": 0, "medications": [],
            "source": "local_only",
            "reason": "Non-numeric patient ID — OpenEMR uses numeric IDs. Using local watchlist only.",
        }

    meds = fetch_openemr_medications(patient_id)
    if meds is None:
        return {"synced": 0, "skipped": 0, "total": 0, "medications": [], "source": "unavailable"}

    medication_names = []
    for med in meds:
        title = med.get("title", "").strip()
        # Skip inactive medications (enddate is set and in the past) — Phase 5E
        enddate = med.get("enddate", "")
        if enddate and enddate.strip():
            try:
                end = datetime.fromisoformat(enddate.replace("Z", "+00:00"))
                if end < datetime.now(timezone.utc):
                    logger.info("Skipping inactive medication '%s' (ended %s)", title, enddate)
                    continue
            except (ValueError, TypeError):
                pass  # If enddate is unparseable, include the medication
        if title:
            medication_names.append(title)

    if not medication_names:
        return {"synced": 0, "skipped": 0, "total": 0, "medications": [], "source": "openemr"}

    conn = get_db()
    synced = 0
    skipped = 0
    try:
        for name in medication_names:
            try:
                conn.execute(
                    "INSERT INTO patient_watchlist (patient_id, medication_name, added_date, notes, source) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (patient_id, name.lower(), datetime.now(timezone.utc).isoformat(),
                     "Auto-synced from OpenEMR", "openemr"),
                )
                synced += 1
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    skipped += 1
                else:
                    logger.warning("Error syncing medication '%s': %s", name, e)
                    skipped += 1
        conn.commit()
    finally:
        conn.close()

    return {
        "synced": synced,
        "skipped": skipped,
        "total": len(medication_names),
        "medications": medication_names,
        "source": "openemr",
    }
