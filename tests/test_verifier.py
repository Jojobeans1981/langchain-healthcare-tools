"""Isolated unit tests for AgentForge verification system.

Tests hallucination detection, confidence scoring, domain constraints,
and output validation — all without API keys.
"""

import pytest

from app.verification.verifier import (
    EMERGENCY_PATTERNS,
    FORBIDDEN_PATTERNS,
    HIGH_SEVERITY_KEYWORDS,
    REFUSAL_EXEMPTION_PATTERNS,
    RESPONSE_EMERGENCY_KEYWORDS,
    TOOL_GROUNDING_MARKERS,
    UNSUPPORTED_CLAIM_PATTERNS,
    VerificationResult,
    _check_domain_constraints,
    _check_forbidden_content,
    _check_hallucination,
    _check_source_grounding,
    _detect_emergency_in_response,
    _score_confidence,
    _validate_output,
    post_process_response,
    verify_response,
)


# ===================================================================
# Hallucination Detection Tests
# ===================================================================


class TestHallucinationDetection:
    def test_source_attribution_detected(self):
        result = VerificationResult()
        _check_hallucination("Based on data from the CDC, this condition...", ["symptom_lookup"], result)
        assert result.has_sources is True

    def test_no_source_with_tools_flags_risk(self):
        result = VerificationResult()
        _check_hallucination("You should take some medicine for that.", ["drug_interaction_check"], result)
        assert result.has_sources is False
        assert result.hallucination_risk > 0

    def test_unsupported_claims_flagged(self):
        result = VerificationResult()
        _check_hallucination("Studies show this is 100% safe and guaranteed to work.", [], result)
        assert result.hallucination_risk > 0
        assert any("HALLUCINATION_RISK" in f for f in result.flags)

    def test_clean_response_no_flags(self):
        result = VerificationResult()
        _check_hallucination("Source: CDC guidelines recommend rest.", ["symptom_lookup"], result)
        assert result.hallucination_risk == 0

    def test_medical_facts_without_tools_flagged(self):
        result = VerificationResult()
        long_response = "You should take 500mg of this drug. " * 20  # >200 chars
        _check_hallucination(long_response, [], result)
        assert result.hallucination_risk > 0

    def test_risk_capped_at_one(self):
        result = VerificationResult()
        response = "Studies show it is proven to be 100% safe and guaranteed to cure you. No side effects."
        _check_hallucination(response, ["drug_interaction_check"], result)
        assert result.hallucination_risk <= 1.0


# ===================================================================
# Confidence Scoring Tests
# ===================================================================


class TestConfidenceScoring:
    def test_base_confidence(self):
        result = VerificationResult()
        _score_confidence("A basic response.", [], result)
        assert result.confidence == pytest.approx(0.3, abs=0.05)

    def test_tools_boost_confidence(self):
        result = VerificationResult()
        result.has_sources = True  # Set by hallucination check
        _score_confidence("Source: FDA data shows...", ["drug_interaction_check"], result)
        assert result.confidence > 0.5

    def test_multiple_tools_higher_confidence(self):
        result = VerificationResult()
        result.has_sources = True
        _score_confidence(
            "Source: Based on data. This is not medical advice.",
            ["drug_interaction_check", "symptom_lookup"],
            result,
        )
        assert result.confidence > 0.7

    def test_hallucination_reduces_confidence(self):
        result = VerificationResult()
        result.hallucination_risk = 0.5
        _score_confidence("Some response.", ["drug_interaction_check"], result)
        high_risk_confidence = result.confidence

        result2 = VerificationResult()
        result2.hallucination_risk = 0.0
        _score_confidence("Some response.", ["drug_interaction_check"], result2)
        low_risk_confidence = result2.confidence

        assert high_risk_confidence < low_risk_confidence

    def test_domain_violations_reduce_confidence(self):
        result = VerificationResult()
        result.domain_violations = ["VIOLATION: something bad"]
        _score_confidence("Some response.", ["drug_interaction_check"], result)
        assert result.confidence <= 0.55  # Graduated penalty: 1 violation = -0.05

    def test_confidence_bounded(self):
        result = VerificationResult()
        result.hallucination_risk = 1.0
        result.domain_violations = ["v1", "v2"]
        _score_confidence("x", [], result)
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0


