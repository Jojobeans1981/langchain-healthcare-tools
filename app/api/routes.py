import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.healthcare_agent import chat, chat_stream
from app.agent.memory import clear_session
from app.observability import get_dashboard_stats, record_feedback

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The user's message")
    session_id: str = Field(default="", description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    response: str
    sources: list[str]
    confidence: float
    tools_used: list[str]
    session_id: str
    trace_id: str
    latency_ms: float
    tokens: dict
    verification: dict


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Process a healthcare chat message through the AI agent."""
    session_id = request.session_id or str(uuid.uuid4())

    # Run the agent (includes verification)
    result = await chat(message=request.message, session_id=session_id)

    return ChatResponse(
        response=result["response"],
        sources=result["sources"],
        confidence=result["confidence"],
        tools_used=result["tools_used"],
        session_id=session_id,
        trace_id=result.get("trace_id", ""),
        latency_ms=result.get("latency_ms", 0),
        tokens=result.get("tokens", {"input": 0, "output": 0, "total": 0}),
        verification=result.get("verification", {}),
    )


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Stream a healthcare chat response via Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator():
        full_response = ""
        tools_used = []
        metadata = {}

        async for event in chat_stream(message=request.message, session_id=session_id):
            event_type = event["type"]
            content = event["content"]

            if event_type == "token":
                full_response += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            elif event_type == "tool_start":
                tools_used.append(content)
                yield f"data: {json.dumps({'type': 'tool_start', 'content': content})}\n\n"
            elif event_type == "tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'content': content})}\n\n"
            elif event_type == "done":
                metadata = json.loads(content)
                yield f"data: {json.dumps({'type': 'done', 'content': metadata})}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'content': content})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class SessionRequest(BaseModel):
    session_id: str


@router.post("/clear-session")
async def clear_session_endpoint(request: SessionRequest):
    """Clear conversation history for a session."""
    clear_session(request.session_id)
    return {"status": "ok", "message": f"Session {request.session_id} cleared"}


class FeedbackRequest(BaseModel):
    trace_id: str = Field(..., description="Trace ID of the response being rated")
    session_id: str = Field(default="", description="Session ID")
    rating: str = Field(..., pattern="^(up|down)$", description="'up' or 'down'")
    correction: str = Field(default="", description="Optional correction text")


@router.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """Record user feedback (thumbs up/down) for a response."""
    record_feedback(
        trace_id=request.trace_id,
        session_id=request.session_id,
        rating=request.rating,
        correction=request.correction,
    )
    return {"status": "ok", "message": "Feedback recorded"}


@router.get("/dashboard")
async def dashboard_endpoint():
    """Get observability dashboard stats."""
    return get_dashboard_stats()
