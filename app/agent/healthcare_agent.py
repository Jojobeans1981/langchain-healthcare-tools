import logging
import os
import uuid

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.agent.memory import get_session_history, trim_history
from app.agent.prompts import HEALTHCARE_AGENT_SYSTEM_PROMPT
from app.config import settings
from app.observability import RequestTracer
from app.verification.verifier import verify_response, post_process_response
from app.tools.appointment_availability import appointment_availability
from app.tools.drug_interaction import drug_interaction_check
from app.tools.insurance_coverage import insurance_coverage_check
from app.tools.provider_search import provider_search
from app.tools.drug_recall import check_drug_recalls, manage_watchlist, scan_watchlist_recalls
from app.tools.medication_lookup import medication_lookup
from app.tools.symptom_lookup import symptom_lookup

logger = logging.getLogger(__name__)

# Export LangSmith env vars so LangChain SDK picks them up
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    logger.info("LangSmith tracing enabled for project: %s", settings.langchain_project)
elif settings.langchain_tracing_v2:
    logger.warning("LangSmith tracing requested but LANGCHAIN_API_KEY is not set")

# Healthcare tools (9 tools: 6 core + 3 drug recall/watchlist)
TOOLS = [
    drug_interaction_check, symptom_lookup, provider_search,
    appointment_availability, insurance_coverage_check, medication_lookup,
    manage_watchlist, check_drug_recalls, scan_watchlist_recalls,
]


_FALLBACK_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-1.5-flash",
}