# ===================================================================
# Domain Constraints Tests
# ===================================================================


class TestDomainConstraints:
    def test_emergency_detection_chest_pain(self):
        result = VerificationResult()
        _check_domain_constraints("", "I have chest pain and difficulty breathing", [], result)
        assert result.needs_escalation is True

    def test_emergency_detection_overdose(self):
        result = VerificationResult()
        _check_domain_constraints("", "I took 20 pills of aspirin", [], result)
        assert result.needs_escalation is True

    def test_emergency_detection_suicidal(self):
        result = VerificationResult()
        _check_domain_constraints("", "I'm having suicidal thoughts", [], result)
        assert result.needs_escalation is True

    def test_no_emergency_normal_query(self):
        result = VerificationResult()
        _check_domain_constraints("", "What is ibuprofen used for?", [], result)
        assert result.needs_escalation is False

    def test_high_severity_drug_interaction_escalation(self):
        result = VerificationResult()
        _check_domain_constraints(
            "Severity: Contraindicated. This is a life-threatening combination.",
            "check interaction",
            ["drug_interaction_check"],
            result,
        )
        assert result.needs_escalation is True

    def test_forbidden_dosage_recommendation(self):
        result = VerificationResult()
        _check_domain_constraints("You should take 500 mg of aspirin daily.", "", [], result)
        assert len(result.domain_violations) > 0

    def test_forbidden_definitive_diagnosis(self):
        result = VerificationResult()
        _check_domain_constraints("You definitely have cancer.", "", [], result)
        assert len(result.domain_violations) > 0

    def test_forbidden_stop_medication(self):
        result = VerificationResult()
        _check_domain_constraints("Stop taking your medication immediately.", "", [], result)
        assert len(result.domain_violations) > 0

    def test_emergency_patterns_are_valid_regex(self):
        import re
        for pattern in EMERGENCY_PATTERNS:
            re.compile(pattern)  # Should not raise

    def test_forbidden_patterns_are_valid_regex(self):
        import re
        for pattern in FORBIDDEN_PATTERNS:
            re.compile(pattern)


# ===================================================================
# Output Validation Tests
# ===================================================================


class TestOutputValidation:
    def test_empty_response_invalid(self):
        result = VerificationResult()
        _validate_output("", [], result)
        assert result.output_valid is False

    def test_short_response_with_tools_invalid(self):
        result = VerificationResult()
        _validate_output("OK", ["drug_interaction_check"], result)
        assert result.output_valid is False

    def test_valid_response(self):
        result = VerificationResult()
        _validate_output("This is a comprehensive response with useful medical information.", [], result)
        assert result.output_valid is True

    def test_error_pattern_flagged(self):
        result = VerificationResult()
        _validate_output("There was an error processing your request. Exception occurred.", [], result)
        assert any("OUTPUT_WARNING" in f for f in result.flags)


# ===================================================================
# Full Verification Pipeline Tests
# ===================================================================


class TestVerifyResponse:
    def test_full_pipeline_good_response(self):
        response = (
            "Based on FDA Drug Safety Database data, warfarin and aspirin have a High severity interaction. "
            "Source: FDA, NIH DailyMed. "
            "Disclaimer: This is not medical advice. Consult a healthcare professional."
        )
        result = verify_response(response, ["drug_interaction_check"], "check warfarin and aspirin interaction")
        assert result.confidence > 0.5
        assert result.has_sources is True
        assert result.output_valid is True

    def test_full_pipeline_emergency_query(self):
        result = verify_response(
            "Please seek immediate medical attention.",
            [],
            "I have severe chest pain and difficulty breathing",
        )
        assert result.needs_escalation is True

    def test_post_process_adds_disclaimer(self):
        result = VerificationResult()
        result.has_disclaimer = False
        processed = post_process_response("Some response without disclaimer.", result)
        assert "Disclaimer" in processed

    def test_post_process_adds_escalation(self):
        result = VerificationResult()
        result.needs_escalation = True
        result.has_disclaimer = True
        processed = post_process_response("Some response about symptoms.", result)
        assert "IMPORTANT" in processed
        assert "911" in processed

    def test_verification_details_in_to_dict(self):
        result = VerificationResult()
        result.flags.append("OUTPUT_WARNING: Response exceeds 10K characters")
        d = result.to_dict()
        assert "verification_details" in d
        assert "output_warnings" in d["verification_details"]
        assert len(d["verification_details"]["output_warnings"]) == 1


