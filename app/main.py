import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="AgentForge Healthcare AI",
    description="Production-ready healthcare AI agent powered by LangGraph and Groq/Llama 3.3",
    version="0.1.0",
)

# CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AgentForge Healthcare AI",
        "version": "0.1.0",
        "model": settings.model_name,
    }


@app.get("/debug")
async def debug_info():
    """Diagnostic endpoint to verify configuration and dependencies."""
    import importlib

    checks = {}

    # Check API key presence
    checks["llm_provider"] = settings.llm_provider
    checks["groq_api_key_set"] = bool(settings.groq_api_key)
    checks["google_api_key_set"] = bool(settings.google_api_key)
    checks["langsmith_tracing"] = settings.langchain_tracing_v2
    checks["langsmith_key_set"] = bool(settings.langchain_api_key)
    checks["model_name"] = settings.model_name

    # Check package versions
    for pkg in ["langchain_core", "langgraph", "langchain_groq", "langchain_google_genai", "httpx"]:
        try:
            mod = importlib.import_module(pkg)
            checks[f"{pkg}_version"] = getattr(mod, "__version__", "installed")
        except ImportError:
            checks[f"{pkg}_version"] = "NOT INSTALLED"

    # Try creating the agent
    try:
        from app.agent.healthcare_agent import get_agent
        agent = get_agent()
        checks["agent_creation"] = "OK"
    except Exception as e:
        checks["agent_creation"] = f"FAILED: {type(e).__name__}: {e}"

    return checks
