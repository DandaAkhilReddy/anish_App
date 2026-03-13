"""Tests for app.core.config.Settings."""
from __future__ import annotations

import pytest

from app.core.config import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED = {
    "azure_openai_endpoint": "https://example.openai.azure.com/",
    "azure_openai_api_key": "test-key-abc123",
}


def make_settings(**overrides: str) -> Settings:
    """Construct a Settings instance with required fields pre-filled.

    All keyword args are forwarded to Settings, overriding the defaults in
    ``_REQUIRED``.  Passing ``_env_file=None`` suppresses .env file loading so
    tests are hermetic.
    """
    return Settings(**{**_REQUIRED, **overrides}, _env_file=None)


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


class TestRequiredFields:
    def test_loads_endpoint_from_kwargs(self) -> None:
        s = make_settings(azure_openai_endpoint="https://my-endpoint.azure.com/")
        assert s.azure_openai_endpoint == "https://my-endpoint.azure.com/"

    def test_loads_api_key_from_kwargs(self) -> None:
        s = make_settings(azure_openai_api_key="secret-key-xyz")
        assert s.azure_openai_api_key == "secret-key-xyz"

    def test_missing_endpoint_raises(self) -> None:
        with pytest.raises(Exception):
            Settings(azure_openai_api_key="key", _env_file=None)

    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(Exception):
            Settings(azure_openai_endpoint="https://example.com/", _env_file=None)


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_deployment_is_gpt41(self) -> None:
        s = make_settings()
        assert s.azure_openai_deployment == "gpt-4.1"

    def test_default_api_version(self) -> None:
        s = make_settings()
        assert s.azure_openai_api_version == "2024-05-01-preview"

    def test_default_environment_is_development(self) -> None:
        s = make_settings()
        assert s.environment == "development"

    def test_default_log_level_is_debug(self) -> None:
        s = make_settings()
        assert s.log_level == "DEBUG"

    def test_default_cors_origins_is_localhost(self) -> None:
        s = make_settings()
        assert s.cors_origins == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Field overrides
# ---------------------------------------------------------------------------


class TestFieldOverrides:
    def test_deployment_override(self) -> None:
        s = make_settings(azure_openai_deployment="gpt-4o")
        assert s.azure_openai_deployment == "gpt-4o"

    def test_api_version_override(self) -> None:
        s = make_settings(azure_openai_api_version="2025-01-01-preview")
        assert s.azure_openai_api_version == "2025-01-01-preview"

    def test_environment_override(self) -> None:
        s = make_settings(environment="staging")
        assert s.environment == "staging"

    def test_log_level_override(self) -> None:
        s = make_settings(log_level="WARNING")
        assert s.log_level == "WARNING"


# ---------------------------------------------------------------------------
# is_production property
# ---------------------------------------------------------------------------


class TestIsProduction:
    def test_returns_true_for_production(self) -> None:
        s = make_settings(environment="production")
        assert s.is_production is True

    def test_returns_false_for_development(self) -> None:
        s = make_settings(environment="development")
        assert s.is_production is False

    def test_returns_false_for_staging(self) -> None:
        s = make_settings(environment="staging")
        assert s.is_production is False

    def test_returns_false_for_empty_string(self) -> None:
        s = make_settings(environment="")
        assert s.is_production is False

    def test_case_sensitive_production_check(self) -> None:
        # "Production" with capital P must NOT be treated as production
        s = make_settings(environment="Production")
        assert s.is_production is False


# ---------------------------------------------------------------------------
# cors_origin_list property
# ---------------------------------------------------------------------------


class TestCorsOriginList:
    def test_single_origin_returns_one_element_list(self) -> None:
        s = make_settings(cors_origins="http://localhost:5173")
        assert s.cors_origin_list == ["http://localhost:5173"]

    def test_multiple_comma_separated_origins(self) -> None:
        s = make_settings(
            cors_origins="http://localhost:5173,https://example.com,https://api.example.com"
        )
        assert s.cors_origin_list == [
            "http://localhost:5173",
            "https://example.com",
            "https://api.example.com",
        ]

    def test_trims_leading_whitespace(self) -> None:
        s = make_settings(cors_origins="http://a.com, http://b.com")
        assert s.cors_origin_list == ["http://a.com", "http://b.com"]

    def test_trims_trailing_whitespace(self) -> None:
        s = make_settings(cors_origins="http://a.com ,http://b.com")
        assert s.cors_origin_list == ["http://a.com", "http://b.com"]

    def test_trims_whitespace_on_all_sides(self) -> None:
        s = make_settings(cors_origins="  http://a.com  ,  http://b.com  ")
        assert s.cors_origin_list == ["http://a.com", "http://b.com"]

    def test_single_origin_no_comma_returns_list_of_one(self) -> None:
        s = make_settings(cors_origins="https://prod.example.com")
        result = s.cors_origin_list
        assert isinstance(result, list)
        assert len(result) == 1

    def test_two_origins_returns_list_of_two(self) -> None:
        s = make_settings(cors_origins="https://a.com,https://b.com")
        assert len(s.cors_origin_list) == 2

    def test_returns_list_type(self) -> None:
        s = make_settings()
        assert isinstance(s.cors_origin_list, list)
