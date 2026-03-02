import logging
import os
import time
import uuid

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
# Use the new non-deprecated import (LangGraph v1.0+)
try:
    from langchain.agents import create_agent as _create_react_agent
    _USE_SYSTEM_PROMPT_PARAM = True
except ImportError:
    from langgraph.prebuilt import create_react_agent as _create_react_agent
    _USE_SYSTEM_PROMPT_PARAM = False

from app.agent.memory import get_session_history, trim_history
from app.agent.prompts import HEALTHCARE_AGENT_SYSTEM_PROMPT
from app.config import settings
from app.observability import RequestTracer
from app.verification.verifier import verify_response, post_process_response
from app.verification.llm_judge import judge_response, apply_judge_to_verification
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
logger.info("Fallback readiness: google_api_key=%s, groq_api_key=%s", bool(settings.google_api_key), bool(settings.groq_api_key))

# Healthcare tools (9 tools: 6 core + 3 drug recall/watchlist)
# Enable handle_tool_error so the agent can recover from individual tool failures
# instead of crashing the entire request.
_ALL_TOOLS = [
    drug_interaction_check, symptom_lookup, provider_search,
    appointment_availability, insurance_coverage_check, medication_lookup,
    manage_watchlist, check_drug_recalls, scan_watchlist_recalls,
]
for _t in _ALL_TOOLS:
    _t.handle_tool_error = True
TOOLS = _ALL_TOOLS


