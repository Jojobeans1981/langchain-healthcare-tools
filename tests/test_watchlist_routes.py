"""Tests for the watchlist REST API endpoints."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.database import get_db, init_db


_test_db_path = Path(tempfile.mkdtemp()) / "test_routes_wl.db"


@pytest.fixture(autouse=True)
def _setup_test_db():
    """Fresh test database for each test."""
    init_db(_test_db_path)
    with patch("app.tools.drug_recall.get_db", lambda: get_db(_test_db_path)), \
         patch("app.tools.watchlist_sync.get_db", lambda: get_db(_test_db_path)), \
         patch("app.tools.watchlist_sync.is_openemr_available", return_value=False):
        yield
    if _test_db_path.exists():
        os.unlink(_test_db_path)


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestWatchlistEndpoints:

    def test_add_and_list(self, client):
        """Add a medication then list it."""
        resp = client.post("/api/watchlist/P001", json={"medication_name": "metformin"})
        assert resp.status_code == 200
        assert resp.json()["success"]

        resp = client.get("/api/watchlist/P001")
        assert resp.status_code == 200
        assert "metformin" in resp.json()["result"]

    def test_add_duplicate_returns_409(self, client):
        """Adding the same medication twice returns 409 Conflict."""
        client.post("/api/watchlist/P001", json={"medication_name": "aspirin"})
        resp = client.post("/api/watchlist/P001", json={"medication_name": "aspirin"})
        assert resp.status_code == 409

    def test_delete_existing(self, client):
        """Removing an existing medication succeeds."""
        client.post("/api/watchlist/P001", json={"medication_name": "warfarin"})
        resp = client.delete("/api/watchlist/P001/warfarin")
        assert resp.status_code == 200

    def test_delete_nonexistent_returns_404(self, client):
        """Removing a non-existent medication returns 404."""
        resp = client.delete("/api/watchlist/P001/nonexistent")
        assert resp.status_code == 404

    def test_sync_without_openemr_returns_503(self, client):
        """Sync endpoint returns 503 when OpenEMR is unavailable."""
        with patch("app.api.watchlist_routes.is_openemr_available", return_value=False):
            resp = client.post("/api/watchlist/P001/sync")
            assert resp.status_code == 503

    @patch("app.tools.drug_recall._fetch_fda_recalls", return_value=[])
    @patch("app.tools.drug_recall.time.sleep")
    def test_scan_endpoint(self, _sleep, _fetch, client):
        """Scan endpoint returns recall results for watchlist medications."""
        client.post("/api/watchlist/P001", json={"medication_name": "metformin"})
        resp = client.post("/api/watchlist/P001/scan")
        assert resp.status_code == 200
        assert "metformin" in resp.json()["result"].lower()
