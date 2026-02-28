"""Unit tests for confidence-based fallback in healthcare_agent.chat().

Verifies PRD 3 requirement: "Automatically switch to a more powerful model
if confidence is <70%." All tests run with mocked LLMs — no API keys needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.verification.verifier import VerificationResult


def _make_verification(confidence: float, needs_escalation: bool = False) -> VerificationResult:
    """Build a VerificationResult with the given confidence."""
    v = VerificationResult()
    v.confidence = confidence
    v.needs_escalation = needs_escalation
    v.has_sources = True
    v.has_disclaimer = True
    return v


def _make_agent_result(text: str):
    """Build a fake LangGraph agent result dict."""
    msg = MagicMock()
    msg.type = "ai"
    msg.content = text
    msg.tool_calls = None
    msg.usage_metadata = None
    msg.response_metadata = {}
    # hasattr checks
    msg.__class__ = type("FakeMsg", (), {
        "type": property(lambda s: "ai"),
        "content": property(lambda s: text),
    })
    return {"messages": [msg]}


# Patches common to every test — order matters (bottom-up in decorator stack)
_PATCHES = {
    "get_agent": "app.agent.healthcare_agent.get_agent",
    "create_agent": "app.agent.healthcare_agent.create_agent",
    "verify": "app.agent.healthcare_agent.verify_response",
    "post_proc": "app.agent.healthcare_agent.post_process_response",
    "get_history": "app.agent.healthcare_agent.get_session_history",
    "trim": "app.agent.healthcare_agent.trim_history",
    "tracer_cls": "app.agent.healthcare_agent.RequestTracer",
    "fallback_prov": "app.agent.healthcare_agent._get_fallback_provider",
}


def _setup_mocks(
    mock_get_agent,
    mock_create_agent,
    mock_verify,
    mock_post_proc,
    mock_get_history,
    mock_trim,
    mock_tracer_cls,
    mock_fallback_prov,
    *,
    primary_text="Primary response",
    fallback_text="Fallback response",
    primary_confidence=0.5,
    fallback_confidence=0.85,
    fallback_provider="gemini",
    primary_escalation=False,
    fallback_escalation=False,
):
    """Wire up all mocks and return handles for assertions."""
    # History mock
    history = MagicMock()
    mock_get_history.return_value = history

    # Tracer mock
    tracer = MagicMock()
    tracer.finish.return_value = MagicMock(total_latency_ms=100.0)
    mock_tracer_cls.return_value = tracer

    # Primary agent
    primary_agent = AsyncMock()
    primary_agent.ainvoke = AsyncMock(return_value=_make_agent_result(primary_text))
    mock_get_agent.return_value = primary_agent

    # Fallback agent
    fallback_agent = AsyncMock()
    fallback_agent.ainvoke = AsyncMock(return_value=_make_agent_result(fallback_text))
    mock_create_agent.return_value = fallback_agent

    # Verification: first call → primary, second call → fallback
    primary_verif = _make_verification(primary_confidence, primary_escalation)
    fallback_verif = _make_verification(fallback_confidence, fallback_escalation)
    mock_verify.side_effect = [primary_verif, fallback_verif]

    # post_process just returns what it gets
    mock_post_proc.side_effect = lambda resp, _v: resp

    # Fallback provider
    mock_fallback_prov.return_value = fallback_provider

    return {
        "primary_agent": primary_agent,
        "fallback_agent": fallback_agent,
        "tracer": tracer,
        "primary_verif": primary_verif,
        "fallback_verif": fallback_verif,
    }


# ===================================================================
# Test: Fallback triggers when confidence < 0.7
# ===================================================================


class TestConfidenceFallbackTriggers:
    @patch(_PATCHES["fallback_prov"])
    @patch(_PATCHES["tracer_cls"])
    @patch(_PATCHES["trim"])
    @patch(_PATCHES["get_history"])
    @patch(_PATCHES["post_proc"])
    @patch(_PATCHES["verify"])
    @patch(_PATCHES["create_agent"])
    @patch(_PATCHES["get_agent"])
    async def test_fallback_used_when_confidence_low(self, *mocks):
        """When primary confidence < 0.7 and fallback is better, use fallback response."""
        handles = _setup_mocks(*mocks, primary_confidence=0.5, fallback_confidence=0.85)

        from app.agent.healthcare_agent import chat
        result = await chat("What is aspirin used for?", session_id="test-1")

        # Fallback agent should have been created
        mocks[1].assert_called_once()  # create_agent
        # verify_response should be called twice (primary + fallback)
        assert mocks[2].call_count == 2
        # Response should be the fallback text
        assert result["response"] == "Fallback response"
        assert result["confidence"] == 0.85

    @patch(_PATCHES["fallback_prov"])
    @patch(_PATCHES["tracer_cls"])
    @patch(_PATCHES["trim"])
    @patch(_PATCHES["get_history"])
    @patch(_PATCHES["post_proc"])
    @patch(_PATCHES["verify"])
    @patch(_PATCHES["create_agent"])
    @patch(_PATCHES["get_agent"])
    async def test_fallback_keeps_original_when_worse(self, *mocks):
        """When fallback confidence is worse, keep original response."""
        handles = _setup_mocks(
            *mocks,
            primary_confidence=0.5,
            fallback_confidence=0.3,  # worse
        )

        from app.agent.healthcare_agent import chat
        result = await chat("What is aspirin used for?", session_id="test-2")

        # Should still use original since fallback was worse
        assert result["response"] == "Primary response"
        assert result["confidence"] == 0.5


# ===================================================================
# Test: Fallback skipped when confidence >= 0.7
# ===================================================================


class TestConfidenceFallbackSkipped:
    @patch(_PATCHES["fallback_prov"])
    @patch(_PATCHES["tracer_cls"])
    @patch(_PATCHES["trim"])
    @patch(_PATCHES["get_history"])
    @patch(_PATCHES["post_proc"])
    @patch(_PATCHES["verify"])
    @patch(_PATCHES["create_agent"])
    @patch(_PATCHES["get_agent"])
    async def test_no_fallback_when_confidence_high(self, *mocks):
        """When primary confidence >= 0.7, no fallback attempt."""
        handles = _setup_mocks(*mocks, primary_confidence=0.75, fallback_confidence=0.9)

        from app.agent.healthcare_agent import chat
        result = await chat("What is aspirin used for?", session_id="test-3")

        # create_agent should NOT be called (no fallback)
        mocks[1].assert_not_called()  # create_agent
        # verify_response called only once
        assert mocks[2].call_count == 1
        assert result["response"] == "Primary response"
        assert result["confidence"] == 0.75


# ===================================================================
# Test: No fallback provider available
# ===================================================================


class TestConfidenceFallbackNoProvider:
    @patch(_PATCHES["fallback_prov"])
    @patch(_PATCHES["tracer_cls"])
    @patch(_PATCHES["trim"])
    @patch(_PATCHES["get_history"])
    @patch(_PATCHES["post_proc"])
    @patch(_PATCHES["verify"])
    @patch(_PATCHES["create_agent"])
    @patch(_PATCHES["get_agent"])
    async def test_no_fallback_when_no_provider(self, *mocks):
        """When no fallback provider is configured, skip silently."""
        handles = _setup_mocks(
            *mocks,
            primary_confidence=0.4,
            fallback_provider=None,  # no fallback available
        )

        from app.agent.healthcare_agent import chat
        result = await chat("What is aspirin used for?", session_id="test-4")

        # create_agent should NOT be called
        mocks[1].assert_not_called()
        # verify called once (primary only)
        assert mocks[2].call_count == 1
        assert result["response"] == "Primary response"
        assert result["confidence"] == 0.4


# ===================================================================
# Test: Fallback skipped on escalation
# ===================================================================


class TestConfidenceFallbackEscalation:
    @patch(_PATCHES["fallback_prov"])
    @patch(_PATCHES["tracer_cls"])
    @patch(_PATCHES["trim"])
    @patch(_PATCHES["get_history"])
    @patch(_PATCHES["post_proc"])
    @patch(_PATCHES["verify"])
    @patch(_PATCHES["create_agent"])
    @patch(_PATCHES["get_agent"])
    async def test_no_fallback_when_escalation_needed(self, *mocks):
        """When needs_escalation is True, skip confidence fallback even if low."""
        handles = _setup_mocks(
            *mocks,
            primary_confidence=0.3,
            primary_escalation=True,  # emergency
        )

        from app.agent.healthcare_agent import chat
        result = await chat("I'm having chest pain", session_id="test-5")

        # create_agent should NOT be called (escalation bypasses fallback)
        mocks[1].assert_not_called()
        assert mocks[2].call_count == 1


# ===================================================================
# Test: Fallback exception handled gracefully
# ===================================================================


class TestConfidenceFallbackError:
    @patch(_PATCHES["fallback_prov"])
    @patch(_PATCHES["tracer_cls"])
    @patch(_PATCHES["trim"])
    @patch(_PATCHES["get_history"])
    @patch(_PATCHES["post_proc"])
    @patch(_PATCHES["verify"])
    @patch(_PATCHES["create_agent"])
    @patch(_PATCHES["get_agent"])
    async def test_fallback_exception_uses_original(self, *mocks):
        """When fallback agent raises, fall back to original response gracefully."""
        handles = _setup_mocks(*mocks, primary_confidence=0.5, fallback_confidence=0.85)
        # Make fallback agent raise
        handles["fallback_agent"].ainvoke.side_effect = RuntimeError("Fallback API error")

        from app.agent.healthcare_agent import chat
        result = await chat("What is aspirin used for?", session_id="test-6")

        # Should use original response despite fallback failure
        assert result["response"] == "Primary response"
        assert result["confidence"] == 0.5
