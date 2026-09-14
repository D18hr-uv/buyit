"""Central configuration, loaded from environment (.env)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    llm_provider: str = "openai"          # "openai" | "stub"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Data layer. Defaults to a local SQLite file so tests / eval run with no infra.
    database_url: str = "sqlite:///./buyit.db"
    redis_url: str = "redis://localhost:6379/0"

    # Guardrails
    max_agent_iters: int = 3
    approval_value_threshold: float = 50000.0
    min_supplier_reliability: float = 0.7

    @property
    def use_real_llm(self) -> bool:
        """Only use the real provider when a key is present and stub not forced."""
        return self.llm_provider == "openai" and bool(self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
