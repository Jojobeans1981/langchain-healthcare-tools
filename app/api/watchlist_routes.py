"""REST API endpoints for the patient medication watchlist.

Provides direct CRUD access to the watchlist and OpenEMR medication sync,
bypassing the chat agent for programmatic integrations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.tools.drug_recall import (
    _watchlist_add, _watchlist_list, _watchlist_remove,
    _fetch_fda_recalls, scan_watchlist_recalls,
)
from app.tools.watchlist_sync import (
    sync_medications_from_openemr, is_openemr_available,
)

watchlist_router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AddMedicationRequest(BaseModel):
    medication_name: str = Field(..., min_length=1, max_length=255)
    notes: str = Field(default="", max_length=1000)


class SyncResponse(BaseModel):
    synced: int
    skipped: int
    total: int
    medications: list[str]
    source: str


@watchlist_router.get("/{patient_id}")
async def list_watchlist(patient_id: str):
    """List medications on a patient's watchlist."""
    result = _watchlist_list(patient_id)
    return {"patient_id": patient_id, "result": result}


@watchlist_router.post("/{patient_id}")
async def add_to_watchlist(patient_id: str, req: AddMedicationRequest):
    """Add a medication to a patient's watchlist."""
    result = _watchlist_add(patient_id, req.medication_name, req.notes)
    success = "Added" in result
    if not success and "already on the watchlist" in result:
        raise HTTPException(status_code=409, detail=result)
    return {"patient_id": patient_id, "result": result, "success": success}


@watchlist_router.delete("/{patient_id}/{medication}")
async def remove_from_watchlist(patient_id: str, medication: str):
    """Remove a medication from a patient's watchlist."""
    result = _watchlist_remove(patient_id, medication)
    found = "Removed" in result
    if not found:
        raise HTTPException(status_code=404, detail=result)
    return {"patient_id": patient_id, "result": result}


@watchlist_router.post("/{patient_id}/sync", response_model=SyncResponse)
async def sync_from_openemr(patient_id: str):
    """Sync patient medications from OpenEMR into the watchlist."""
    if not is_openemr_available():
        raise HTTPException(status_code=503, detail="OpenEMR is not available or not enabled.")
    result = sync_medications_from_openemr(patient_id)
    return SyncResponse(**result)


@watchlist_router.post("/{patient_id}/scan")
async def scan_for_recalls(patient_id: str):
    """Scan all watchlist medications against the FDA recall database."""
    result = scan_watchlist_recalls.invoke({"patient_id": patient_id})
    return {"patient_id": patient_id, "result": result}
