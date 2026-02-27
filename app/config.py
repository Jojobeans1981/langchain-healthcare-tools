from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Provider: "groq" or "gemini"
    llm_provider: str = "groq"
    groq_api_key: str = ""
    google_api_key: str = ""
    model_name: str = "llama-3.3-70b-versatile"
    model_temperature: float = 0.1
    model_max_tokens: int = 1024

    # OpenEMR REST API connection
    openemr_base_url: str = "https://localhost:9300"
    openemr_user: str = "admin"
    openemr_pass: str = "pass"
    openemr_enabled: bool = False

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "agentforge-healthcare"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
