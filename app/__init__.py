"""langchain-healthcare-tools — Production healthcare AI tools for LangChain/LangGraph.

Quick start:
    from app.tools import ALL_TOOLS
    from app.agent.prompts import HEALTHCARE_AGENT_SYSTEM_PROMPT
    from app.verification.verifier import verify_response, post_process_response

    # Build a verified healthcare agent in 5 lines:
    from langgraph.prebuilt import create_react_agent
    agent = create_react_agent(llm, ALL_TOOLS, prompt=HEALTHCARE_AGENT_SYSTEM_PROMPT)
"""

from app import tools  # noqa: F401
from app.agent.prompts import HEALTHCARE_AGENT_SYSTEM_PROMPT  # noqa: F401
from app.verification.verifier import (  # noqa: F401
    VerificationResult,
    post_process_response,
    verify_response,
)

__all__ = [
    "tools",
    "HEALTHCARE_AGENT_SYSTEM_PROMPT",
    "verify_response",
    "post_process_response",
    "VerificationResult",
]