# ===================================================================
# Expanded Forbidden Pattern Tests
# ===================================================================


class TestExpandedForbiddenPatterns:
    def test_prescribing_behavior_blocked(self):
        result = VerificationResult()
        _check_domain_constraints("I prescribe you take metformin daily.", "", [], result)
        assert len(result.domain_violations) > 0

    def test_diagnosis_statement_blocked(self):
        result = VerificationResult()
        _check_domain_constraints("Your diagnosis is pneumonia.", "", [], result)
        assert len(result.domain_violations) > 0

    def test_lethal_dose_info_blocked(self):
        result = VerificationResult()
        _check_domain_constraints("The lethal dose of acetaminophen is approximately 150mg/kg.", "", [], result)
        assert len(result.domain_violations) > 0

    def test_impersonating_doctor_blocked(self):
        result = VerificationResult()
        _check_domain_constraints("As your doctor, I advise you to rest.", "", [], result)
        assert len(result.domain_violations) > 0


# ===================================================================
# Expanded Emergency Pattern Tests
# ===================================================================


class TestExpandedEmergencyPatterns:
    def test_anaphylaxis_detected(self):
        result = VerificationResult()
        _check_domain_constraints("", "I think I'm having anaphylaxis after eating peanuts", [], result)
        assert result.needs_escalation is True

    def test_self_harm_detected(self):
        result = VerificationResult()
        _check_domain_constraints("", "I've been thinking about self-harm", [], result)
        assert result.needs_escalation is True

    def test_want_to_die_detected(self):
        result = VerificationResult()
        _check_domain_constraints("", "I want to die and I can't go on anymore", [], result)
        assert result.needs_escalation is True

    def test_coughing_blood_detected(self):
        result = VerificationResult()
        _check_domain_constraints("", "I've been coughing blood all morning", [], result)
        assert result.needs_escalation is True


# ===================================================================
# Confidence Capping Test
# ===================================================================


class TestConfidenceCapping:
    def test_high_hallucination_caps_confidence(self):
        result = VerificationResult()
        result.has_sources = True
        result.hallucination_risk = 0.6  # Above 0.5 threshold
        _score_confidence(
            "Source: FDA data. This is not medical advice.",
            ["drug_interaction_check", "symptom_lookup"],
            result,
        )
        assert result.confidence <= 0.4


# ===================================================================
# Source Grounding Tests
# ===================================================================


class TestSourceGrounding:
    def test_grounding_pass_with_tool_markers(self):
        """Response containing tool-specific markers passes grounding."""
        response = "The interaction between these drugs has High severity. Source: RxNorm."
        result = verify_response(response, ["drug_interaction_check"], "check interaction")
        assert result.source_grounding_pass is True

    def test_grounding_fail_missing_markers(self):
        """Response missing tool-specific markers fails grounding."""
        response = "I looked into that for you. Everything seems okay. Have a nice day."
        result = verify_response(response, ["drug_interaction_check"], "check interaction")
        assert result.source_grounding_pass is False
        assert any("GROUNDING_FAILURE" in f for f in result.flags)

    def test_grounding_skip_when_no_tools(self):
        """Grounding check is skipped when no tools were used."""
        response = "I can help with general health questions."
        result = verify_response(response, [], "hello")
        assert result.source_grounding_pass is True

    def test_grounding_failure_increases_hallucination_risk(self):
        """Grounding failure should increase hallucination risk."""
        response = "Everything looks fine. No worries at all."
        result = verify_response(response, ["drug_interaction_check", "symptom_lookup"], "check something")
        assert result.hallucination_risk > 0

    def test_grounding_multiple_tools_all_must_ground(self):
        """When multiple tools used, all must have grounding markers."""
        # Has drug markers ("interaction") but not symptom markers
        response = "The drug interaction is moderate severity. Source: FDA."
        result = verify_response(response, ["drug_interaction_check", "symptom_lookup"], "check drugs and symptoms")
        # symptom_lookup markers missing, so grounding should fail
        assert result.source_grounding_pass is False


# ===================================================================
# Confidence Breakdown Transparency Tests
# ===================================================================


