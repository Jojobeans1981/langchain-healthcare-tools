"""Isolated unit tests for AgentForge healthcare tools.

These tests use mock data and do NOT require API keys or network access.
"""

import pytest

from app.tools.insurance_coverage import (
    MOCK_PLANS,
    PROCEDURE_CODES,
    _find_matching_plans,
    _resolve_procedure_code,
)
from app.tools.symptom_lookup import EMERGENCY_KEYWORDS, _get_default_symptom_db
from app.tools.drug_interaction import (
    KNOWN_INTERACTIONS,
    _check_local_interactions,
    _normalize_drug_name,
)
from app.tools.medication_lookup import MOCK_MEDICATIONS, _check_mock_data


# ===================================================================
# Insurance Coverage Tool Tests
# ===================================================================


class TestResolveProcedureCode:
    def test_cpt_code_passthrough(self):
        assert _resolve_procedure_code("99213") == "99213"
        assert _resolve_procedure_code("71046") == "71046"

    def test_description_lookup(self):
        assert _resolve_procedure_code("office visit") == "99213"
        assert _resolve_procedure_code("chest x-ray") == "71046"
        assert _resolve_procedure_code("knee replacement") == "27447"

    def test_case_insensitive(self):
        assert _resolve_procedure_code("OFFICE VISIT") == "99213"
        assert _resolve_procedure_code("MRI") == "70553"

    def test_unknown_procedure(self):
        assert _resolve_procedure_code("nonexistent procedure") is None
        assert _resolve_procedure_code("brain transplant") is None

    def test_whitespace_handling(self):
        assert _resolve_procedure_code("  office visit  ") == "99213"

    def test_partial_match(self):
        assert _resolve_procedure_code("I need a chest x-ray") == "71046"


class TestFindMatchingPlans:
    def test_empty_returns_all(self):
        plans = _find_matching_plans("")
        assert len(plans) == len(MOCK_PLANS)

    def test_find_blue_cross(self):
        plans = _find_matching_plans("Blue Cross")
        assert len(plans) == 1
        assert plans[0]["plan_name"] == "Blue Cross Blue Shield PPO"

    def test_find_medicare(self):
        plans = _find_matching_plans("Medicare")
        assert len(plans) == 1
        assert plans[0]["type"] == "Government"

    def test_find_aetna(self):
        plans = _find_matching_plans("Aetna")
        assert len(plans) == 1
        assert plans[0]["type"] == "HMO"

    def test_no_match(self):
        plans = _find_matching_plans("NonexistentInsurance")
        assert len(plans) == 0

    def test_case_insensitive(self):
        plans = _find_matching_plans("blue cross")
        assert len(plans) == 1


class TestInsuranceMockData:
    def test_all_plans_have_required_fields(self):
        for key, plan in MOCK_PLANS.items():
            assert "plan_name" in plan
            assert "plan_id" in plan
            assert "type" in plan
            assert "coverages" in plan
            assert "deductible" in plan
            assert "out_of_pocket_max" in plan

    def test_all_coverages_have_required_fields(self):
        for key, plan in MOCK_PLANS.items():
            for code, coverage in plan["coverages"].items():
                assert "description" in coverage
                assert "covered" in coverage
                assert "copay" in coverage
                assert "coinsurance" in coverage
                assert "deductible_applies" in coverage
                assert "prior_auth" in coverage

    def test_procedure_codes_are_valid(self):
        for desc, code in PROCEDURE_CODES.items():
            assert len(code) == 5
            assert code.isdigit()


# ===================================================================
# Symptom Lookup Tool Tests
# ===================================================================


class TestSymptomDatabase:
    def test_default_db_has_entries(self):
        db = _get_default_symptom_db()
        assert len(db) >= 5
        assert "headache" in db
        assert "fever" in db
        assert "cough" in db

    def test_conditions_have_required_fields(self):
        db = _get_default_symptom_db()
        for symptom, data in db.items():
            assert "conditions" in data
            assert "seek_emergency_if" in data
            for condition in data["conditions"]:
                assert "name" in condition
                assert "likelihood" in condition
                assert "description" in condition
                assert "recommended_actions" in condition

    def test_emergency_keywords_exist(self):
        assert len(EMERGENCY_KEYWORDS) >= 10
        assert "chest pain" in EMERGENCY_KEYWORDS
        assert "difficulty breathing" in EMERGENCY_KEYWORDS
        assert "seizure" in EMERGENCY_KEYWORDS


# ===================================================================
# Drug Interaction Tool Tests
# ===================================================================


class TestDrugInteraction:
    def test_normalize_drug_name(self):
        assert _normalize_drug_name("  Warfarin  ") == "warfarin"
        assert _normalize_drug_name("ASPIRIN") == "aspirin"

    def test_known_interaction_found(self):
        interactions = _check_local_interactions(["warfarin", "aspirin"])
        assert len(interactions) == 1
        assert interactions[0]["severity"] == "High"
        assert "drugs" in interactions[0]

    def test_no_interaction(self):
        interactions = _check_local_interactions(["aspirin", "metformin"])
        assert len(interactions) == 0

    def test_multiple_interactions(self):
        interactions = _check_local_interactions(["warfarin", "aspirin", "ibuprofen"])
        assert len(interactions) >= 2

    def test_case_insensitive(self):
        interactions = _check_local_interactions(["WARFARIN", "Aspirin"])
        assert len(interactions) == 1

    def test_known_interactions_have_required_fields(self):
        for pair, data in KNOWN_INTERACTIONS.items():
            assert "severity" in data
            assert "description" in data
            assert "source" in data
            assert "clinical_action" in data

    def test_severity_levels_are_valid(self):
        valid_severities = {"Low", "Moderate", "High", "Contraindicated"}
        for pair, data in KNOWN_INTERACTIONS.items():
            assert data["severity"] in valid_severities


# ===================================================================
# Medication Lookup Tool Tests
# ===================================================================


class TestMedicationLookup:
    def test_mock_data_by_generic_name(self):
        result = _check_mock_data("metformin")
        assert result is not None
        assert result["generic_name"] == "Metformin Hydrochloride"

    def test_mock_data_by_brand_name(self):
        result = _check_mock_data("Lipitor")
        assert result is not None
        assert result["generic_name"] == "Atorvastatin Calcium"

    def test_mock_data_not_found(self):
        result = _check_mock_data("nonexistent_drug")
        assert result is None

    def test_case_insensitive(self):
        result = _check_mock_data("METFORMIN")
        assert result is not None

    def test_all_mock_medications_have_required_fields(self):
        for name, data in MOCK_MEDICATIONS.items():
            assert "brand_names" in data
            assert "generic_name" in data
            assert "manufacturer" in data
            assert "indications" in data
            assert "warnings" in data
            assert "contraindications" in data
            assert "dosage_forms" in data
            assert "drug_class" in data
