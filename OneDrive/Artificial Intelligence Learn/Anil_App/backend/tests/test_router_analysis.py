"""Tests for app.routers.analysis — POST /api/analyze/{ticker}."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import AIAnalysisError, ExternalAPIError, StockNotFoundError
from app.models.analysis import (
    PriceForecast,
    PricePredictions,
    RiskAssessment,
    StockAnalysisResponse,
    TechnicalSnapshot,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_FIXED_TIMESTAMP = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)

_MOCK_RESPONSE = StockAnalysisResponse(
    ticker="AAPL",
    company_name="Apple Inc.",
    current_price=227.50,
    previous_close=224.72,
    open=225.10,
    day_high=229.00,
    day_low=224.50,
    volume=58_000_000,
    market_cap="3.5T",
    pe_ratio=35.2,
    eps=6.46,
    week_52_high=237.23,
    week_52_low=164.08,
    dividend_yield=0.0044,
    technical=TechnicalSnapshot(
        sma_20=221.30,
        sma_50=215.80,
        rsi_14=58.4,
        signal="buy",
    ),
    news=[],
    quarterly_earnings=[],
    recommendation="buy",
    confidence_score=0.78,
    summary="Apple remains a quality compounder with strong services growth.",
    bull_case="Services segment continues to expand margins substantially.",
    bear_case="Hardware saturation in China could pressure top-line growth.",
    risk_assessment=RiskAssessment(
        overall_risk="medium",
        risk_factors=["China exposure", "antitrust scrutiny"],
        risk_score=0.40,
    ),
    price_predictions=PricePredictions(
        one_week=PriceForecast(low=222.0, mid=228.0, high=234.0, confidence=0.70),
        one_month=PriceForecast(low=218.0, mid=235.0, high=248.0, confidence=0.65),
        three_months=PriceForecast(low=210.0, mid=245.0, high=265.0, confidence=0.55),
    ),
    analysis_timestamp=_FIXED_TIMESTAMP,
)

_PATCH_TARGET = "app.routers.analysis._ai_service.analyze"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestAnalyzeStockSuccess:
    """POST /api/analyze/{ticker} — successful AI analysis."""

    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient) -> None:
        """A valid ticker returns HTTP 200."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_ticker(self, client: AsyncClient) -> None:
        """Response body includes the correct ticker field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_response_contains_company_name(self, client: AsyncClient) -> None:
        """Response body includes the company_name field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["company_name"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_response_contains_current_price(self, client: AsyncClient) -> None:
        """Response body includes the current_price field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["current_price"] == pytest.approx(227.50)

    @pytest.mark.asyncio
    async def test_response_contains_recommendation(self, client: AsyncClient) -> None:
        """Response body includes the recommendation field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["recommendation"] == "buy"

    @pytest.mark.asyncio
    async def test_response_contains_confidence_score(self, client: AsyncClient) -> None:
        """Response body includes the confidence_score field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["confidence_score"] == pytest.approx(0.78)

    @pytest.mark.asyncio
    async def test_response_contains_summary(self, client: AsyncClient) -> None:
        """Response body includes the summary field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert "summary" in response.json()

    @pytest.mark.asyncio
    async def test_response_contains_risk_assessment(self, client: AsyncClient) -> None:
        """Response body includes a nested risk_assessment object."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        body = response.json()
        assert "risk_assessment" in body
        assert body["risk_assessment"]["overall_risk"] == "medium"

    @pytest.mark.asyncio
    async def test_response_contains_price_predictions(self, client: AsyncClient) -> None:
        """Response body includes a nested price_predictions object with three horizons."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        predictions = response.json()["price_predictions"]
        assert "one_week" in predictions
        assert "one_month" in predictions
        assert "three_months" in predictions

    @pytest.mark.asyncio
    async def test_response_body_is_json(self, client: AsyncClient) -> None:
        """Content-Type header must indicate JSON."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Service call verification
# ---------------------------------------------------------------------------


class TestAnalyzeStockServiceCall:
    """Verifies that the router delegates correctly to the AI service."""

    @pytest.mark.asyncio
    async def test_calls_analyze_with_uppercase_ticker(self, client: AsyncClient) -> None:
        """analyze() is invoked with the ticker exactly as supplied in the URL."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            await client.post("/api/analyze/AAPL")

        mock_analyze.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_calls_analyze_once(self, client: AsyncClient) -> None:
        """analyze() is called exactly once per request — no double-dispatch."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            await client.post("/api/analyze/AAPL")

        assert mock_analyze.call_count == 1

    @pytest.mark.asyncio
    async def test_ticker_forwarded_verbatim_to_service(self, client: AsyncClient) -> None:
        """The ticker in the path is forwarded verbatim to analyze(), preserving case."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            await client.post("/api/analyze/MSFT")

        mock_analyze.assert_called_once_with("MSFT")

    @pytest.mark.asyncio
    async def test_different_tickers_call_service_with_correct_arg(
        self, client: AsyncClient
    ) -> None:
        """Each distinct ticker path segment reaches analyze() unchanged."""
        tickers = ["TSLA", "NVDA", "GOOGL"]
        for ticker in tickers:
            with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = _MOCK_RESPONSE
                await client.post(f"/api/analyze/{ticker}")
            mock_analyze.assert_called_once_with(ticker)


# ---------------------------------------------------------------------------
# AIAnalysisError → 500
# ---------------------------------------------------------------------------


class TestAnalyzeStockAIAnalysisError:
    """When the AI service raises AIAnalysisError the router must return 500."""

    @pytest.mark.asyncio
    async def test_returns_500_on_ai_analysis_error(self, client: AsyncClient) -> None:
        """HTTP status must be 500 when analyze() raises AIAnalysisError."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = AIAnalysisError("model timed out")
            response = await client.post("/api/analyze/AAPL")

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_error_body_has_error_key(self, client: AsyncClient) -> None:
        """500 response body contains a top-level 'error' object."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = AIAnalysisError("model timed out")
            response = await client.post("/api/analyze/AAPL")

        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_error_body_contains_code(self, client: AsyncClient) -> None:
        """500 error JSON body includes the structured error code."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = AIAnalysisError("context window exceeded")
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["error"]["code"] == "AI_ANALYSIS_ERROR"

    @pytest.mark.asyncio
    async def test_error_body_contains_message(self, client: AsyncClient) -> None:
        """500 error JSON includes the human-readable message from the exception."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = AIAnalysisError("null response from API")
            response = await client.post("/api/analyze/AAPL")

        body = response.json()
        assert "message" in body["error"]
        assert "null response from API" in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_error_response_is_json(self, client: AsyncClient) -> None:
        """500 response must have JSON content-type, not plain text."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = AIAnalysisError("bad JSON from model")
            response = await client.post("/api/analyze/AAPL")

        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# StockNotFoundError → 404
# ---------------------------------------------------------------------------


class TestAnalyzeStockNotFoundError:
    """When the AI service raises StockNotFoundError the router must return 404."""

    @pytest.mark.asyncio
    async def test_returns_404_on_stock_not_found(self, client: AsyncClient) -> None:
        """HTTP status must be 404 when analyze() raises StockNotFoundError."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = StockNotFoundError("INVALID")
            response = await client.post("/api/analyze/INVALID")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_not_found_error_body_has_error_key(self, client: AsyncClient) -> None:
        """404 response body contains a top-level 'error' object."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = StockNotFoundError("ZZZZZ")
            response = await client.post("/api/analyze/ZZZZZ")

        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_not_found_error_body_contains_code(self, client: AsyncClient) -> None:
        """404 error JSON includes the STOCK_NOT_FOUND error code."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = StockNotFoundError("ZZZZZ")
            response = await client.post("/api/analyze/ZZZZZ")

        assert response.json()["error"]["code"] == "STOCK_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_not_found_error_body_contains_message(self, client: AsyncClient) -> None:
        """404 error JSON includes a message that references the missing ticker."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = StockNotFoundError("ZZZZZ")
            response = await client.post("/api/analyze/ZZZZZ")

        assert "ZZZZZ" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_not_found_response_is_json(self, client: AsyncClient) -> None:
        """404 response must have JSON content-type."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = StockNotFoundError("FAKE")
            response = await client.post("/api/analyze/FAKE")

        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# ExternalAPIError → 502
# ---------------------------------------------------------------------------


class TestAnalyzeStockExternalAPIError:
    """When the AI service raises ExternalAPIError the router must return 502."""

    @pytest.mark.asyncio
    async def test_returns_502_on_external_api_error(self, client: AsyncClient) -> None:
        """HTTP status must be 502 when analyze() raises ExternalAPIError."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = ExternalAPIError("Yahoo Finance", "connection timeout")
            response = await client.post("/api/analyze/AAPL")

        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_502_error_body_has_error_key(self, client: AsyncClient) -> None:
        """502 response body must contain a top-level 'error' object."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = ExternalAPIError("FMP", "503 upstream")
            response = await client.post("/api/analyze/TSLA")

        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_502_error_body_contains_code(self, client: AsyncClient) -> None:
        """502 error JSON body must include the EXTERNAL_API_ERROR code."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = ExternalAPIError("Yahoo Finance", "rate limited")
            response = await client.post("/api/analyze/AAPL")

        assert response.json()["error"]["code"] == "EXTERNAL_API_ERROR"

    @pytest.mark.asyncio
    async def test_502_response_is_json(self, client: AsyncClient) -> None:
        """502 response must have JSON content-type."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = ExternalAPIError("FMP", "unreachable")
            response = await client.post("/api/analyze/NVDA")

        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# URL-encoded and special-character tickers
# ---------------------------------------------------------------------------


class TestAnalyzeStockSpecialTickers:
    """Verifies routing behaviour for non-standard ticker path segments."""

    @pytest.mark.asyncio
    async def test_url_encoded_space_decoded_before_service(
        self, client: AsyncClient
    ) -> None:
        """A ticker path segment with a URL-encoded space is decoded by FastAPI
        and forwarded to the service as the decoded string."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            # %20 is a URL-encoded space; FastAPI path decodes it automatically
            await client.post("/api/analyze/BRK%20B")

        called_with = mock_analyze.call_args[0][0]
        assert " " in called_with or called_with == "BRK B"

    @pytest.mark.asyncio
    async def test_hyphenated_ticker_forwarded_verbatim(
        self, client: AsyncClient
    ) -> None:
        """Tickers containing a hyphen (e.g. BRK-B) are forwarded without mutation."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            await client.post("/api/analyze/BRK-B")

        mock_analyze.assert_called_once_with("BRK-B")

    @pytest.mark.asyncio
    async def test_lowercase_ticker_forwarded_as_is(
        self, client: AsyncClient
    ) -> None:
        """The router does NOT normalise case — lowercase ticker reaches the service unchanged."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            await client.post("/api/analyze/aapl")

        mock_analyze.assert_called_once_with("aapl")

    @pytest.mark.asyncio
    async def test_response_contains_all_required_top_level_fields(
        self, client: AsyncClient
    ) -> None:
        """A successful response must include every mandatory top-level field."""
        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = _MOCK_RESPONSE
            response = await client.post("/api/analyze/AAPL")

        body = response.json()
        required_fields = [
            "ticker",
            "company_name",
            "current_price",
            "recommendation",
            "confidence_score",
            "summary",
            "bull_case",
            "bear_case",
            "risk_assessment",
            "price_predictions",
            "analysis_timestamp",
        ]
        for field in required_fields:
            assert field in body, f"Missing required field: {field}"
