from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Provider: "groq" or "gemini"
    llm_provider: str = "groq"
    groq_api_key: str = ""
    google_api_key: str = ""
    model_name: str = "llama-3.3-70b-versatile"
    model_temperature: float = 0.1
    model_max_tokens: int = 2048

    # OpenEMR REST API connection
    openemr_base_url: str = "https://localhost:9300"
    openemr_user: str = "admin"
    openemr_pass: str = "pass"
    openemr_enabled: bool = False
    openemr_verify_ssl: bool = False  # False for dev (self-signed certs)
    openemr_redirect_uri: str = "http://localhost:8000/callback"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "agentforge-healthcare"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"groq", "gemini"}
        if v.lower() not in allowed:
            raise ValueError(f"llm_provider must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("model_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"model_temperature must be between 0.0 and 2.0, got {v}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return v.upper()


settings = Settings()