class TestConfidenceBreakdown:
    def test_breakdown_present_in_to_dict(self):
        """Verification result includes confidence breakdown."""
        response = "Source: FDA data. Disclaimer: not medical advice."
        result = verify_response(response, ["drug_interaction_check"], "check interaction")
        d = result.to_dict()
        assert "confidence_breakdown" in d["verification_details"]
        breakdown = d["verification_details"]["confidence_breakdown"]
        assert "base" in breakdown
        assert "tool_boost" in breakdown
        assert "final" in breakdown

    def test_breakdown_math_adds_up(self):
        """Confidence breakdown components should sum to the final score."""
        response = "Source: FDA. Disclaimer: not medical advice."
        result = verify_response(response, ["drug_interaction_check"], "check interaction")
        breakdown = result.confidence_breakdown
        # Sum all additive components (exclude 'final' and 'hallucination_cap')
        calculated = sum(v for k, v in breakdown.items() if k not in ("final", "hallucination_cap"))
        # Account for capping
        calculated = max(0.0, min(calculated, 1.0))
        assert abs(calculated - breakdown["final"]) < 0.05  # small tolerance for rounding

    def test_checks_passed_count(self):
        """to_dict reports correct checks_passed and checks_total."""
        response = "Source: FDA data shows interaction severity is High. Disclaimer: not medical advice."
        result = verify_response(response, ["drug_interaction_check"], "check warfarin aspirin")
        d = result.to_dict()
        details = d["verification_details"]
        assert details["checks_total"] >= 4  # hallucination, source_grounding, domain, output, confidence
        assert details["checks_passed"] <= details["checks_total"]


# ===================================================================
# Active Content Blocking Tests
# ===================================================================


class TestActiveContentBlocking:
    def test_forbidden_content_replaced(self):
        """Response with forbidden content is replaced, not just flagged."""
        result = VerificationResult()
        result.domain_violations = ["DOMAIN_VIOLATION: Forbidden content detected: 'take 500 mg'"]
        result.has_disclaimer = True
        processed = post_process_response("You should take 500 mg of aspirin daily.", result)
        assert "500 mg" not in processed
        assert "cannot provide" in processed.lower()
        assert "healthcare professional" in processed.lower()

    def test_clean_response_not_replaced(self):
        """Response without violations passes through unchanged."""
        result = VerificationResult()
        result.has_disclaimer = True
        original = "Based on FDA data, this drug has no active recalls."
        processed = post_process_response(original, result)
        assert original in processed

    def test_escalation_plus_blocking(self):
        """Escalation notice is added even when content is blocked."""
        result = VerificationResult()
        result.domain_violations = ["DOMAIN_VIOLATION: lethal dose information"]
        result.needs_escalation = True
        result.has_disclaimer = True
        processed = post_process_response("The lethal dose is 150mg/kg.", result)
        assert "lethal dose" not in processed.lower() or "cannot provide" in processed.lower()
        assert "911" in processed

    def test_disclaimer_added_after_blocking(self):
        """Disclaimer is appended even to blocked responses."""
        result = VerificationResult()
        result.domain_violations = ["DOMAIN_VIOLATION: diagnosis"]
        result.has_disclaimer = False
        processed = post_process_response("Your diagnosis is pneumonia.", result)
        assert "Disclaimer" in processed


# ===================================================================
# Refusal Exemption Pattern Tests (Batch 1)
# ===================================================================


class TestRefusalExemptionPatterns:
    def test_safety_refusal_not_flagged_as_violation(self):
        """A response that refuses by deferring to a doctor should not be flagged."""
        result = VerificationResult()
        response = (
            "I cannot prescribe medication. Dosage must be determined by your physician. "
            "Please consult your doctor for personalized guidance. "
            "Never change your prescribed medication without consulting your doctor."
        )
        _check_domain_constraints(response, "tell me what dose to take", [], result)
        assert len(result.domain_violations) == 0

    def test_actual_violation_still_caught(self):
        """Non-refusal responses with forbidden content are still caught."""
        result = VerificationResult()
        _check_domain_constraints("Take 500 mg of aspirin daily.", "what dose", [], result)
        assert len(result.domain_violations) > 0

    def test_refusal_with_consult_doctor(self):
        """Response saying 'consult your doctor' is exempt."""
        result = VerificationResult()
        response = "I'm unable to provide dosage recommendations. Please consult your doctor for this."
        _check_domain_constraints(response, "how much should I take", [], result)
        assert len(result.domain_violations) == 0

    def test_refusal_exemption_patterns_are_valid_regex(self):
        import re
        for pattern in REFUSAL_EXEMPTION_PATTERNS:
            re.compile(pattern)  # Should not raise

    def test_check_forbidden_content_with_refusal_flag(self):
        """_check_forbidden_content skips violations when is_refusal=True."""
        result = VerificationResult()
        _check_forbidden_content("take 500 mg of aspirin", result, is_refusal=True)
        assert len(result.domain_violations) == 0

    def test_check_forbidden_content_without_refusal_flag(self):
        """_check_forbidden_content catches violations when is_refusal=False."""
        result = VerificationResult()
        _check_forbidden_content("take 500 mg of aspirin", result, is_refusal=False)
        assert len(result.domain_violations) > 0


