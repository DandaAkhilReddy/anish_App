"""Application configuration via pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str = "gpt-4.1"
    azure_openai_api_version: str = "2024-05-01-preview"

    # Financial Modeling Prep
    fmp_api_key: str = ""

    # Azure AI Foundry SharePoint Agent
    sharepoint_agent_endpoint: str = ""

    # App
    environment: str = "development"
    log_level: str = "DEBUG"
    cors_origins: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        """Split comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
