"""Live integration tests for OpenEMR REST API connection.

These tests require a running OpenEMR instance (docker compose up).
They are skipped by default — run with:

    OPENEMR_ENABLED=true python -m pytest tests/test_openemr_live.py -v

Or set OPENEMR_ENABLED=true in your .env file.
"""

import os

import pytest

# Mark as integration tests — excluded from default test run.
# Run explicitly with: pytest -m integration tests/test_openemr_live.py
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("OPENEMR_ENABLED", "false").lower() != "true",
        reason="OPENEMR_ENABLED not set — skipping live OpenEMR tests",
    ),
]


@pytest.fixture(scope="module")
def emr_client():
    """Get the OpenEMR client singleton."""
    from app.openemr_client import OpenEMRClient
    client = OpenEMRClient()
    if not client.is_available():
        pytest.skip("OpenEMR is not reachable")
    return client


class TestOpenEMRConnection:
    def test_is_available(self, emr_client):
        """OpenEMR REST API responds to health probe."""
        assert emr_client.is_available() is True

    def test_oauth2_authentication(self, emr_client):
        """OAuth2 password grant returns a valid token."""
        assert emr_client._authenticate() is True
        assert emr_client._token is not None
        assert len(emr_client._token) > 10

    def test_get_practitioners(self, emr_client):
        """Fetch practitioners list from OpenEMR."""
        result = emr_client.get_practitioners()
        assert result is not None
        assert isinstance(result, list)
        # Default OpenEMR dev has at least the admin user
        assert len(result) >= 1, "Expected at least 1 practitioner in OpenEMR"

    def test_get_patients(self, emr_client):
        """Fetch patient list from OpenEMR."""
        result = emr_client.get_patients()
        assert result is not None
        assert isinstance(result, list)

    def test_get_appointments(self, emr_client):
        """Fetch appointments from OpenEMR (may be empty on fresh install)."""
        result = emr_client.get_appointments()
        assert result is not None
        assert isinstance(result, list)


class TestToolsWithLiveData:
    """Test that the LangChain tools work with live OpenEMR data."""

    def test_provider_search_live(self):
        """provider_search returns results from OpenEMR."""
        import asyncio
        from app.tools.provider_search import provider_search
        result = asyncio.get_event_loop().run_until_complete(
            provider_search.ainvoke({"specialty": "medicine"})
        )
        assert "PROVIDER RESULTS" in result or "No providers found" in result

    def test_appointment_availability_live(self):
        """appointment_availability queries the scheduling system."""
        import asyncio
        from app.tools.appointment_availability import appointment_availability
        result = asyncio.get_event_loop().run_until_complete(
            appointment_availability.ainvoke({"specialty": "medicine"})
        )
        assert "APPOINTMENT" in result or "No available appointments" in result


class TestWatchlistSyncLive:
    """Test the medication watchlist sync against a real OpenEMR instance."""

    def test_get_patient_medications(self, emr_client):
        """get_patient_medications returns a list (possibly empty) for a valid patient."""
        result = emr_client.get_patient_medications(1)
        # On a fresh OpenEMR install, patient 1 may have no medications.
        # The key assertion: the API responds with data, not None.
        assert result is not None
        assert isinstance(result, list)

    def test_watchlist_sync_from_openemr(self, tmp_path):
        """sync_medications_from_openemr calls real OpenEMR and returns a valid result."""
        from unittest.mock import patch
        from app.database import get_db, init_db
        from app.tools.watchlist_sync import sync_medications_from_openemr

        # Use an isolated database so we don't pollute anything
        db_path = tmp_path / "live_sync_test.db"
        init_db(db_path)

        with patch("app.tools.watchlist_sync.get_db", lambda: get_db(db_path)):
            result = sync_medications_from_openemr("1")

        assert isinstance(result, dict)
        assert "source" in result
        # Should be 'openemr' (successful sync) or 'unavailable' (if patient has no meds)
        assert result["source"] in ("openemr", "unavailable")
        assert isinstance(result.get("medications", []), list)

    def test_scan_with_openemr_sync(self, tmp_path):
        """Full pipeline: sync from OpenEMR → scan for FDA recalls."""
        from unittest.mock import patch
        from app.database import get_db, init_db
        from app.tools.drug_recall import scan_watchlist_recalls, manage_watchlist

        db_path = tmp_path / "live_scan_test.db"
        init_db(db_path)

        with patch("app.tools.drug_recall.get_db", lambda: get_db(db_path)), \
             patch("app.tools.watchlist_sync.get_db", lambda: get_db(db_path)):
            # Add a manual medication so scan always has at least one to check
            manage_watchlist.invoke({
                "action": "add", "patient_id": "1",
                "medication_name": "aspirin", "notes": "live test"
            })

            # Scan — this will auto-sync from OpenEMR, then check FDA
            result = scan_watchlist_recalls.invoke({"patient_id": "1"})

        assert "aspirin" in result.lower()
        # If OpenEMR has medications for patient 1, we'll see [OpenEMR] tags
        # If not, we'll still see the manually-added aspirin
        assert "FDA" in result.upper() or "recall" in result.lower()
