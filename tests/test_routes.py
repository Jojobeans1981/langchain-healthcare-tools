"""Isolated unit tests for AgentForge FastAPI routes.

Tests API endpoints with mocked agent — no API keys needed.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ===================================================================
# Health & Debug Endpoints
# ===================================================================


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "model" in data

    def test_debug_returns_config(self):
        resp = client.get("/debug")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_provider" in data
        assert "model_name" in data
        assert "agent_creation" in data


# ===================================================================
# Chat Endpoint
# ===================================================================


MOCK_CHAT_RESULT = {
    "response": "Warfarin and aspirin have a High severity interaction.",
    "sources": ["FDA Drug Safety Database"],
    "confidence": 0.55,
    "tools_used": ["drug_interaction_check"],
    "session_id": "test-session",
    "trace_id": "abc123",
    "latency_ms": 1500.0,
    "tokens": {"input": 100, "output": 50, "total": 150},
    "verification": {
        "has_sources": False,
        "has_disclaimer": False,
        "confidence": 0.55,
        "flags": [],
        "needs_escalation": False,
        "hallucination_risk": 0.0,
        "domain_violations": [],
        "output_valid": True,
        "verification_checks": {},
        "verification_details": {},
    },
}


class TestChatEndpoint:
    @patch("app.api.routes.chat", new_callable=AsyncMock, return_value=MOCK_CHAT_RESULT)
    def test_chat_success(self, mock_chat):
        resp = client.post("/api/chat", json={"message": "Check warfarin and aspirin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "verification" in data
        assert "confidence" in data
        assert data["tools_used"] == ["drug_interaction_check"]
        mock_chat.assert_called_once()

    @patch("app.api.routes.chat", new_callable=AsyncMock, return_value=MOCK_CHAT_RESULT)
    def test_chat_assigns_session_id(self, mock_chat):
        resp = client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        # Should have a session_id even if not provided
        assert data["session_id"]

    @patch("app.api.routes.chat", new_callable=AsyncMock, return_value=MOCK_CHAT_RESULT)
    def test_chat_uses_provided_session_id(self, mock_chat):
        resp = client.post("/api/chat", json={"message": "hello", "session_id": "my-session"})
        assert resp.status_code == 200
        # Verify agent was called with the provided session_id
        call_kwargs = mock_chat.call_args
        assert call_kwargs.kwargs.get("session_id") == "my-session" or call_kwargs[1].get("session_id") == "my-session"

    def test_chat_empty_message_rejected(self):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422  # Validation error

    @patch("app.api.routes.chat", new_callable=AsyncMock, return_value=MOCK_CHAT_RESULT)
    def test_chat_response_includes_verification(self, mock_chat):
        resp = client.post("/api/chat", json={"message": "test query"})
        data = resp.json()
        verification = data["verification"]
        assert "has_sources" in verification
        assert "confidence" in verification
        assert "hallucination_risk" in verification
        assert "output_valid" in verification


# ===================================================================
# Feedback Endpoint
# ===================================================================


class TestFeedbackEndpoint:
    @patch("app.api.routes.record_feedback")
    def test_feedback_thumbs_up(self, mock_feedback):
        resp = client.post("/api/feedback", json={
            "trace_id": "t-123",
            "session_id": "s-456",
            "rating": "up",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_feedback.assert_called_once_with(
            trace_id="t-123", session_id="s-456", rating="up", correction=""
        )

    @patch("app.api.routes.record_feedback")
    def test_feedback_thumbs_down_with_correction(self, mock_feedback):
        resp = client.post("/api/feedback", json={
            "trace_id": "t-789",
            "session_id": "s-101",
            "rating": "down",
            "correction": "The drug interaction severity was wrong",
        })
        assert resp.status_code == 200
        mock_feedback.assert_called_once()

    def test_feedback_invalid_rating(self):
        resp = client.post("/api/feedback", json={
            "trace_id": "t-123",
            "rating": "maybe",
        })
        assert resp.status_code == 422


# ===================================================================
# Dashboard Endpoint
# ===================================================================


class TestDashboardEndpoint:
    def test_dashboard_returns_stats(self):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data


# ===================================================================
# Clear Session Endpoint
# ===================================================================


class TestClearSessionEndpoint:
    def test_clear_session(self):
        resp = client.post("/api/clear-session", json={"session_id": "test-clear"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
