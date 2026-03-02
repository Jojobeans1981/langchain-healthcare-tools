"""End-to-end pipeline integration tests for AgentForge.

These tests exercise the FULL pipeline: tool execution → verification → post-processing,
with REAL FDA API calls (no mocks) and real SQLite database operations.

Tests are marked with @pytest.mark.e2e and require internet access.
They test the actual system behavior a pharmacist would experience.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.database import get_db, init_db
from app.tools.drug_recall import (
    check_drug_recalls,
    manage_watchlist,
    scan_watchlist_recalls,
)
from app.verification.verifier import verify_response, post_process_response


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Give every test a fresh SQLite database."""
    db_path = tmp_path / "test_e2e.db"
    init_db(db_path)

    with patch("app.tools.drug_recall.get_db", lambda: get_db(db_path)), \
         patch("app.tools.watchlist_sync.get_db", lambda: get_db(db_path)), \
         patch("app.tools.watchlist_sync.is_openemr_available", return_value=False):
        yield db_path


# ===================================================================
# E2E: Tool → Verification → Post-processing
# ===================================================================


class TestToolVerificationPipeline:
    """Tests that tool output passes through verification correctly."""

    def test_recall_check_passes_verification(self):
        """check_drug_recalls output should pass source grounding."""
        # Call the real tool (hits actual FDA API)
        result = check_drug_recalls.invoke({"drug_name": "metformin"})

        # Verify the output passes verification
        verification = verify_response(result, ["check_drug_recalls"], "Check metformin recalls")
        assert verification.source_grounding_pass or not verification.flags
        # Should contain FDA-related markers
        result_lower = result.lower()
        assert any(word in result_lower for word in ["recall", "fda", "no active"])

    def test_watchlist_crud_passes_verification(self):
        """Watchlist add → list → remove round-trip with verification."""
        # Add
        add_result = manage_watchlist.invoke({
            "action": "add", "patient_id": "E2E-001",
            "medication_name": "metformin", "notes": "e2e test"
        })
        assert "added" in add_result.lower()

        # List
        list_result = manage_watchlist.invoke({
            "action": "list", "patient_id": "E2E-001"
        })
        assert "metformin" in list_result.lower()

        # Verify list output passes grounding
        verification = verify_response(list_result, ["manage_watchlist"], "List patient E2E-001 medications")
        assert verification.source_grounding_pass

        # Remove
        remove_result = manage_watchlist.invoke({
            "action": "remove", "patient_id": "E2E-001",
            "medication_name": "metformin"
        })
        assert "removed" in remove_result.lower()

    def test_scan_with_real_fda_api(self):
        """Add medications, scan against REAL FDA API, verify output."""
        # Add medications to watchlist
        manage_watchlist.invoke({
            "action": "add", "patient_id": "E2E-002",
            "medication_name": "aspirin", "notes": ""
        })
        manage_watchlist.invoke({
            "action": "add", "patient_id": "E2E-002",
            "medication_name": "metformin", "notes": ""
        })

        # Scan against real FDA API
        scan_result = scan_watchlist_recalls.invoke({"patient_id": "E2E-002"})

        # Output should contain structured recall report
        assert "E2E-002" in scan_result or "e2e-002" in scan_result.lower()
        assert "aspirin" in scan_result.lower()
        assert "metformin" in scan_result.lower()

        # Verify scan output passes verification
        verification = verify_response(scan_result, ["scan_watchlist_recalls"], "Scan E2E-002 medications")
        assert verification.source_grounding_pass
        # Confidence should be reasonable (>= 0.3 base)
        assert verification.confidence >= 0.3

    def test_verification_blocks_unsafe_responses(self):
        """Verify that unsafe responses are blocked by post-processing."""
        unsafe_response = "You definitely have diabetes. Take 500mg of metformin twice daily."
        verification = verify_response(unsafe_response, ["symptom_lookup"], "I have high blood sugar")

        # Should have domain violations
        assert len(verification.domain_violations) > 0

        # Post-processing should replace the response
        processed = post_process_response(unsafe_response, verification)
        assert "I cannot provide" in processed
        assert "500mg" not in processed

    def test_emergency_escalation_always_prepended(self):
        """Emergency queries should always get 911 notice prepended."""
        safe_response = "Chest pain can have many causes. Source: AgentForge Healthcare Database."
        verification = verify_response(safe_response, ["symptom_lookup"], "I'm having chest pain")

        assert verification.needs_escalation

        processed = post_process_response(safe_response, verification)
        # 911 notice should be at the TOP
        assert processed.startswith("**IMPORTANT:")
        assert "911" in processed

    def test_hallucinated_response_gets_low_confidence(self):
        """Response with unsupported claims should get low confidence."""
        hallucinated = "Studies show that this drug is 100% safe and guaranteed to cure your condition."
        verification = verify_response(hallucinated, [], "Is this drug safe?")

        assert verification.hallucination_risk > 0.3
        assert verification.confidence < 0.5

    def test_full_pipeline_safe_interaction_query(self):
        """Full pipeline: safe drug interaction info → high confidence."""
        good_response = (
            "Based on the drug interaction check, warfarin and aspirin have a "
            "HIGH severity interaction. The risk of bleeding is significantly increased "
            "when these medications are combined. This is a contraindicated combination.\n\n"
            "Source: FDA Drug Safety Database, RxNorm\n\n"
            "**Disclaimer:** This information is for educational purposes only and does not "
            "constitute medical advice. Always consult a qualified healthcare professional."
        )
        verification = verify_response(
            good_response,
            ["drug_interaction_check"],
            "Check warfarin and aspirin interaction"
        )

        # Should pass all checks
        assert verification.source_grounding_pass
        assert verification.has_sources
        assert verification.has_disclaimer
        assert verification.confidence >= 0.5
        assert len(verification.domain_violations) == 0
        # Should trigger escalation (high severity)
        assert verification.needs_escalation


