"""Observability module for AgentForge Healthcare AI Agent.

Implements all 6 observability requirements from the PRD:
1. Trace Logging - Full trace of each request
2. Latency Tracking - Time breakdown for LLM, tools, total
3. Error Tracking - Capture and categorize failures
4. Token Usage - Input/output tokens per request, cost tracking
5. Eval Results - Historical eval scores
6. User Feedback - Thumbs up/down mechanism

Uses LangSmith when available, falls back to structured local logging.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Local storage for observability data
DATA_DIR = Path(__file__).parent.parent / "data" / "observability"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TraceRecord:
    """Full trace of a single agent request."""
    trace_id: str = ""
    session_id: str = ""
    timestamp: str = ""
    # Input
    query: str = ""
    # Processing
    tools_called: list[str] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    # Output
    response: str = ""
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    verification_flags: list[str] = field(default_factory=list)
    # Latency
    total_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    tool_latency_ms: float = 0.0
    verification_latency_ms: float = 0.0
    # Tokens
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    # Errors
    error: str | None = None
    error_category: str | None = None


class RequestTracer:
    """Context manager for tracing a single request through the agent pipeline."""

    def __init__(self, query: str, session_id: str, trace_id: str):
        self.record = TraceRecord(
            trace_id=trace_id,
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            query=query,
        )
        self._start_time: float = 0
        self._tool_start: float = 0
        self._llm_start: float = 0

    def start(self):
        self._start_time = time.time()
        return self

    def start_llm(self):
        self._llm_start = time.time()

    def end_llm(self):
        if self._llm_start:
            self.record.llm_latency_ms = (time.time() - self._llm_start) * 1000

    def start_tool(self):
        self._tool_start = time.time()

    def end_tool(self, tool_name: str, result_summary: str = ""):
        if self._tool_start:
            elapsed = (time.time() - self._tool_start) * 1000
            self.record.tool_latency_ms += elapsed
        self.record.tools_called.append(tool_name)
        self.record.tool_results.append({"tool": tool_name, "summary": result_summary[:200]})

    def set_response(self, response: str, confidence: float, sources: list[str]):
        self.record.response = response[:1000]  # Truncate for storage
        self.record.confidence = confidence
        self.record.sources = sources

    def set_verification(self, flags: list[str], verification_latency_ms: float = 0):
        self.record.verification_flags = flags
        self.record.verification_latency_ms = verification_latency_ms

    def set_tokens(self, input_tokens: int, output_tokens: int):
        self.record.input_tokens = input_tokens
        self.record.output_tokens = output_tokens
        self.record.total_tokens = input_tokens + output_tokens
        # Cost depends on provider
        from app.config import settings
        if settings.llm_provider.lower() == "groq":
            # Groq free tier — no cost
            self.record.estimated_cost_usd = 0.0
        else:
            # Gemini 2.0 Flash pricing: $0.10/1M input, $0.40/1M output
            self.record.estimated_cost_usd = (
                (input_tokens / 1_000_000 * 0.10) + (output_tokens / 1_000_000 * 0.40)
            )

    def set_error(self, error: str, category: str = "unknown"):
        self.record.error = error
        self.record.error_category = category

    def finish(self) -> TraceRecord:
        self.record.total_latency_ms = (time.time() - self._start_time) * 1000
        # Save trace
        _save_trace(self.record)
        return self.record


# ===================================================================
# Trace Storage
# ===================================================================

_traces: list[TraceRecord] = []
_feedback: list[dict] = []
_eval_history: list[dict] = []


def _save_trace(trace: TraceRecord):
    """Save a trace record to memory and optionally to disk."""
    _traces.append(trace)

    # Log structured trace
    logger.info(
        "TRACE: id=%s query=%s tools=%s confidence=%.2f latency=%.0fms tokens=%d cost=$%.6f",
        trace.trace_id,
        trace.query[:50],
        trace.tools_called,
        trace.confidence,
        trace.total_latency_ms,
        trace.total_tokens,
        trace.estimated_cost_usd,
    )

    if trace.error:
        logger.error(
            "TRACE_ERROR: id=%s category=%s error=%s",
            trace.trace_id,
            trace.error_category,
            trace.error,
        )

    # Persist to disk periodically
    if len(_traces) % 10 == 0:
        _flush_traces()


def _flush_traces():
    """Write traces to disk."""
    try:
        trace_file = DATA_DIR / "traces.jsonl"
        with open(trace_file, "a") as f:
            for trace in _traces[-10:]:
                f.write(json.dumps(asdict(trace)) + "\n")
    except Exception as e:
        logger.warning("Failed to flush traces: %s", e)


# ===================================================================
# User Feedback
# ===================================================================

def record_feedback(trace_id: str, session_id: str, rating: str, correction: str = ""):
    """Record user feedback (thumbs up/down) for a response.

    Args:
        trace_id: ID of the trace this feedback is for
        session_id: User session ID
        rating: 'up' or 'down'
        correction: Optional user correction text
    """
    feedback_record = {
        "trace_id": trace_id,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rating": rating,
        "correction": correction,
    }
    _feedback.append(feedback_record)
    logger.info("FEEDBACK: trace=%s rating=%s", trace_id, rating)

    # Persist
    try:
        feedback_file = DATA_DIR / "feedback.jsonl"
        with open(feedback_file, "a") as f:
            f.write(json.dumps(feedback_record) + "\n")
    except Exception as e:
        logger.warning("Failed to save feedback: %s", e)


# ===================================================================
# Eval Results Tracking
# ===================================================================

def record_eval_run(results: dict):
    """Record eval suite results for historical tracking."""
    eval_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": results.get("total", 0),
        "passed": results.get("passed", 0),
        "failed": results.get("failed", 0),
        "pass_rate": results.get("pass_rate", 0),
        "categories": results.get("categories", {}),
    }
    _eval_history.append(eval_record)

    try:
        eval_file = DATA_DIR / "eval_history.jsonl"
        with open(eval_file, "a") as f:
            f.write(json.dumps(eval_record) + "\n")
    except Exception as e:
        logger.warning("Failed to save eval results: %s", e)


# ===================================================================
# Observability Dashboard Data
# ===================================================================

def get_dashboard_stats() -> dict:
    """Get aggregated stats for the observability dashboard."""
    if not _traces:
        return {"total_requests": 0, "message": "No traces recorded yet"}

    total = len(_traces)
    errors = sum(1 for t in _traces if t.error)
    avg_latency = sum(t.total_latency_ms for t in _traces) / total
    avg_confidence = sum(t.confidence for t in _traces) / total
    total_tokens = sum(t.total_tokens for t in _traces)
    total_cost = sum(t.estimated_cost_usd for t in _traces)

    # Tool usage breakdown
    tool_counts: dict[str, int] = {}
    for trace in _traces:
        for tool in trace.tools_called:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    # Error category breakdown
    error_categories: dict[str, int] = {}
    for trace in _traces:
        if trace.error_category:
            error_categories[trace.error_category] = error_categories.get(trace.error_category, 0) + 1

    # Escalation count
    escalations = sum(1 for t in _traces if any("ESCALATION" in f for f in t.verification_flags))

    # Feedback summary
    thumbs_up = sum(1 for f in _feedback if f["rating"] == "up")
    thumbs_down = sum(1 for f in _feedback if f["rating"] == "down")

    return {
        "total_requests": total,
        "error_count": errors,
        "error_rate": errors / total if total > 0 else 0,
        "avg_latency_ms": round(avg_latency, 1),
        "avg_confidence": round(avg_confidence, 3),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "tool_usage": tool_counts,
        "error_categories": error_categories,
        "escalation_count": escalations,
        "feedback": {"thumbs_up": thumbs_up, "thumbs_down": thumbs_down},
        "eval_history": _eval_history[-5:],  # Last 5 eval runs
        "recent_errors": [
            {"trace_id": t.trace_id, "error": t.error, "category": t.error_category}
            for t in _traces[-10:] if t.error
        ],
    }