_FALLBACK_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.5-flash",
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

    Catches rate limits, tool-calling incompatibility, model availability errors,
    and malformed tool call errors (failed_generation from Groq).
    """
    error_str = str(e).lower()
    return (
        _is_rate_limit_error(e)
        or "tool calling is not supported" in error_str
        or "does not support tools" in error_str
        or "function calling" in error_str and "not supported" in error_str
        or "model not found" in error_str
        or "model_not_found" in error_str
        or "failed_generation" in error_str
        or "failed to call" in error_str
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
    llm = _create_llm(provider, model)

    if _USE_SYSTEM_PROMPT_PARAM:
        # New API (langchain.agents.create_agent): accepts system_prompt directly
        agent = _create_react_agent(
            model=llm,
            tools=TOOLS,
            system_prompt=HEALTHCARE_AGENT_SYSTEM_PROMPT,
        )
        logger.info("Created agent via langchain.agents.create_agent (system_prompt)")
        return agent

    # Legacy API (langgraph.prebuilt.create_react_agent): needs ChatPromptTemplate
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages([
        ("system", HEALTHCARE_AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    for param_name in ("state_modifier", "prompt"):
        try:
            agent = _create_react_agent(
                model=llm,
                tools=TOOLS,
                **{param_name: prompt},
            )
            logger.info("Created agent using legacy '%s' parameter", param_name)
            return agent
        except TypeError:
            continue

    logger.warning("Could not inject system prompt — agent will run without instructions")
    return _create_react_agent(model=llm, tools=TOOLS)


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
    _start_time = time.monotonic()

    # Start observability trace
    tracer = RequestTracer(query=message, session_id=session_id, trace_id=trace_id)
    tracer.start()

    config = {"configurable": {"thread_id": f"{session_id}-{trace_id}"}}

    history = get_session_history(session_id)
    # Build conversation context: prior turns + current question
    prior_messages = list(history.messages)
    all_messages = prior_messages + [HumanMessage(content=message)]
    num_input_messages = len(all_messages)
    history.add_user_message(message)

    async def _invoke_agent(agent_instance, override_config=None):
        """Invoke agent and extract response data."""
        use_config = override_config if override_config is not None else config
        tracer.start_llm()
        result = await agent_instance.ainvoke(
            {"messages": all_messages},
            config=use_config,
        )
        tracer.end_llm()

        # Only process messages generated by THIS turn (skip history).
        # Real LangGraph includes input messages in results; mocks may not.
        messages = result.get("messages", [])
        if len(messages) > num_input_messages:
            new_messages = messages[num_input_messages:]
        else:
            new_messages = messages
        response_text = ""
        tools_used = []
        tool_outputs = []
        sources = []
        input_tokens = 0
        output_tokens = 0

        for msg in new_messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tools_used.append(tc["name"])
                    tracer.end_tool(tc["name"])
            if msg.type == "tool" and msg.content:
                # Collect tool output from ToolMessages
                tool_outputs.append(msg.content)
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
            for msg in reversed(new_messages):
                if msg.type == "ai" and msg.content:
                    response_text = msg.content
                    break

        # If LLM response is too short but tools returned data, prepend tool output
        if tool_outputs and len(response_text) < 300:
            tool_data = "\n\n".join(
                t.replace("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]\n", "") for t in tool_outputs
            )
            response_text = tool_data + "\n\n" + response_text

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

        # Run LLM-as-judge semantic verification (additive — only raises flags)
        try:
            judge_result = await judge_response(response_text, unique_tools, message)
            apply_judge_to_verification(judge_result, verification)
        except Exception as judge_err:
            logger.debug("LLM judge skipped: %s", judge_err)

        # Confidence-based fallback: retry with fallback provider if confidence < 0.7
        # Time guard: skip fallback if already past 25s to avoid eval/request timeouts
        _elapsed = time.monotonic() - _start_time
        if verification.confidence < 0.7 and not verification.needs_escalation and _elapsed < 25:
            fallback = _get_fallback_provider()
            if fallback:
                logger.warning(
                    "Low confidence (%.2f), retrying with fallback provider %s",
                    verification.confidence, fallback,
                )
                try:
                    fallback_model = _FALLBACK_MODELS.get(fallback)
                    fallback_agent = create_agent(provider=fallback, model=fallback_model)
                    quality_config = {"configurable": {"thread_id": f"{session_id}-quality-{trace_id}"}}
                    fb_response, fb_tools, fb_sources, fb_in, fb_out = await _invoke_agent(fallback_agent, override_config=quality_config)
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
    # Build conversation context: prior turns + current question
    prior_messages = list(history.messages)
    all_messages = prior_messages + [HumanMessage(content=message)]
    history.add_user_message(message)

    full_response = ""
    tools_used = []
    tool_outputs = []
    input_tokens = 0
    output_tokens = 0

    async def _stream_agent(agent_instance):
        """Stream from an agent instance, yielding events.

        In a ReAct loop the LLM is called multiple times (reason → tool → synthesize).
        We only stream tokens from the *final* LLM turn to avoid duplicating tool data
        that appears in intermediate reasoning steps.  We detect the final turn by
        tracking pending tool calls: once all tools have finished executing, the next
        LLM tokens are the final response.
        """
        nonlocal full_response, tools_used, tool_outputs, input_tokens, output_tokens
        pending_tools = 0          # tracks tools started but not yet finished
        tools_ever_called = False  # whether any tool was invoked at all
        buffered_tokens = ""       # tokens from the current LLM turn (may be intermediate)

        async for event in agent_instance.astream_events(
            {"messages": all_messages},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    if not getattr(chunk, "tool_calls", None) and not getattr(chunk, "tool_call_chunks", None):
                        # Only stream to user if we're in the final turn
                        # (no pending tools AND tools have already completed)
                        is_final_turn = tools_ever_called and pending_tools == 0
                        if not tools_ever_called or is_final_turn:
                            full_response += chunk.content
                            yield {"type": "token", "content": chunk.content}
                        else:
                            buffered_tokens += chunk.content

            elif kind == "on_chat_model_end":
                # Extract token usage from the completed model response
                output = event.get("data", {}).get("output")
                if output and hasattr(output, "usage_metadata") and output.usage_metadata:
                    usage = output.usage_metadata
                    if isinstance(usage, dict):
                        input_tokens += usage.get("input_tokens", 0)
                        output_tokens += usage.get("output_tokens", 0)
                    else:
                        input_tokens += getattr(usage, "input_tokens", 0) or 0
                        output_tokens += getattr(usage, "output_tokens", 0) or 0
                # Discard buffered intermediate tokens (tool-calling reasoning)
                buffered_tokens = ""

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tools_used.append(tool_name)
                tools_ever_called = True
                pending_tools += 1
                yield {"type": "tool_start", "content": tool_name}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                tracer.end_tool(tool_name)
                pending_tools = max(pending_tools - 1, 0)
                # Extract tool output for the reinvoke safety net
                tool_output = ""
                data = event.get("data", {})
                for key in ("output", "result", "content"):
                    raw = data.get(key, "")
                    if raw:
                        if hasattr(raw, "content"):
                            tool_output = raw.content
                        elif isinstance(raw, str):
                            tool_output = raw
                        elif isinstance(raw, dict):
                            tool_output = raw.get("content", str(raw))
                        else:
                            tool_output = str(raw)
                        if tool_output:
                            break
                if tool_output:
                    clean = tool_output.replace("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]\n", "")
                    tool_outputs.append(clean)
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

        # If tools were called but stream didn't capture outputs AND response is short,
        # call the tools directly to get their data
        if tools_used and not tool_outputs and len(full_response.strip()) < 300:
            logger.warning("Stream produced short response (%d chars) with %d tools. Calling tools directly.", len(full_response.strip()), len(tools_used))
            # Use non-streaming ainvoke to get tool messages
            try:
                reinvoke_result = await agent.ainvoke(
                    {"messages": all_messages},
                    config={"configurable": {"thread_id": f"{session_id}-{trace_id}-recover"}},
                )
                for msg in reinvoke_result.get("messages", []):
                    if msg.type == "tool" and msg.content:
                        clean = msg.content.replace("[INCLUDE THIS SOURCE LINE IN YOUR RESPONSE]\n", "")
                        tool_outputs.append(clean)
                if tool_outputs:
                    injected = "\n\n".join(tool_outputs)
                    full_response = injected + "\n\n" + full_response
                    logger.info("Recovered %d tool output(s) via non-streaming reinvoke", len(tool_outputs))
            except Exception as recover_err:
                logger.error("Tool output recovery failed: %s", recover_err)

        # Extract sources
        sources = []
        if "Source:" in full_response:
            for line in full_response.split("\n"):
                if line.strip().startswith("Source:"):
                    sources.append(line.strip().replace("Source: ", ""))

        # Run verification on complete response
        unique_tools = list(set(tools_used))
        verification = verify_response(full_response, unique_tools, message)

        # Run LLM-as-judge semantic verification (additive — only raises flags)
        try:
            judge_result = await judge_response(full_response, unique_tools, message)
            apply_judge_to_verification(judge_result, verification)
        except Exception as judge_err:
            logger.debug("LLM judge skipped in stream: %s", judge_err)

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
        error_str = str(e).lower()
        # Detect tool call failures (malformed function calls from LLM)
        if "failed to call" in error_str or "failed_generation" in error_str or "tool_call" in error_str:
            yield {
                "type": "clarify",
                "content": (
                    "I wasn't sure how to process that request. Could you try rephrasing your question? "
                    "Here are some things I can help with:\n\n"
                    "- **Drug interactions:** \"Check interaction between warfarin and aspirin\"\n"
                    "- **Symptoms:** \"I have a persistent headache with fever\"\n"
                    "- **Medications:** \"What are the side effects of metformin?\"\n"
                    "- **Providers:** \"Find me a cardiologist\"\n"
                    "- **Appointments:** \"Any dermatology openings this week?\"\n"
                    "- **Insurance:** \"Does Blue Cross PPO cover an MRI?\"\n"
                    "- **FDA Recalls:** \"Check if lisinopril has been recalled\"\n"
                    "- **Watchlist:** \"Add metformin to patient P001's watchlist\"\n\n"
                    "**Disclaimer:** This information is for educational purposes only and does not "
                    "constitute medical advice. Always consult a qualified healthcare professional "
                    "for personalized medical guidance."
                ),
            }
        else:
            yield {"type": "error", "content": str(e)}