# ===================================================================
# E2E: Database state consistency
# ===================================================================


class TestDatabaseConsistency:
    """Tests that verify database state matches tool outputs."""

    def test_add_then_verify_database_row(self, _isolated_db):
        """Adding a medication via tool should create exact database row."""
        manage_watchlist.invoke({
            "action": "add", "patient_id": "DB-001",
            "medication_name": "Lisinopril", "notes": "blood pressure"
        })

        conn = get_db(_isolated_db)
        row = conn.execute(
            "SELECT patient_id, medication_name, notes, status, source "
            "FROM patient_watchlist WHERE patient_id='DB-001'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["patient_id"] == "DB-001"
        assert row["medication_name"] == "lisinopril"  # lowercased
        assert row["notes"] == "blood pressure"
        assert row["status"] == "active"
        assert row["source"] == "manual"

    def test_remove_is_soft_delete_in_database(self, _isolated_db):
        """Remove should set status='removed', not delete the row."""
        manage_watchlist.invoke({
            "action": "add", "patient_id": "DB-002",
            "medication_name": "warfarin", "notes": ""
        })
        manage_watchlist.invoke({
            "action": "remove", "patient_id": "DB-002",
            "medication_name": "warfarin"
        })

        conn = get_db(_isolated_db)
        row = conn.execute(
            "SELECT status FROM patient_watchlist WHERE patient_id='DB-002' AND medication_name='warfarin'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["status"] == "removed"

    def test_scan_updates_last_scanned_timestamp(self, _isolated_db):
        """Scanning should update last_scanned for each medication."""
        manage_watchlist.invoke({
            "action": "add", "patient_id": "DB-003",
            "medication_name": "aspirin", "notes": ""
        })

        # Verify last_scanned is null before scan
        conn = get_db(_isolated_db)
        row = conn.execute(
            "SELECT last_scanned FROM patient_watchlist WHERE patient_id='DB-003'"
        ).fetchone()
        conn.close()
        assert row["last_scanned"] is None

        # Scan (hits real FDA API)
        scan_watchlist_recalls.invoke({"patient_id": "DB-003"})

        # Verify last_scanned is now set
        conn = get_db(_isolated_db)
        row = conn.execute(
            "SELECT last_scanned FROM patient_watchlist WHERE patient_id='DB-003'"
        ).fetchone()
        conn.close()
        assert row["last_scanned"] is not None
