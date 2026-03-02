"""Tests for the LLM-as-judge semantic verification layer.

All tests mock the LLM call so they run without API keys.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.verification.llm_judge import (
    JudgeResult,
    _parse_judge_response,
    apply_judge_to_verification,
    judge_response,
)
from app.verification.verifier import VerificationResult


# ===================================================================
# JudgeResult unit tests
# ===================================================================


class TestJudgeResult:
    def test_no_violations_by_default(self):
        result = JudgeResult()
        assert not result.has_violations
        assert result.violation_flags == []

    def test_single_violation(self):
        result = JudgeResult()
        result.prescribes_dosage = True
        assert result.has_violations
        assert len(result.violation_flags) == 1
        assert "dosage" in result.violation_flags[0].lower()

    def test_multiple_violations(self):
        result = JudgeResult()
        result.prescribes_dosage = True
        result.makes_diagnosis = True
        result.impersonates_provider = True
        assert len(result.violation_flags) == 3

    def test_to_dict(self):
        result = JudgeResult()
        result.judge_available = True
        result.judge_latency_ms = 150.5
        result.prescribes_dosage = True
        d = result.to_dict()
        assert d["judge_available"] is True
        assert d["judge_latency_ms"] == 150.5
        assert d["prescribes_dosage"] is True
        assert len(d["violations"]) == 1


# ===================================================================
# JSON parsing tests
# ===================================================================


class TestParseJudgeResponse:
    def test_clean_json(self):
        raw = '{"prescribes_dosage": true, "makes_diagnosis": false}'
        parsed = _parse_judge_response(raw)
        assert parsed["prescribes_dosage"] is True
        assert parsed["makes_diagnosis"] is False

    def test_markdown_fenced_json(self):
        raw = '```json\n{"prescribes_dosage": true}\n```'
        parsed = _parse_judge_response(raw)
        assert parsed["prescribes_dosage"] is True

    def test_json_with_surrounding_text(self):
        raw = 'Here is my analysis: {"prescribes_dosage": false, "makes_diagnosis": true} end.'
        parsed = _parse_judge_response(raw)
        assert parsed["makes_diagnosis"] is True

    def test_invalid_json_returns_empty(self):
        raw = "This is not JSON at all"
        parsed = _parse_judge_response(raw)
        assert parsed == {}

    def test_empty_string(self):
        parsed = _parse_judge_response("")
        assert parsed == {}


# ===================================================================
# judge_response integration tests (mocked LLM)
# ===================================================================


class TestJudgeResponse:
    @pytest.mark.asyncio
    async def test_safe_response_no_violations(self):
        mock_llm = AsyncMock()
        mock_output = MagicMock()
        mock_output.content = json.dumps({
            "prescribes_dosage": False,
            "makes_diagnosis": False,
            "contradicts_tool": False,
            "provides_harmful_info": False,
            "impersonates_provider": False,
        })
        mock_llm.ainvoke = AsyncMock(return_value=mock_output)

        with patch("app.verification.llm_judge._get_judge_llm", return_value=mock_llm):
            result = await judge_response(
                "Warfarin and aspirin have a high-severity interaction. Source: FDA.",
                ["drug_interaction_check"],
                "Check warfarin and aspirin interaction",
            )

        assert result.judge_available
        assert not result.has_violations

    @pytest.mark.asyncio
    async def test_dosage_violation_detected(self):
        mock_llm = AsyncMock()
        mock_output = MagicMock()
        mock_output.content = json.dumps({
            "prescribes_dosage": True,
            "makes_diagnosis": False,
            "contradicts_tool": False,
            "provides_harmful_info": False,
            "impersonates_provider": False,
        })
        mock_llm.ainvoke = AsyncMock(return_value=mock_output)

        with patch("app.verification.llm_judge._get_judge_llm", return_value=mock_llm):
            result = await judge_response(
                "The standard dose is 500mg of ibuprofen for adults.",
                ["medication_lookup"],
                "Tell me about ibuprofen",
            )

        assert result.judge_available
        assert result.has_violations
        assert result.prescribes_dosage

    @pytest.mark.asyncio
    async def test_contradiction_detected(self):
        mock_llm = AsyncMock()
        mock_output = MagicMock()
        mock_output.content = json.dumps({
            "prescribes_dosage": False,
            "makes_diagnosis": False,
            "contradicts_tool": True,
            "provides_harmful_info": False,
            "impersonates_provider": False,
        })
        mock_llm.ainvoke = AsyncMock(return_value=mock_output)

        with patch("app.verification.llm_judge._get_judge_llm", return_value=mock_llm):
            result = await judge_response(
                "There is no significant risk combining these drugs.",
                ["drug_interaction_check"],
                "Check warfarin and aspirin",
            )

        assert result.contradicts_tool

    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty_result(self):
        with patch("app.verification.llm_judge._get_judge_llm", return_value=None):
            result = await judge_response(
                "Some response text that is long enough to not be skipped.",
                ["symptom_lookup"],
                "I have a headache",
            )

        assert not result.judge_available
        assert not result.has_violations

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_result(self):
        mock_llm = AsyncMock()

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(10)  # Will timeout

        mock_llm.ainvoke = slow_invoke

        with patch("app.verification.llm_judge._get_judge_llm", return_value=mock_llm):
            result = await judge_response(
                "Some response that takes too long to judge semantically.",
                ["medication_lookup"],
                "Tell me about aspirin",
                timeout_seconds=0.1,  # Very short timeout
            )

        assert not result.judge_available
        assert not result.has_violations

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_result(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM crashed"))

        with patch("app.verification.llm_judge._get_judge_llm", return_value=mock_llm):
            result = await judge_response(
                "Some response that causes an LLM error during judging.",
                ["symptom_lookup"],
                "I have symptoms",
            )

        assert not result.judge_available
        assert not result.has_violations

    @pytest.mark.asyncio
    async def test_short_response_skips_judge(self):
        """Responses under 50 chars should skip the judge entirely."""
        with patch("app.verification.llm_judge._get_judge_llm") as mock_get:
            result = await judge_response("Short.", [], "query")
            mock_get.assert_not_called()
            assert not result.judge_available

    @pytest.mark.asyncio
    async def test_malformed_json_from_llm(self):
        mock_llm = AsyncMock()
        mock_output = MagicMock()
        mock_output.content = "I cannot analyze this as JSON. Sorry!"
        mock_llm.ainvoke = AsyncMock(return_value=mock_output)

        with patch("app.verification.llm_judge._get_judge_llm", return_value=mock_llm):
            result = await judge_response(
                "A valid response that the judge fails to parse correctly.",
                ["medication_lookup"],
                "Tell me about metformin",
            )

        # Should succeed but with no violations (all default to False)
        assert result.judge_available
        assert not result.has_violations


# ===================================================================
# apply_judge_to_verification tests
# ===================================================================


class TestApplyJudgeToVerification:
    def test_no_violations_no_changes(self):
        judge = JudgeResult()
        judge.judge_available = True
        verification = VerificationResult()
        original_confidence = verification.confidence
        apply_judge_to_verification(judge, verification)
        # No violations = no changes except the check being added
        assert verification.confidence == original_confidence
        assert "llm_judge" in verification.verification_checks
        assert verification.verification_checks["llm_judge"] is True

    def test_dosage_violation_adds_domain_violation(self):
        judge = JudgeResult()
        judge.judge_available = True
        judge.prescribes_dosage = True
        verification = VerificationResult()
        verification.confidence = 0.8
        apply_judge_to_verification(judge, verification)
        assert len(verification.domain_violations) == 1
        assert "dosage" in verification.domain_violations[0].lower()
        assert verification.confidence < 0.8  # Penalty applied

    def test_contradiction_fails_grounding(self):
        judge = JudgeResult()
        judge.judge_available = True
        judge.contradicts_tool = True
        verification = VerificationResult()
        verification.source_grounding_pass = True
        apply_judge_to_verification(judge, verification)
        assert not verification.source_grounding_pass
        assert verification.hallucination_risk > 0.0

    def test_harmful_info_heavy_penalty(self):
        judge = JudgeResult()
        judge.judge_available = True
        judge.provides_harmful_info = True
        verification = VerificationResult()
        verification.hallucination_risk = 0.0
        apply_judge_to_verification(judge, verification)
        assert verification.hallucination_risk >= 0.3

    def test_multiple_violations_compound(self):
        judge = JudgeResult()
        judge.judge_available = True
        judge.prescribes_dosage = True
        judge.makes_diagnosis = True
        judge.contradicts_tool = True
        verification = VerificationResult()
        verification.confidence = 0.9
        apply_judge_to_verification(judge, verification)
        assert len(verification.domain_violations) == 2
        assert not verification.source_grounding_pass
        # 3 violations * 0.1 penalty = 0.3 reduction
        assert verification.confidence <= 0.6

    def test_unavailable_judge_no_changes(self):
        judge = JudgeResult()
        judge.judge_available = False  # Judge didn't run
        judge.prescribes_dosage = True  # Even with violations set
        verification = VerificationResult()
        original_flags = len(verification.flags)
        apply_judge_to_verification(judge, verification)
        # Should not apply anything when judge wasn't available
        assert len(verification.flags) == original_flags
