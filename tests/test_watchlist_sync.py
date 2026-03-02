"""Tests for OpenEMR medication sync integration.

Tests the watchlist_sync module and OpenEMR-enhanced drug_recall tools
with mocked OpenEMR client — no running OpenEMR instance needed.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.database import get_db, init_db


_test_db_path = Path(tempfile.mkdtemp()) / "test_sync.db"


@pytest.fixture(autouse=True)
def _setup_test_db():
    """Fresh test database for each test."""
    init_db(_test_db_path)
    with patch("app.tools.drug_recall.get_db", lambda: get_db(_test_db_path)), \
         patch("app.tools.watchlist_sync.get_db", lambda: get_db(_test_db_path)):
        yield
    if _test_db_path.exists():
        os.unlink(_test_db_path)


MOCK_OPENEMR_MEDICATIONS = [
    {"title": "Metformin", "begdate": "2025-01-15", "enddate": None, "id": 1},
    {"title": "Lisinopril", "begdate": "2025-03-01", "enddate": None, "id": 2},
    {"title": "Aspirin", "begdate": "2024-06-20", "enddate": None, "id": 3},
]


# ===================================================================
# Sync Layer Tests
# ===================================================================


class TestSyncMedicationsFromOpenemr:

    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_sync_adds_new_medications(self, mock_settings, mock_get_client):
        """Syncing from OpenEMR inserts medications into watchlist."""
        from app.tools.watchlist_sync import sync_medications_from_openemr

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.return_value = MOCK_OPENEMR_MEDICATIONS
        mock_get_client.return_value = mock_client

        result = sync_medications_from_openemr("1")
        assert result["synced"] == 3
        assert result["skipped"] == 0
        assert result["source"] == "openemr"

        # Verify in DB
        conn = get_db(_test_db_path)
        rows = conn.execute("SELECT * FROM patient_watchlist WHERE patient_id = '1'").fetchall()
        conn.close()
        assert len(rows) == 3
        assert all(r["source"] == "openemr" for r in rows)

    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_sync_skips_existing_medications(self, mock_settings, mock_get_client):
        """Re-syncing doesn't duplicate existing entries."""
        from app.tools.drug_recall import _watchlist_add
        from app.tools.watchlist_sync import sync_medications_from_openemr

        _watchlist_add("1", "metformin", "existing entry")

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.return_value = MOCK_OPENEMR_MEDICATIONS
        mock_get_client.return_value = mock_client

        result = sync_medications_from_openemr("1")
        assert result["synced"] == 2  # lisinopril + aspirin
        assert result["skipped"] == 1  # metformin already exists

    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_sync_returns_unavailable_when_openemr_down(self, mock_settings, mock_get_client):
        """When OpenEMR is unreachable, sync returns source='unavailable'."""
        from app.tools.watchlist_sync import sync_medications_from_openemr

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_get_client.return_value = mock_client

        result = sync_medications_from_openemr("1")
        assert result["source"] == "unavailable"
        assert result["synced"] == 0

    def test_sync_skips_non_numeric_patient_id(self):
        """Non-numeric patient IDs skip OpenEMR lookup."""
        from app.tools.watchlist_sync import fetch_openemr_medications
        result = fetch_openemr_medications("P001")
        assert result is None

    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_sync_handles_empty_medication_list(self, mock_settings, mock_get_client):
        """Patient exists in OpenEMR but has no medications."""
        from app.tools.watchlist_sync import sync_medications_from_openemr

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.return_value = []
        mock_get_client.return_value = mock_client

        result = sync_medications_from_openemr("1")
        assert result["synced"] == 0
        assert result["total"] == 0
        assert result["source"] == "openemr"

    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_sync_handles_openemr_api_error(self, mock_settings, mock_get_client):
        """OpenEMR API errors return None, treated as unavailable."""
        from app.tools.watchlist_sync import fetch_openemr_medications

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.side_effect = Exception("Connection refused")
        mock_get_client.return_value = mock_client

        result = fetch_openemr_medications("1")
        assert result is None


# ===================================================================
# OpenEMR-Enhanced Scan Tests
# ===================================================================


class TestOpenemrEnhancedScanRecalls:

    @patch("app.tools.drug_recall.time.sleep")
    @patch("app.tools.drug_recall._fetch_fda_recalls")
    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_scan_syncs_from_openemr_before_scanning(self, mock_settings, mock_get_client, mock_fetch, _mock_sleep):
        """scan_watchlist_recalls syncs from OpenEMR then scans all medications."""
        from app.tools.drug_recall import scan_watchlist_recalls

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.return_value = MOCK_OPENEMR_MEDICATIONS
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = []

        result = scan_watchlist_recalls.invoke({"patient_id": "1"})
        assert "3 medication(s)" in result
        assert "metformin" in result.lower()
        assert "lisinopril" in result.lower()
        assert "OpenEMR" in result

    @patch("app.tools.drug_recall.time.sleep")
    @patch("app.tools.drug_recall._fetch_fda_recalls")
    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_scan_combines_openemr_and_manual_meds(self, mock_settings, mock_get_client, mock_fetch, _mock_sleep):
        """Scan includes both OpenEMR-synced and manually-added medications."""
        from app.tools.drug_recall import _watchlist_add, scan_watchlist_recalls

        _watchlist_add("1", "warfarin", "manual add")

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.return_value = [
            {"title": "Metformin", "begdate": "2025-01-15"}
        ]
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = []

        result = scan_watchlist_recalls.invoke({"patient_id": "1"})
        assert "2 medication(s)" in result
        assert "warfarin" in result.lower()
        assert "metformin" in result.lower()


# ===================================================================
# OpenEMR-Enhanced List Tests
# ===================================================================


class TestOpenemrEnhancedListWatchlist:

    @patch("app.tools.watchlist_sync._get_openemr_client")
    @patch("app.tools.watchlist_sync.settings")
    def test_list_shows_source_tags(self, mock_settings, mock_get_client):
        """_watchlist_list shows [OpenEMR] tag for synced medications."""
        from app.tools.drug_recall import _watchlist_list
        from app.tools.watchlist_sync import sync_medications_from_openemr

        mock_settings.openemr_enabled = True
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.get_patient_medications.return_value = [
            {"title": "Metformin", "begdate": "2025-01-15"}
        ]
        mock_get_client.return_value = mock_client

        # Sync first, then list
        sync_medications_from_openemr("1")
        result = _watchlist_list("1")
        assert "[OpenEMR]" in result
        assert "metformin" in result.lower()
