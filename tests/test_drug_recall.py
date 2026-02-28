"""Isolated unit tests for AgentForge FDA drug recall tools.

Tests watchlist CRUD and recall checking with mocked FDA API — no API keys needed.
Uses a temporary SQLite database for each test.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
import pytest

from app.database import get_db, init_db

# Temporary DB for tests
_test_db_path = Path(tempfile.mkdtemp()) / "test_agentforge.db"


@pytest.fixture(autouse=True)
def _setup_test_db():
    """Create a fresh test database for each test."""
    init_db(_test_db_path)
    with patch("app.tools.drug_recall.get_db", lambda: get_db(_test_db_path)):
        yield
    # Cleanup
    if _test_db_path.exists():
        os.unlink(_test_db_path)


# ===================================================================
# Watchlist CRUD Tests
# ===================================================================


class TestManageWatchlist:
    def test_add_to_watchlist(self):
        from app.tools.drug_recall import _watchlist_add
        result = _watchlist_add("P001", "metformin", "diabetes management")
        assert "Added" in result
        assert "metformin" in result

        # Verify in DB
        conn = get_db(_test_db_path)
        rows = conn.execute("SELECT * FROM patient_watchlist WHERE patient_id = 'P001'").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["medication_name"] == "metformin"
        assert rows[0]["notes"] == "diabetes management"
        assert rows[0]["status"] == "active"

    def test_add_duplicate(self):
        from app.tools.drug_recall import _watchlist_add
        _watchlist_add("P001", "metformin", "")
        result = _watchlist_add("P001", "metformin", "")
        assert "already on the watchlist" in result

    def test_list_watchlist(self):
        from app.tools.drug_recall import _watchlist_add, _watchlist_list
        _watchlist_add("P001", "metformin", "for diabetes")
        _watchlist_add("P001", "lisinopril", "blood pressure")
        result = _watchlist_list("P001")
        assert "2 medications" in result
        assert "metformin" in result
        assert "lisinopril" in result

    def test_list_empty_watchlist(self):
        from app.tools.drug_recall import _watchlist_list
        result = _watchlist_list("P999")
        assert "No medications on watchlist" in result

    def test_remove_from_watchlist(self):
        from app.tools.drug_recall import _watchlist_add, _watchlist_remove, _watchlist_list
        _watchlist_add("P001", "aspirin", "")
        result = _watchlist_remove("P001", "aspirin")
        assert "Removed" in result

        # Verify it no longer appears in list
        list_result = _watchlist_list("P001")
        assert "No medications on watchlist" in list_result

    def test_remove_nonexistent(self):
        from app.tools.drug_recall import _watchlist_remove
        result = _watchlist_remove("P001", "nonexistent_drug")
        assert "not found" in result

    def test_update_watchlist_notes(self):
        from app.tools.drug_recall import _watchlist_add, _watchlist_update
        _watchlist_add("P001", "warfarin", "initial")
        result = _watchlist_update("P001", "warfarin", "adjusted dosage per Dr. Smith")
        assert "Updated" in result

        # Verify in DB
        conn = get_db(_test_db_path)
        row = conn.execute(
            "SELECT notes FROM patient_watchlist WHERE patient_id = 'P001' AND medication_name = 'warfarin'"
        ).fetchone()
        conn.close()
        assert row["notes"] == "adjusted dosage per Dr. Smith"


# ===================================================================
# FDA Recall Checker Tests
# ===================================================================


MOCK_FDA_RESPONSE = {
    "results": [
        {
            "recall_number": "D-0001-2026",
            "reason_for_recall": "Contamination with NDMA above acceptable levels",
            "classification": "Class I",
            "status": "Ongoing",
            "voluntary_mandated": "Voluntary",
            "distribution_pattern": "Nationwide",
        },
        {
            "recall_number": "D-0002-2026",
            "reason_for_recall": "Mislabeled dosage strength",
            "classification": "Class II",
            "status": "Ongoing",
            "voluntary_mandated": "Voluntary",
            "distribution_pattern": "CA, NY, TX",
        },
    ]
}


class TestCheckDrugRecalls:
    @patch("app.tools.drug_recall.httpx.Client")
    def test_check_recalls_with_results(self, mock_client_cls):
        from app.tools.drug_recall import _fetch_fda_recalls

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_FDA_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        recalls = _fetch_fda_recalls("metformin")
        assert len(recalls) == 2
        assert recalls[0]["recall_number"] == "D-0001-2026"
        assert recalls[0]["classification"] == "Class I"
        assert "death" in recalls[0]["severity"].lower()
        assert recalls[1]["classification"] == "Class II"

    @patch("app.tools.drug_recall.httpx.Client")
    def test_check_recalls_no_results(self, mock_client_cls):
        from app.tools.drug_recall import _fetch_fda_recalls

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        recalls = _fetch_fda_recalls("safe_drug_xyz")
        assert recalls == []

    @patch("app.tools.drug_recall.httpx.Client")
    def test_check_recalls_api_failure(self, mock_client_cls):
        from app.tools.drug_recall import _fetch_fda_recalls

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # max_retries=1 to avoid slow backoff in tests
        recalls = _fetch_fda_recalls("metformin", max_retries=1)
        assert recalls == []

    @patch("app.tools.drug_recall.httpx.Client")
    def test_check_recalls_timeout(self, mock_client_cls):
        """Timeout triggers graceful empty return."""
        from app.tools.drug_recall import _fetch_fda_recalls

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Read timed out")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        recalls = _fetch_fda_recalls("metformin", max_retries=1)
        assert recalls == []

    @patch("app.tools.drug_recall.httpx.Client")
    def test_check_recalls_retry_success(self, mock_client_cls):
        """First call fails, second succeeds — tests exponential backoff."""
        from app.tools.drug_recall import _fetch_fda_recalls

        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = MOCK_FDA_RESPONSE
        mock_resp_ok.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.side_effect = [
            httpx.ConnectError("Connection refused"),
            mock_resp_ok,
        ]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("app.tools.drug_recall.time.sleep"):  # Skip actual sleep
            recalls = _fetch_fda_recalls("metformin", max_retries=2)
        assert len(recalls) == 2
        assert recalls[0]["recall_number"] == "D-0001-2026"


# ===================================================================
# Watchlist Recall Scanner Tests
# ===================================================================


class TestScanWatchlistRecalls:
    @patch("app.tools.drug_recall.time.sleep")  # Skip throttle delay
    @patch("app.tools.drug_recall._fetch_fda_recalls")
    def test_scan_watchlist_recalls(self, mock_fetch, _mock_sleep):
        from app.tools.drug_recall import _watchlist_add, scan_watchlist_recalls

        _watchlist_add("P001", "metformin", "")
        _watchlist_add("P001", "lisinopril", "")

        # One drug has recalls, one doesn't. Return recalls for every call to
        # exercise both branches: the order depends on DB row ordering.
        def fake_fetch(drug_name, max_retries=3):
            if "metformin" in drug_name.lower():
                return [{"classification": "Class I", "severity": "Most Serious", "reason": "Contamination"}]
            return []

        mock_fetch.side_effect = fake_fetch

        result = scan_watchlist_recalls.invoke({"patient_id": "P001"})
        assert "METFORMIN" in result
        assert "recall" in result.lower()
        assert "lisinopril" in result.lower()
        assert "No active recalls" in result

    def test_scan_empty_watchlist(self):
        from app.tools.drug_recall import scan_watchlist_recalls
        result = scan_watchlist_recalls.invoke({"patient_id": "P999"})
        assert "No medications on watchlist" in result

    @patch("app.tools.drug_recall.time.sleep")  # Skip throttle delay
    @patch("app.tools.drug_recall._fetch_fda_recalls")
    def test_scan_partial_api_failure(self, mock_fetch, _mock_sleep):
        """One drug succeeds, one fails — partial results still returned."""
        from app.tools.drug_recall import _watchlist_add, scan_watchlist_recalls

        _watchlist_add("P001", "metformin", "")
        _watchlist_add("P001", "lisinopril", "")

        def fake_fetch(drug_name, max_retries=3):
            if "metformin" in drug_name.lower():
                return [{"classification": "Class II", "severity": "Moderate", "reason": "Label error"}]
            return []  # Simulates API failure returning empty

        mock_fetch.side_effect = fake_fetch

        result = scan_watchlist_recalls.invoke({"patient_id": "P001"})
        assert "METFORMIN" in result
        assert "1 recall" in result.lower() or "recall" in result.lower()
        assert "lisinopril" in result.lower()

    @patch("app.tools.drug_recall.time.sleep")  # Skip throttle delay
    @patch("app.tools.drug_recall._fetch_fda_recalls")
    def test_last_scanned_updated_after_scan(self, mock_fetch, _mock_sleep):
        """Verify last_scanned timestamp is set after scan_watchlist_recalls runs."""
        from app.tools.drug_recall import _watchlist_add, scan_watchlist_recalls

        _watchlist_add("P001", "aspirin", "")
        mock_fetch.return_value = []

        scan_watchlist_recalls.invoke({"patient_id": "P001"})

        # Check the DB for last_scanned
        conn = get_db(_test_db_path)
        row = conn.execute(
            "SELECT last_scanned FROM patient_watchlist WHERE patient_id = 'P001' AND medication_name = 'aspirin'"
        ).fetchone()
        conn.close()
        assert row["last_scanned"] is not None
        assert "2026" in row["last_scanned"]  # Should be current year

    def test_add_medication_case_insensitive(self):
        """'Metformin' and 'metformin' should be treated as the same entry."""
        from app.tools.drug_recall import _watchlist_add

        result1 = _watchlist_add("P001", "Metformin", "")
        assert "Added" in result1

        result2 = _watchlist_add("P001", "metformin", "")
        assert "already on the watchlist" in result2