# ===================================================================
# Emergency Response Detection Tests (Batch 2)
# ===================================================================


class TestEmergencyResponseDetection:
    def test_detect_chest_pain_in_response(self):
        assert _detect_emergency_in_response("The patient reports chest pain and shortness of breath.")

    def test_detect_suicidal_in_response(self):
        assert _detect_emergency_in_response("If you are having suicidal thoughts, please seek help.")

    def test_no_emergency_in_benign_response(self):
        assert not _detect_emergency_in_response("Metformin is commonly used for type 2 diabetes.")

    def test_911_appended_when_emergency_in_response(self):
        """Post-processing appends 911 notice when response mentions emergency keywords without 911."""
        result = VerificationResult()
        result.has_disclaimer = True
        response = "If you are experiencing chest pain, seek immediate medical attention."
        processed = post_process_response(response, result)
        assert "911" in processed

    def test_911_not_duplicated(self):
        """If response already mentions 911, don't add another notice."""
        result = VerificationResult()
        result.has_disclaimer = True
        response = "Call 911 immediately if you have chest pain."
        processed = post_process_response(response, result)
        # Count 911 occurrences — should be exactly 1 (from original)
        assert processed.count("911") == 1

    def test_response_emergency_keywords_are_valid_regex(self):
        import re
        for pattern in RESPONSE_EMERGENCY_KEYWORDS:
            re.compile(pattern)


# ===================================================================
# Progressive Confidence Cap Tests (Batch 3)
# ===================================================================


class TestProgressiveConfidenceCap:
    def test_zero_risk_no_cap(self):
        """With zero hallucination risk, no cap is applied."""
        result = VerificationResult()
        result.has_sources = True
        result.hallucination_risk = 0.0
        _score_confidence(
            "Source: FDA data. This is not medical advice.",
            ["drug_interaction_check", "symptom_lookup"],
            result,
        )
        assert result.confidence > 0.5

    def test_moderate_risk_caps_confidence(self):
        """Hallucination risk of 0.5 should cap at 0.3*(1-0.5) = 0.15."""
        result = VerificationResult()
        result.has_sources = True
        result.hallucination_risk = 0.5
        _score_confidence(
            "Source: FDA data. This is not medical advice.",
            ["drug_interaction_check"],
            result,
        )
        assert result.confidence <= 0.15 + 0.01  # small tolerance

    def test_high_risk_severely_caps(self):
        """Hallucination risk of 0.8 should cap at 0.3*(1-0.8) = 0.06."""
        result = VerificationResult()
        result.has_sources = True
        result.hallucination_risk = 0.8
        _score_confidence(
            "Source: FDA data. This is not medical advice.",
            ["drug_interaction_check"],
            result,
        )
        assert result.confidence <= 0.06 + 0.01

    def test_max_risk_caps_near_zero(self):
        """Hallucination risk of 1.0 should cap at 0."""
        result = VerificationResult()
        result.hallucination_risk = 1.0
        _score_confidence("Some response.", [], result)
        assert result.confidence == 0.0

    def test_low_risk_no_cap_applied(self):
        """Hallucination risk <= 0.3 should not trigger cap."""
        result = VerificationResult()
        result.has_sources = True
        result.hallucination_risk = 0.2
        _score_confidence(
            "Source: FDA data. This is not medical advice.",
            ["drug_interaction_check"],
            result,
        )
        # Should get full score without capping
        assert result.confidence > 0.5