def _create_llm(provider: str = None, model: str = None) -> BaseChatModel:
    """Create an LLM instance for the given provider."""
    provider = (provider or settings.llm_provider).lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        if settings.groq_api_key:
            os.environ["GROQ_API_KEY"] = settings.groq_api_key
        return ChatGroq(
            model=model or settings.model_name,
            temperature=settings.model_temperature,
            max_tokens=settings.model_max_tokens,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        if settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = settings.google_api_key
        return ChatGoogleGenerativeAI(
            model=model or settings.model_name,
            temperature=settings.model_temperature,
            max_output_tokens=settings.model_max_tokens,
        )


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a rate limit error."""
    error_str = str(e).lower()
    return "rate_limit" in error_str or "429" in error_str or "resource_exhausted" in error_str


def _should_try_fallback(e: Exception) -> bool:
    """Check if the error warrants trying a fallback provider.

    Catches rate limits, tool-calling incompatibility, and model availability errors.
    """
    error_str = str(e).lower()
    return (
        _is_rate_limit_error(e)
        or "tool calling is not supported" in error_str
        or "does not support tools" in error_str
        or "function calling" in error_str and "not supported" in error_str
        or "model not found" in error_str
        or "model_not_found" in error_str
    )


def _get_fallback_provider() -> str | None:
    """Get the fallback provider name if credentials are available.

    Fallback priority: Gemini > Groq.
    """
    primary = settings.llm_provider.lower()
    if primary != "gemini" and settings.google_api_key:
        return "gemini"
    if primary != "groq" and settings.groq_api_key:
        return "groq"
    return None


def create_agent(provider: str = None, model: str = None):
    """Create the healthcare ReAct agent with tools and memory."""
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    llm = _create_llm(provider, model)

    # Build a proper ChatPromptTemplate for the system prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", HEALTHCARE_AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Try each parameter name LangGraph has used across versions
    for param_name in ("state_modifier", "prompt"):
        try:
            agent = create_react_agent(
                model=llm,
                tools=TOOLS,
                **{param_name: prompt},
            )
            logger.info("Created agent using '%s' parameter", param_name)
            return agent
        except TypeError:
            continue

    # Last resort: no system prompt parameter (agent will work but without instructions)
    logger.warning("Could not inject system prompt — agent will run without instructions")
    return create_react_agent(model=llm, tools=TOOLS)


_agent = None
_agent_provider = None


def get_agent():
    """Get or create the agent instance. Recreates if provider changed."""
    global _agent, _agent_provider
    current_provider = settings.llm_provider.lower()
    if _agent is None or _agent_provider != current_provider:
        logger.info("Creating agent with provider: %s, model: %s", current_provider, settings.model_name)
        _agent = create_agent()
        _agent_provider = current_provider
    return _agent


async def chat(message: str, session_id: str = "default") -> dict:
    """Process a chat message through the healthcare agent with full observability."""
    trace_id = str(uuid.uuid4())[:8]

    # Start observability trace
    tracer = RequestTracer(query=message, session_id=session_id, trace_id=trace_id)
    tracer.start()

    config = {"configurable": {"thread_id": f"{session_id}-{trace_id}"}}

    history = get_session_history(session_id)
    history.add_user_message(message)

    async def _invoke_agent(agent_instance):
        """Invoke agent and extract response data."""
        tracer.start_llm()
        result = await agent_instance.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        tracer.end_llm()

        messages = result.get("messages", [])
        response_text = ""
        tools_used = []
        sources = []
        input_tokens = 0
        output_tokens = 0

        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_used.append(tc["name"])
                    tracer.end_tool(tc["name"])
            if msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                response_text = msg.content
            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                usage = msg.usage_metadata
                input_tokens += getattr(usage, "input_tokens", 0) or 0
                output_tokens += getattr(usage, "output_tokens", 0) or 0
            elif hasattr(msg, "response_metadata"):
                meta = msg.response_metadata or {}
                if "usage_metadata" in meta:
                    usage = meta["usage_metadata"]
                    input_tokens += usage.get("prompt_token_count", 0)
                    output_tokens += usage.get("candidates_token_count", 0)

        if not response_text:
            for msg in reversed(messages):
                if msg.type == "ai" and msg.content:
                    response_text = msg.content
                    break

        return response_text, tools_used, sources, input_tokens, output_tokens

    try:
        agent = get_agent()
        logger.info("Invoking agent with provider=%s model=%s", settings.llm_provider, settings.model_name)

        try:
            response_text, tools_used, sources, input_tokens, output_tokens = await _invoke_agent(agent)
        except Exception as e:
            if not _should_try_fallback(e):
                raise
            # Primary failed — try fallback provider
            fallback = _get_fallback_provider()
            if not fallback:
                raise
            logger.warning("Primary provider %s failed (%s), falling back to %s", settings.llm_provider, e, fallback)
            try:
                fallback_model = _FALLBACK_MODELS.get(fallback)
                fallback_agent = create_agent(provider=fallback, model=fallback_model)
                response_text, tools_used, sources, input_tokens, output_tokens = await _invoke_agent(fallback_agent)
            except Exception as fallback_err:
                logger.error("Fallback provider also failed: %s", fallback_err)
                raise e  # Re-raise the original error

        # Extract sources
        if "Source:" in response_text:
            for line in response_text.split("\n"):
                if line.strip().startswith("Source:"):
                    sources.append(line.strip().replace("Source: ", ""))

        # Run verification
        unique_tools = list(set(tools_used))
        verification = verify_response(response_text, unique_tools, message)

        # Confidence-based fallback: retry with fallback provider if confidence < 0.7
        if verification.confidence < 0.7 and not verification.needs_escalation:
            fallback = _get_fallback_provider()
            if fallback:
                logger.warning(
                    "Low confidence (%.2f), retrying with fallback provider %s",
                    verification.confidence, fallback,
                )
                try:
                    fallback_model = _FALLBACK_MODELS.get(fallback)
                    fallback_agent = create_agent(provider=fallback, model=fallback_model)
                    fb_response, fb_tools, fb_sources, fb_in, fb_out = await _invoke_agent(fallback_agent)
                    fb_unique_tools = list(set(fb_tools))
                    fb_verification = verify_response(fb_response, fb_unique_tools, message)
                    # Only use fallback if it's actually better
                    if fb_verification.confidence > verification.confidence:
                        response_text = fb_response
                        unique_tools = fb_unique_tools
                        verification = fb_verification
                        input_tokens = fb_in
                        output_tokens = fb_out
                        sources = fb_sources
                        logger.info("Fallback improved confidence: %.2f -> %.2f", verification.confidence, fb_verification.confidence)
                except Exception as e:
                    logger.warning("Confidence fallback failed: %s", e)

        processed_response = post_process_response(response_text, verification)

        # Record observability data
        tracer.set_tokens(input_tokens, output_tokens)
        tracer.set_response(processed_response, confidence=verification.confidence, sources=sources)

        # Store in history
        history.add_ai_message(processed_response)
        trim_history(session_id)

        trace_record = tracer.finish()

        return {
            "response": processed_response,
            "sources": sources,
            "confidence": verification.confidence,
            "tools_used": unique_tools,
            "session_id": session_id,
            "trace_id": trace_id,
            "latency_ms": trace_record.total_latency_ms,
            "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
            "verification": verification.to_dict(),
        }

    except Exception as e:
        logger.error("Agent error: %s", e, exc_info=True)
        tracer.set_error(str(e), category=type(e).__name__)
        tracer.finish()

        error_detail = f"{type(e).__name__}: {e}"
        error_msg = (
            "I apologize, but I encountered an error processing your request. "
            "Please try rephrasing your question or try again later.\n\n"
            "If you're experiencing a medical emergency, please call 911 immediately."
        )
        history.add_ai_message(error_msg)
        return {
            "response": error_msg,
            "sources": [],
            "confidence": 0.0,
            "tools_used": [],
            "session_id": session_id,
            "trace_id": trace_id,
            "error": error_detail,
        }


async def chat_stream(message: str, session_id: str = "default"):
    """Stream agent response tokens. Yields dicts with 'type' and 'content' keys.

    Event types:
    - 'token': A chunk of the response text
    - 'tool_start': A tool is being called (content = tool name)
    - 'tool_end': A tool finished (content = tool name)
    - 'done': Stream complete (content = full metadata dict as JSON)
    - 'error': An error occurred (content = error message)
    """
    import json as _json

    trace_id = str(uuid.uuid4())[:8]
    tracer = RequestTracer(query=message, session_id=session_id, trace_id=trace_id)
    tracer.start()

    config = {"configurable": {"thread_id": f"{session_id}-{trace_id}"}}
    history = get_session_history(session_id)
    history.add_user_message(message)

    full_response = ""
    tools_used = []
    input_tokens = 0
    output_tokens = 0

    async def _stream_agent(agent_instance):
        """Stream from an agent instance, yielding events."""
        nonlocal full_response, tools_used, input_tokens, output_tokens
        async for event in agent_instance.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    if not getattr(chunk, "tool_calls", None) and not getattr(chunk, "tool_call_chunks", None):
                        full_response += chunk.content
                        yield {"type": "token", "content": chunk.content}

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tools_used.append(tool_name)
                yield {"type": "tool_start", "content": tool_name}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                tracer.end_tool(tool_name)
                yield {"type": "tool_end", "content": tool_name}

    try:
        agent = get_agent()
        tracer.start_llm()
        logger.info("Streaming agent with provider=%s model=%s", settings.llm_provider, settings.model_name)

        try:
            async for event in _stream_agent(agent):
                yield event
        except Exception as e:
            if not _should_try_fallback(e):
                raise
            fallback = _get_fallback_provider()
            if not fallback:
                raise
            logger.warning("Primary provider %s failed (%s), falling back to %s for stream", settings.llm_provider, e, fallback)
            try:
                full_response = ""
                tools_used = []
                fallback_model = _FALLBACK_MODELS.get(fallback)
                fallback_agent = create_agent(provider=fallback, model=fallback_model)
                async for event in _stream_agent(fallback_agent):
                    yield event
            except Exception as fallback_err:
                logger.error("Fallback provider also failed: %s", fallback_err)
                raise e  # Re-raise the original rate limit error

        tracer.end_llm()

        # Extract sources
        sources = []
        if "Source:" in full_response:
            for line in full_response.split("\n"):
                if line.strip().startswith("Source:"):
                    sources.append(line.strip().replace("Source: ", ""))

        # Run verification on complete response
        unique_tools = list(set(tools_used))
        verification = verify_response(full_response, unique_tools, message)
        processed_response = post_process_response(full_response, verification)

        tracer.set_tokens(input_tokens, output_tokens)
        tracer.set_response(processed_response, confidence=verification.confidence, sources=sources)
        history.add_ai_message(full_response)
        trim_history(session_id)
        trace_record = tracer.finish()

        yield {
            "type": "done",
            "content": _json.dumps({
                "response": processed_response,
                "sources": sources,
                "confidence": verification.confidence,
                "tools_used": unique_tools,
                "trace_id": trace_id,
                "session_id": session_id,
                "latency_ms": trace_record.total_latency_ms,
                "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
                "verification": verification.to_dict(),
            }),
        }

    except Exception as e:
        logger.error("Agent stream error: %s", e, exc_info=True)
        tracer.set_error(str(e), category=type(e).__name__)
        tracer.finish()
        yield {"type": "error", "content": str(e)}
