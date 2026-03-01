from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from this file to find the nearest .env file
_here = Path(__file__).parent
_search_dirs = [_here, _here.parent, _here.parent.parent, _here.parent.parent.parent]
_env_file = next((p / ".env" for p in _search_dirs if (p / ".env").exists()), Path(".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: str = "development"

    # Logging
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://genhealth:genhealth_dev@localhost:5433/genhealth"

    # Anthropic / LLM
    anthropic_api_key: str = ""
    llm_max_file_size_mb: int = 10
    llm_max_pages: int = 20
    llm_max_tokens: int = 256
    llm_request_timeout_seconds: int = 30
    llm_max_retries: int = 2
    llm_rate_limit_per_minute: int = 10


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Use dependency injection in FastAPI routes."""
    return Settings()