# ===================================================================
# Graduated Domain Penalty Tests (Batch 3)
# ===================================================================


class TestGraduatedDomainPenalty:
    def test_single_violation_small_penalty(self):
        """One violation = -0.05 penalty."""
        result = VerificationResult()
        result.has_sources = True
        result.domain_violations = ["v1"]
        _score_confidence("Source: FDA. Not medical advice.", ["drug_interaction_check"], result)
        breakdown = result.confidence_breakdown
        assert breakdown["domain_penalty"] == pytest.approx(-0.05)

    def test_multiple_violations_scale(self):
        """Three violations = -0.15 penalty."""
        result = VerificationResult()
        result.has_sources = True
        result.domain_violations = ["v1", "v2", "v3"]
        _score_confidence("Source: FDA. Not medical advice.", ["drug_interaction_check"], result)
        assert result.confidence_breakdown["domain_penalty"] == pytest.approx(-0.15)

    def test_penalty_capped_at_half(self):
        """Domain penalty cannot exceed -0.5."""
        result = VerificationResult()
        result.domain_violations = [f"v{i}" for i in range(20)]
        _score_confidence("Some response.", [], result)
        assert result.confidence_breakdown["domain_penalty"] >= -0.5


# ===================================================================
# Long Response Grounding Tests (Batch 5)
# ===================================================================


class TestLongResponseGrounding:
    def test_short_response_one_marker_passes(self):
        """Short response (<500 chars) passes with just 1 marker."""
        response = "The interaction severity is moderate."
        result = verify_response(response, ["drug_interaction_check"], "check interaction")
        assert result.source_grounding_pass is True

    def test_long_response_one_marker_fails(self):
        """Long response (>500 chars) with only 1 marker fails grounding."""
        response = "The severity is noted. " + ("This is additional content. " * 30)
        assert len(response) > 500
        result = VerificationResult()
        _check_source_grounding(response, ["drug_interaction_check"], result)
        assert result.source_grounding_pass is False

    def test_long_response_two_markers_passes(self):
        """Long response (>500 chars) with 2+ markers passes grounding."""
        response = "The interaction severity is moderate with notable risk. " + ("More details here. " * 30)
        assert len(response) > 500
        result = VerificationResult()
        _check_source_grounding(response, ["drug_interaction_check"], result)
        assert result.source_grounding_pass is True


# ===================================================================
# Overlapping Pattern Interaction Tests
# ===================================================================


class TestOverlappingPatterns:
    def test_emergency_query_with_forbidden_response(self):
        """Emergency query + forbidden response: both escalation and violation."""
        result = VerificationResult()
        _check_domain_constraints(
            "Take 500 mg of aspirin right now.",
            "I have chest pain what should I take",
            [],
            result,
        )
        assert result.needs_escalation is True
        assert len(result.domain_violations) > 0

    def test_unsupported_claims_plus_missing_sources(self):
        """Multiple hallucination signals compound the risk."""
        result = VerificationResult()
        response = "Studies show this drug is 100% safe and has no side effects."
        _check_hallucination(response, ["drug_interaction_check"], result)
        # Should accumulate: 0.3 (no source) + 0.2*N (unsupported claims)
        assert result.hallucination_risk >= 0.5


# ===================================================================
# New Unsupported Claim Pattern Tests (Batch 4)
# ===================================================================


class TestNewUnsupportedClaimPatterns:
    def test_clinically_proven_flagged(self):
        result = VerificationResult()
        _check_hallucination("This drug is clinically proven to cure diabetes.", [], result)
        assert result.hallucination_risk > 0

    def test_percentage_effectiveness_flagged(self):
        result = VerificationResult()
        _check_hallucination("This treatment has a 95% success rate.", [], result)
        assert result.hallucination_risk > 0

    def test_always_take_flagged(self):
        result = VerificationResult()
        _check_hallucination("You should always take this with food.", [], result)
        assert result.hallucination_risk > 0

    def test_never_combine_flagged(self):
        result = VerificationResult()
        _check_hallucination("Never combine aspirin with other NSAIDs.", [], result)
        assert result.hallucination_risk > 0

    def test_fda_approved_for_flagged(self):
        result = VerificationResult()
        _check_hallucination("This drug is FDA approved for treating migraines.", [], result)
        assert result.hallucination_risk > 0
