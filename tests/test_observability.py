"""Isolated unit tests for AgentForge observability module.

Tests trace records, request tracing, and dashboard stats — no API keys needed.
"""

import time

import pytest

from app.observability import (
    RequestTracer,
    TraceRecord,
    _traces,
    get_dashboard_stats,
    record_feedback,
)


class TestTraceRecord:
    def test_default_values(self):
        record = TraceRecord()
        assert record.trace_id == ""
        assert record.total_latency_ms == 0.0
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.error is None
        assert record.tools_called == []

    def test_custom_values(self):
        record = TraceRecord(
            trace_id="test-123",
            query="test query",
            tools_called=["drug_interaction_check"],
            confidence=0.85,
        )
        assert record.trace_id == "test-123"
        assert record.query == "test query"
        assert record.confidence == 0.85
        assert "drug_interaction_check" in record.tools_called


class TestRequestTracer:
    def test_basic_trace_lifecycle(self):
        tracer = RequestTracer(query="test query", session_id="sess-1", trace_id="t-1")
        tracer.start()
        time.sleep(0.01)  # Small delay to measure
        tracer.start_llm()
        time.sleep(0.01)
        tracer.end_llm()
        tracer.end_tool("drug_interaction_check")
        tracer.set_tokens(100, 50)
        tracer.set_response("Test response", confidence=0.8, sources=["FDA"])
        record = tracer.finish()

        assert record.trace_id == "t-1"
        assert record.session_id == "sess-1"
        assert record.total_latency_ms > 0
        assert record.llm_latency_ms > 0
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert "drug_interaction_check" in record.tools_called
        assert record.response == "Test response"

    def test_error_tracking(self):
        tracer = RequestTracer(query="error query", session_id="sess-2", trace_id="t-2")
        tracer.start()
        tracer.set_error("Connection timeout", category="TimeoutError")
        record = tracer.finish()

        assert record.error == "Connection timeout"
        assert record.error_category == "TimeoutError"

    def test_groq_zero_cost(self):
        tracer = RequestTracer(query="test", session_id="s", trace_id="t")
        tracer.start()
        tracer.set_tokens(1000, 500)
        record = tracer.finish()
        # With Groq as provider, cost should be $0
        assert record.estimated_cost_usd == 0.0

    def test_response_truncation(self):
        tracer = RequestTracer(query="test", session_id="s", trace_id="t")
        tracer.start()
        long_response = "x" * 5000
        tracer.set_response(long_response, confidence=0.5, sources=[])
        record = tracer.finish()
        assert len(record.response) <= 1000


class TestDashboardStats:
    def test_empty_traces(self):
        # Save and restore state
        original = _traces.copy()
        _traces.clear()
        stats = get_dashboard_stats()
        assert stats["total_requests"] == 0
        _traces.extend(original)

    def test_stats_with_traces(self):
        original = _traces.copy()
        _traces.clear()

        # Add mock traces
        t1 = TraceRecord(
            trace_id="s1",
            total_latency_ms=1000,
            confidence=0.8,
            total_tokens=200,
            estimated_cost_usd=0.0,
            tools_called=["drug_interaction_check"],
        )
        t2 = TraceRecord(
            trace_id="s2",
            total_latency_ms=2000,
            confidence=0.6,
            total_tokens=300,
            estimated_cost_usd=0.0,
            tools_called=["symptom_lookup"],
            error="timeout",
            error_category="TimeoutError",
        )
        _traces.extend([t1, t2])

        stats = get_dashboard_stats()
        assert stats["total_requests"] == 2
        assert stats["error_count"] == 1
        assert stats["avg_latency_ms"] == 1500.0
        assert stats["avg_confidence"] == 0.7
        assert stats["total_tokens"] == 500
        assert stats["tool_usage"]["drug_interaction_check"] == 1
        assert stats["tool_usage"]["symptom_lookup"] == 1

        _traces.clear()
        _traces.extend(original)
