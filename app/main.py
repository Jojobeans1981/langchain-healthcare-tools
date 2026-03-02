import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.watchlist_routes import watchlist_router
from app.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the LLM agent on startup to eliminate cold-start latency."""
    try:
        from app.agent.healthcare_agent import get_agent
        agent = get_agent()
        logger.info("Agent warmed up successfully: %s", type(agent).__name__)
    except Exception as e:
        logger.warning("Agent warmup failed (will retry on first request): %s", e)
    yield


app = FastAPI(
    title="AgentForge Healthcare AI",
    description="Production-ready healthcare AI agent powered by LangGraph and Groq/Llama 3.3",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration (Phase 6B) — restrict origins based on environment
_default_origins = [
    "http://localhost:8501",   # Streamlit default
    "http://127.0.0.1:8501",
    "http://localhost:8000",   # FastAPI (Swagger UI)
    "http://127.0.0.1:8000",
]
if settings.app_env == "production":
    _allowed_origins = [getattr(settings, "allowed_origin", "https://agentforge-0p0k.onrender.com")]
else:
    _allowed_origins = _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Rate limiting (Phase 6A) — simple in-memory per-IP rate limiter
_request_counts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 60   # requests per minute
_RATE_WINDOW = 60   # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _request_counts[client_ip] = [t for t in _request_counts[client_ip] if now - t < _RATE_WINDOW]
    if len(_request_counts[client_ip]) >= _RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please retry in 1 minute."},
        )
    _request_counts[client_ip].append(now)
    return await call_next(request)


# Global exception handler — return structured JSON, never leak stack traces (Phase 6D)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
        # Never include exc details in response body
    )


# Include API routes
app.include_router(router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")


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
