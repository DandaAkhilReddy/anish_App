"""Tests for AIAnalysisService.analyze() — two-phase market data + AI approach."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AIAnalysisError, ExternalAPIError, StockNotFoundError
from app.models.analysis import HistoricalPrice, LongTermOutlook, StockAnalysisResponse, TechnicalSnapshot
from app.services.ai_analysis_service import AIAnalysisService

# ---------------------------------------------------------------------------
# Module-level mock data constants
# ---------------------------------------------------------------------------

_MOCK_QUOTE: dict = {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "current_price": 185.50,
    "previous_close": 184.20,
    "open": 184.80,
    "day_high": 186.10,
    "day_low": 184.00,
    "volume": 45000000,
    "market_cap": "2.8T",
    "pe_ratio": 28.5,
    "eps": 6.51,
    "week_52_high": 199.62,
    "week_52_low": 164.08,
    "dividend_yield": 0.0054,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "headquarters": "Cupertino, California",
    "ceo": "",
    "founded": "",
    "employees": "164,000",
    "company_description": "Apple designs consumer electronics.",
}

_MOCK_HISTORY: list[HistoricalPrice] = [
    HistoricalPrice(date="2025-01-02", open=182.0, high=185.0, low=181.0, close=184.0, volume=40000000),
    HistoricalPrice(date="2025-01-03", open=184.0, high=187.0, low=183.5, close=186.5, volume=42000000),
]

_MOCK_TECHNICALS: TechnicalSnapshot = TechnicalSnapshot(
    sma_20=183.5,
    sma_50=180.2,
    sma_200=175.0,
    rsi_14=62.3,
    signal="neutral",
)

_MOCK_AI_RESPONSE: dict = {
    "recommendation": "buy",
    "confidence_score": 0.78,
    "summary": "Apple shows strong momentum.",
    "bull_case": "Strong ecosystem.",
    "bear_case": "Regulatory pressure.",
    "risk_assessment": {
        "overall_risk": "medium",
        "risk_factors": ["Regulation"],
        "risk_score": 0.45,
    },
    "price_predictions": {
        "one_week": {"low": 183.0, "mid": 186.0, "high": 189.0, "confidence": 0.75},
        "one_month": {"low": 180.0, "mid": 190.0, "high": 200.0, "confidence": 0.65},
        "three_months": {"low": 175.0, "mid": 195.0, "high": 215.0, "confidence": 0.55},
    },
    "news": [{"title": "Apple Reports Strong Q1", "source": "Reuters", "sentiment": "positive"}],
    "quarterly_earnings": [
        {
            "quarter": "Q1 2025",
            "revenue": 94900,
            "net_income": 23600,
            "eps": 1.53,
            "yoy_revenue_growth": 0.05,
        }
    ],
    "support_levels": [180.0, 175.0],
    "resistance_levels": [190.0, 195.0],
    "signal": "buy",
    "ceo": "Tim Cook",
    "founded": "1976",
    "long_term_outlook": {
        "one_year": {"low": 170.0, "mid": 200.0, "high": 230.0, "confidence": 0.70},
        "five_year": {"low": 200.0, "mid": 300.0, "high": 400.0, "confidence": 0.55},
        "ten_year": {"low": 250.0, "mid": 450.0, "high": 650.0, "confidence": 0.40},
        "verdict": "buy",
        "verdict_rationale": "Strong ecosystem and services growth support long-term appreciation.",
        "catalysts": ["AI integration", "Services expansion"],
        "long_term_risks": ["Regulatory pressure", "Hardware saturation"],
        "compound_annual_return": 12.5,
    },
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_provider() -> AsyncMock:
    """AsyncMock standing in for OpenAIProvider.

    Returns a mock whose ``chat_completion_json`` is an awaitable that
    returns the canonical qualitative-only mock AI response by default.
    """
    provider = AsyncMock()
    provider.chat_completion_json = AsyncMock(return_value=dict(_MOCK_AI_RESPONSE))
    return provider


@pytest.fixture()
def mock_market() -> AsyncMock:
    """AsyncMock standing in for MarketDataService.

    All three data-fetch methods return the canonical mock data.
    ``get_quote`` uses a side_effect so the returned ticker reflects the
    symbol that was passed in — required for ticker-normalisation assertions.
    """
    market = AsyncMock()
    market.resolve_ticker = AsyncMock(side_effect=lambda t: t.upper().strip())
    market.search_ticker = AsyncMock(side_effect=StockNotFoundError("no match"))
    market.get_quote = AsyncMock(
        side_effect=lambda t, **_: {**_MOCK_QUOTE, "ticker": t}
    )
    market.get_historical = AsyncMock(return_value=list(_MOCK_HISTORY))
    market.get_technicals = AsyncMock(return_value=_MOCK_TECHNICALS)
    return market


@pytest.fixture()
def service(mock_provider: AsyncMock, mock_market: AsyncMock) -> AIAnalysisService:
    """AIAnalysisService wired to both the mock provider and mock market."""
    return AIAnalysisService(provider=mock_provider, market_data=mock_market)


# ---------------------------------------------------------------------------
# Ticker normalisation
# ---------------------------------------------------------------------------


class TestTickerNormalisation:
    @pytest.mark.asyncio
    async def test_analyze_uppercases_lowercase_ticker(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """Lowercase ticker is upper-cased before being passed to the AI prompt."""
        await service.analyze("aapl")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "AAPL" in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_analyze_uppercases_mixed_case_ticker(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """Mixed-case ticker is normalised to uppercase."""
        await service.analyze("MsFt")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "MSFT" in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_analyze_strips_leading_whitespace(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """Leading whitespace is stripped before processing."""
        await service.analyze("  AAPL")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "AAPL" in kwargs["user_prompt"]
        assert "  AAPL" not in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_analyze_strips_trailing_whitespace(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """Trailing whitespace is stripped before processing."""
        await service.analyze("AAPL  ")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "AAPL" in kwargs["user_prompt"]
        assert "AAPL  " not in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_analyze_strips_whitespace_and_uppercases_together(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """Whitespace stripping and uppercasing both apply in one pass."""
        await service.analyze("  tsla  ")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "TSLA" in kwargs["user_prompt"]


# ---------------------------------------------------------------------------
# Market data service call arguments
# ---------------------------------------------------------------------------


class TestMarketDataCalls:
    @pytest.mark.asyncio
    async def test_analyze_calls_get_quote_with_normalised_ticker(
        self, service: AIAnalysisService, mock_market: AsyncMock
    ) -> None:
        """get_quote is called with the uppercased ticker."""
        await service.analyze("aapl")

        mock_market.get_quote.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_calls_get_historical(
        self, service: AIAnalysisService, mock_market: AsyncMock
    ) -> None:
        """get_historical is called exactly once per analyze call."""
        await service.analyze("AAPL")

        mock_market.get_historical.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_calls_get_technicals(
        self, service: AIAnalysisService, mock_market: AsyncMock
    ) -> None:
        """get_technicals is called exactly once per analyze call."""
        await service.analyze("AAPL")

        mock_market.get_technicals.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_calls_all_three_market_methods(
        self, service: AIAnalysisService, mock_market: AsyncMock
    ) -> None:
        """All three market data calls are issued for a single analyze call."""
        await service.analyze("AAPL")

        mock_market.get_quote.assert_called_once()
        mock_market.get_historical.assert_called_once()
        mock_market.get_technicals.assert_called_once()


# ---------------------------------------------------------------------------
# Provider call arguments
# ---------------------------------------------------------------------------


class TestProviderCallArguments:
    @pytest.mark.asyncio
    async def test_analyze_passes_system_prompt(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """chat_completion_json receives a non-empty system_prompt kwarg."""
        await service.analyze("AAPL")

        mock_provider.chat_completion_json.assert_called_once()
        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "system_prompt" in kwargs
        assert len(kwargs["system_prompt"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_passes_user_prompt_containing_ticker(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """User prompt forwarded to AI contains the stock ticker."""
        await service.analyze("NVDA")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "NVDA" in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_analyze_passes_max_tokens_8000(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """Phase-2 AI call uses max_tokens=8000 (qualitative-only, smaller budget)."""
        await service.analyze("AAPL")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert kwargs["max_tokens"] == 8000

    @pytest.mark.asyncio
    async def test_analyze_calls_provider_exactly_once(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """AI provider is called exactly once per analyze invocation."""
        await service.analyze("AAPL")

        mock_provider.chat_completion_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_user_prompt_does_not_contain_raw_ticker_format_placeholder(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """The {ticker} template placeholder must be substituted, not left verbatim."""
        await service.analyze("AAPL")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "{ticker}" not in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_analyze_user_prompt_contains_real_price_data(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """User prompt forwarded to AI contains the real market price from the quote."""
        await service.analyze("AAPL")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "185.5" in kwargs["user_prompt"]


# ---------------------------------------------------------------------------
# Successful response parsing
# ---------------------------------------------------------------------------


class TestSuccessfulResponse:
    @pytest.mark.asyncio
    async def test_analyze_returns_stock_analysis_response_type(
        self, service: AIAnalysisService
    ) -> None:
        """Return value is always a StockAnalysisResponse instance."""
        result = await service.analyze("AAPL")

        assert isinstance(result, StockAnalysisResponse)

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_ticker(
        self, service: AIAnalysisService
    ) -> None:
        """Ticker in the response matches the normalised input symbol."""
        result = await service.analyze("AAPL")

        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_company_name(
        self, service: AIAnalysisService
    ) -> None:
        """Company name comes from the market quote, not the AI response."""
        result = await service.analyze("AAPL")

        assert result.company_name == "Apple Inc."

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_current_price(
        self, service: AIAnalysisService
    ) -> None:
        """Current price is sourced from the real market quote."""
        result = await service.analyze("AAPL")

        assert result.current_price == pytest.approx(185.50)

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_previous_close(
        self, service: AIAnalysisService
    ) -> None:
        """Previous close comes from the real market quote."""
        result = await service.analyze("AAPL")

        assert result.previous_close == pytest.approx(184.20)

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_recommendation(
        self, service: AIAnalysisService
    ) -> None:
        """Recommendation comes from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert result.recommendation == "buy"

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_confidence_score(
        self, service: AIAnalysisService
    ) -> None:
        """Confidence score comes from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert result.confidence_score == pytest.approx(0.78)

    @pytest.mark.asyncio
    async def test_analyze_returns_technical_snapshot(
        self, service: AIAnalysisService
    ) -> None:
        """Technical snapshot is built from real market technicals, signal from AI."""
        result = await service.analyze("AAPL")

        assert result.technical is not None
        # RSI sourced from real market data (mock_market.get_technicals)
        assert result.technical.rsi_14 == pytest.approx(62.3)
        # Signal overridden by AI's signal field
        assert result.technical.signal == "buy"

    @pytest.mark.asyncio
    async def test_analyze_returns_technical_sma_from_market_data(
        self, service: AIAnalysisService
    ) -> None:
        """SMA values in the technical snapshot come from real market technicals."""
        result = await service.analyze("AAPL")

        assert result.technical is not None
        assert result.technical.sma_20 == pytest.approx(183.5)
        assert result.technical.sma_50 == pytest.approx(180.2)
        assert result.technical.sma_200 == pytest.approx(175.0)

    @pytest.mark.asyncio
    async def test_analyze_returns_news_items(
        self, service: AIAnalysisService
    ) -> None:
        """News items come from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert len(result.news) == 1
        assert result.news[0].title == "Apple Reports Strong Q1"
        assert result.news[0].sentiment == "positive"

    @pytest.mark.asyncio
    async def test_analyze_returns_quarterly_earnings(
        self, service: AIAnalysisService
    ) -> None:
        """Quarterly earnings come from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert len(result.quarterly_earnings) == 1
        assert result.quarterly_earnings[0].quarter == "Q1 2025"

    @pytest.mark.asyncio
    async def test_analyze_returns_risk_assessment(
        self, service: AIAnalysisService
    ) -> None:
        """Risk assessment comes from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert result.risk_assessment.overall_risk == "medium"
        assert result.risk_assessment.risk_score == pytest.approx(0.45)

    @pytest.mark.asyncio
    async def test_analyze_returns_price_predictions(
        self, service: AIAnalysisService
    ) -> None:
        """Price predictions come from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert result.price_predictions.one_week.mid == pytest.approx(186.0)
        assert result.price_predictions.one_month.confidence == pytest.approx(0.65)
        assert result.price_predictions.three_months.high == pytest.approx(215.0)

    @pytest.mark.asyncio
    async def test_analyze_populates_analysis_timestamp(
        self, service: AIAnalysisService
    ) -> None:
        """analysis_timestamp is always populated after a successful call."""
        result = await service.analyze("AAPL")

        assert result.analysis_timestamp is not None

    @pytest.mark.asyncio
    async def test_analyze_returns_historical_prices_from_market(
        self, service: AIAnalysisService
    ) -> None:
        """historical_prices are sourced from the real market data service."""
        result = await service.analyze("AAPL")

        assert len(result.historical_prices) == 2
        assert result.historical_prices[0].date == "2025-01-02"

    @pytest.mark.asyncio
    async def test_analyze_ticker_in_response_is_resolved_from_quote(
        self,
        mock_provider: AsyncMock,
        mock_market: AsyncMock,
    ) -> None:
        """Ticker in the response is taken from the quote (resolved by yfinance), uppercased."""
        # quote returns the normalised uppercase ticker from mock_market's side_effect
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_analyze_ceo_from_ai_response(
        self, service: AIAnalysisService
    ) -> None:
        """CEO field is populated from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert result.ceo == "Tim Cook"

    @pytest.mark.asyncio
    async def test_analyze_founded_from_ai_response(
        self, service: AIAnalysisService
    ) -> None:
        """Founded year is populated from the AI qualitative response."""
        result = await service.analyze("AAPL")

        assert result.founded == "1976"

    @pytest.mark.asyncio
    async def test_analyze_support_levels_merged_from_ai(
        self, service: AIAnalysisService
    ) -> None:
        """Support levels from AI response are merged into the technical snapshot."""
        result = await service.analyze("AAPL")

        assert result.technical is not None
        assert 180.0 in result.technical.support_levels
        assert 175.0 in result.technical.support_levels

    @pytest.mark.asyncio
    async def test_analyze_resistance_levels_merged_from_ai(
        self, service: AIAnalysisService
    ) -> None:
        """Resistance levels from AI response are merged into the technical snapshot."""
        result = await service.analyze("AAPL")

        assert result.technical is not None
        assert 190.0 in result.technical.resistance_levels
        assert 195.0 in result.technical.resistance_levels

    @pytest.mark.asyncio
    async def test_analyze_returns_long_term_outlook(
        self, service: AIAnalysisService
    ) -> None:
        """Long-term outlook is parsed from the AI response when present."""
        result = await service.analyze("AAPL")

        assert result.long_term_outlook is not None
        assert isinstance(result.long_term_outlook, LongTermOutlook)
        assert result.long_term_outlook.verdict == "buy"
        assert result.long_term_outlook.compound_annual_return == pytest.approx(12.5)
        assert result.long_term_outlook.one_year.mid == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_analyze_long_term_outlook_none_when_absent(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """Long-term outlook is None when the AI response omits the field."""
        ai_response = dict(_MOCK_AI_RESPONSE)
        del ai_response["long_term_outlook"]
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_response)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.long_term_outlook is None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_analyze_re_raises_ai_analysis_error_unchanged(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """AIAnalysisError from the provider must bubble up unmodified."""
        original = AIAnalysisError("upstream failure")
        mock_provider.chat_completion_json = AsyncMock(side_effect=original)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="upstream failure"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_does_not_double_wrap_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """AIAnalysisError from the provider must bubble up as-is, not wrapped again."""
        original = AIAnalysisError("provider broke")
        mock_provider.chat_completion_json = AsyncMock(side_effect=original)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError) as exc_info:
            await service.analyze("AAPL")

        # __cause__ should be None — re-raised, not chained
        assert exc_info.value.__cause__ is None

    @pytest.mark.asyncio
    async def test_analyze_wraps_generic_exception_in_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """RuntimeError from the AI provider is wrapped in AIAnalysisError."""
        mock_provider.chat_completion_json = AsyncMock(
            side_effect=RuntimeError("network timeout")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_wraps_generic_exception_preserves_original_message(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """The original exception message is preserved inside the AIAnalysisError."""
        mock_provider.chat_completion_json = AsyncMock(
            side_effect=RuntimeError("network timeout")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="network timeout"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_wraps_generic_exception_chains_cause(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """The original exception is chained as __cause__ on the AIAnalysisError."""
        original = RuntimeError("dns failure")
        mock_provider.chat_completion_json = AsyncMock(side_effect=original)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError) as exc_info:
            await service.analyze("AAPL")

        assert exc_info.value.__cause__ is original

    @pytest.mark.asyncio
    async def test_analyze_wraps_value_error_in_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """ValueError from the AI provider is wrapped in AIAnalysisError."""
        mock_provider.chat_completion_json = AsyncMock(
            side_effect=ValueError("unexpected value")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="unexpected value"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_raises_ai_analysis_error_on_missing_required_key(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """AI response missing required qualitative fields (e.g. recommendation) raises AIAnalysisError."""
        bad_payload: dict = {}  # missing recommendation, confidence_score, summary, etc.
        mock_provider.chat_completion_json = AsyncMock(return_value=bad_payload)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_propagates_stock_not_found_after_fallback(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """StockNotFoundError propagates when both get_quote and search_ticker fail."""
        mock_market.get_quote = AsyncMock(side_effect=StockNotFoundError("FAKE"))
        mock_market.search_ticker = AsyncMock(
            side_effect=StockNotFoundError("FAKE")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(StockNotFoundError, match="FAKE"):
            await service.analyze("FAKE")

    @pytest.mark.asyncio
    async def test_analyze_falls_back_to_search_on_stock_not_found(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When get_quote raises StockNotFoundError, search_ticker is tried."""
        call_count = 0

        async def get_quote_side_effect(t: str, **_: object) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise StockNotFoundError(t)
            return {**_MOCK_QUOTE, "ticker": "TSLA"}

        mock_market.get_quote = AsyncMock(side_effect=get_quote_side_effect)
        mock_market.search_ticker = AsyncMock(return_value="TSLA")
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("TESLA")
        assert result.ticker == "TSLA"
        mock_market.search_ticker.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_propagates_external_api_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """ExternalAPIError from market data triggers search fallback.

        When get_quote raises ExternalAPIError, the service falls back
        to search_ticker. If search also fails, the error propagates.
        """
        mock_market.get_quote = AsyncMock(
            side_effect=ExternalAPIError("FMP API", "connection refused")
        )
        mock_market.search_ticker = AsyncMock(
            side_effect=ExternalAPIError("FMP API", "connection refused")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(ExternalAPIError):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_wraps_market_runtime_error_as_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """RuntimeError from get_historical is wrapped in AIAnalysisError."""
        mock_market.get_historical = AsyncMock(
            side_effect=RuntimeError("FMP API unavailable")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="FMP API unavailable"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_does_not_call_ai_when_market_fetch_fails(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """If market data fetch fails, the AI provider must not be called at all."""
        mock_market.get_quote = AsyncMock(side_effect=RuntimeError("timeout"))
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError):
            await service.analyze("AAPL")

        mock_provider.chat_completion_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_calls_resolve_ticker(
        self, service: AIAnalysisService, mock_market: AsyncMock
    ) -> None:
        """resolve_ticker is called before market data fetch."""
        await service.analyze("AAPL")

        mock_market.resolve_ticker.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_propagates_stock_not_found_from_resolve(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """StockNotFoundError from resolve_ticker propagates as-is."""
        mock_market.resolve_ticker = AsyncMock(
            side_effect=StockNotFoundError("XYZFAKE")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(StockNotFoundError, match="XYZFAKE"):
            await service.analyze("XYZFAKE")


# ---------------------------------------------------------------------------
# Default provider / market construction
# ---------------------------------------------------------------------------


class TestDefaultProviderConstruction:
    def test_init_creates_openai_provider_when_none_given(self) -> None:
        """Constructor must instantiate OpenAIProvider when no provider is supplied."""
        with patch("app.services.ai_analysis_service.OpenAIProvider") as mock_cls:
            mock_cls.return_value = AsyncMock()
            with patch("app.services.ai_analysis_service.MarketDataService"):
                svc = AIAnalysisService()
                mock_cls.assert_called_once()
                assert svc._provider is mock_cls.return_value

    def test_init_creates_market_data_service_when_none_given(self) -> None:
        """Constructor must instantiate MarketDataService when no market_data is supplied."""
        with patch("app.services.ai_analysis_service.MarketDataService") as mock_cls:
            mock_cls.return_value = AsyncMock()
            with patch("app.services.ai_analysis_service.OpenAIProvider"):
                svc = AIAnalysisService()
                mock_cls.assert_called_once()
                assert svc._market is mock_cls.return_value

    def test_init_uses_supplied_provider(self, mock_provider: AsyncMock) -> None:
        """Supplied provider is stored without replacement."""
        with patch("app.services.ai_analysis_service.MarketDataService"):
            svc = AIAnalysisService(provider=mock_provider)
            assert svc._provider is mock_provider

    def test_init_uses_supplied_market_data(self, mock_market: AsyncMock) -> None:
        """Supplied market_data is stored without replacement."""
        with patch("app.services.ai_analysis_service.OpenAIProvider"):
            svc = AIAnalysisService(market_data=mock_market)
            assert svc._market is mock_market


# ---------------------------------------------------------------------------
# Ticker resolution edge cases
# ---------------------------------------------------------------------------


class TestTickerResolutionEdgeCases:
    @pytest.mark.asyncio
    async def test_analyze_mixed_case_all_chars_normalized(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """'aApL' is normalised to 'AAPL' before resolve_ticker is called."""
        mock_market.resolve_ticker = AsyncMock(side_effect=lambda t: t)  # echo back
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("aApL")

        # resolve_ticker must receive the already-uppercased ticker
        mock_market.resolve_ticker.assert_called_once_with("AAPL")
        # quote mock echoes the ticker it receives, so result.ticker must be AAPL
        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_analyze_very_long_ticker_normalised(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """A 20-character lower-case string is uppercased before being forwarded."""
        long_input = "longcompanynamexyz12"  # 20 chars, no real meaning
        mock_market.resolve_ticker = AsyncMock(return_value="LCNX")
        mock_market.get_quote = AsyncMock(
            return_value={**_MOCK_QUOTE, "ticker": "LCNX"}
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze(long_input)

        # resolve_ticker receives the uppercased form
        mock_market.resolve_ticker.assert_called_once_with(long_input.upper())
        assert result.ticker == "LCNX"

    @pytest.mark.asyncio
    async def test_analyze_fast_path_fails_then_search_ticker_used(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When the first gather raises StockNotFoundError, search_ticker is called.

        The second gather then succeeds, and the resolved symbol from search
        is the one that ends up in the response.
        """
        call_count = 0

        async def flaky_quote(t: str, **_: object) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise StockNotFoundError(t)
            return {**_MOCK_QUOTE, "ticker": "NVDA"}

        mock_market.get_quote = AsyncMock(side_effect=flaky_quote)
        mock_market.search_ticker = AsyncMock(return_value="NVDA")
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("nvidia")

        mock_market.search_ticker.assert_called_once()
        assert result.ticker == "NVDA"

    @pytest.mark.asyncio
    async def test_analyze_search_ticker_called_once_on_fast_path_failure(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """search_ticker is invoked exactly once when the fast-path gather fails."""
        call_count = 0

        async def fail_once(t: str, **_: object) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ExternalAPIError("yfinance", "timeout")
            return {**_MOCK_QUOTE, "ticker": "TSLA"}

        mock_market.get_quote = AsyncMock(side_effect=fail_once)
        mock_market.search_ticker = AsyncMock(return_value="TSLA")
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        await service.analyze("tesla")

        mock_market.search_ticker.assert_called_once()


# ---------------------------------------------------------------------------
# Parallel fetch partial failures
# ---------------------------------------------------------------------------


class TestParallelFetchPartialFailures:
    @pytest.mark.asyncio
    async def test_get_historical_runtime_error_wraps_to_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """RuntimeError in get_historical (inside the first gather) is caught and
        wrapped in AIAnalysisError — it is not a StockNotFoundError so the generic
        handler fires, not the search fallback."""
        mock_market.get_historical = AsyncMock(
            side_effect=RuntimeError("history unavailable")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="history unavailable"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_get_technicals_runtime_error_wraps_to_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """RuntimeError in get_technicals (inside the first gather) is wrapped in
        AIAnalysisError — the generic except branch fires."""
        mock_market.get_technicals = AsyncMock(
            side_effect=RuntimeError("technicals unavailable")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="technicals unavailable"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_all_three_parallel_calls_succeed_data_present_in_response(
        self, service: AIAnalysisService, mock_market: AsyncMock
    ) -> None:
        """When all three parallel calls succeed, all data is present in the response."""
        result = await service.analyze("AAPL")

        # Market quote fields
        assert result.current_price == pytest.approx(185.50)
        assert result.volume == 45_000_000
        assert result.pe_ratio == pytest.approx(28.5)
        # Historical prices from get_historical
        assert len(result.historical_prices) == 2
        # Technicals from get_technicals
        assert result.technical is not None
        assert result.technical.rsi_14 == pytest.approx(62.3)
        assert result.technical.sma_50 == pytest.approx(180.2)

    @pytest.mark.asyncio
    async def test_get_historical_not_found_triggers_search_fallback(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """StockNotFoundError raised by get_historical triggers the search_ticker
        fallback path, which then retries all three market calls."""
        first_call = True

        async def history_fail_once(t: str, **_: object) -> list[HistoricalPrice]:
            nonlocal first_call
            if first_call:
                first_call = False
                raise StockNotFoundError(t)
            return list(_MOCK_HISTORY)

        mock_market.get_historical = AsyncMock(side_effect=history_fail_once)
        mock_market.search_ticker = AsyncMock(return_value="AAPL")
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        mock_market.search_ticker.assert_called_once()
        assert isinstance(result, StockAnalysisResponse)


# ---------------------------------------------------------------------------
# AI provider interaction edge cases
# ---------------------------------------------------------------------------


class TestAIProviderInteractionEdgeCases:
    @pytest.mark.asyncio
    async def test_provider_returns_minimal_json_defaults_fill_in(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When the AI response contains only the required fields, optional fields
        default to empty lists / None / empty strings without raising."""
        minimal_ai: dict = {
            "recommendation": "hold",
            "confidence_score": 0.5,
            "summary": "Minimal summary.",
            "bull_case": "Some upside.",
            "bear_case": "Some downside.",
            "risk_assessment": {
                "overall_risk": "medium",
                "risk_score": 0.5,
            },
            "price_predictions": {
                "one_week": {"low": 100.0, "mid": 105.0, "high": 110.0, "confidence": 0.6},
                "one_month": {"low": 95.0, "mid": 108.0, "high": 120.0, "confidence": 0.5},
                "three_months": {"low": 90.0, "mid": 115.0, "high": 140.0, "confidence": 0.4},
            },
        }
        mock_provider.chat_completion_json = AsyncMock(return_value=minimal_ai)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.recommendation == "hold"
        assert result.news == []
        assert result.quarterly_earnings == []
        assert result.ceo == ""
        assert result.founded == ""
        assert result.long_term_outlook is None
        assert result.technical.support_levels == []
        assert result.technical.resistance_levels == []

    @pytest.mark.asyncio
    async def test_provider_returns_extra_fields_they_are_ignored(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """Extra unknown fields in the AI JSON response must be silently ignored
        and must not raise an exception."""
        ai_with_extras = dict(_MOCK_AI_RESPONSE)
        ai_with_extras["unknown_field_xyz"] = "should be ignored"
        ai_with_extras["another_extra"] = {"nested": True}
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_with_extras)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        # All required fields still parsed correctly
        assert result.recommendation == "buy"
        assert result.confidence_score == pytest.approx(0.78)

    @pytest.mark.asyncio
    async def test_provider_asyncio_timeout_wraps_to_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """asyncio.TimeoutError from the provider is wrapped in AIAnalysisError."""
        mock_provider.chat_completion_json = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_provider_asyncio_timeout_chains_original_cause(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """The original asyncio.TimeoutError is chained as __cause__ on the
        wrapped AIAnalysisError."""
        original = asyncio.TimeoutError()
        mock_provider.chat_completion_json = AsyncMock(side_effect=original)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError) as exc_info:
            await service.analyze("AAPL")

        assert exc_info.value.__cause__ is original

    @pytest.mark.asyncio
    async def test_provider_connection_error_wraps_to_ai_analysis_error(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """ConnectionError (e.g. network reset) from provider is wrapped in
        AIAnalysisError, not leaked as a raw exception."""
        mock_provider.chat_completion_json = AsyncMock(
            side_effect=ConnectionError("connection reset")
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="connection reset"):
            await service.analyze("AAPL")


# ---------------------------------------------------------------------------
# Response merging — real data overrides AI values
# ---------------------------------------------------------------------------


class TestResponseMerging:
    @pytest.mark.asyncio
    async def test_current_price_always_from_quote_not_ai(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """current_price in the response must come from the quote dict, even if the
        AI response also returned a price field (it shouldn't, but merging is explicit)."""
        # Inject an AI response that has no price fields — real data must win
        ai_response = dict(_MOCK_AI_RESPONSE)
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_response)
        # Quote reports a distinct price
        mock_market.get_quote = AsyncMock(
            return_value={**_MOCK_QUOTE, "current_price": 999.99, "ticker": "AAPL"}
        )
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.current_price == pytest.approx(999.99)

    @pytest.mark.asyncio
    async def test_historical_prices_sourced_from_market_data_not_ai(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """historical_prices in the response is the exact list returned by
        get_historical — the AI response never contributes to it."""
        extended_history = [
            HistoricalPrice(date="2025-03-01", open=170.0, high=175.0, low=169.0, close=173.0, volume=50000000),
            HistoricalPrice(date="2025-03-02", open=173.0, high=178.0, low=172.0, close=177.0, volume=48000000),
            HistoricalPrice(date="2025-03-03", open=177.0, high=180.0, low=176.0, close=179.0, volume=46000000),
        ]
        mock_market.get_historical = AsyncMock(return_value=extended_history)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert len(result.historical_prices) == 3
        assert result.historical_prices[0].date == "2025-03-01"
        assert result.historical_prices[2].close == pytest.approx(179.0)

    @pytest.mark.asyncio
    async def test_technical_snapshot_real_values_preserved_in_merge(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """All real technical indicator values (SMA, EMA, RSI, MACD, Bollinger)
        from market data are preserved in the merged TechnicalSnapshot."""
        rich_technicals = TechnicalSnapshot(
            sma_20=200.0,
            sma_50=195.0,
            sma_200=180.0,
            ema_12=202.0,
            ema_26=198.0,
            rsi_14=55.0,
            macd_line=1.5,
            macd_signal=1.2,
            macd_histogram=0.3,
            bollinger_upper=210.0,
            bollinger_middle=200.0,
            bollinger_lower=190.0,
            signal="neutral",
        )
        mock_market.get_technicals = AsyncMock(return_value=rich_technicals)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        t = result.technical
        assert t is not None
        assert t.sma_20 == pytest.approx(200.0)
        assert t.sma_50 == pytest.approx(195.0)
        assert t.sma_200 == pytest.approx(180.0)
        assert t.ema_12 == pytest.approx(202.0)
        assert t.ema_26 == pytest.approx(198.0)
        assert t.rsi_14 == pytest.approx(55.0)
        assert t.macd_line == pytest.approx(1.5)
        assert t.macd_signal == pytest.approx(1.2)
        assert t.macd_histogram == pytest.approx(0.3)
        assert t.bollinger_upper == pytest.approx(210.0)
        assert t.bollinger_middle == pytest.approx(200.0)
        assert t.bollinger_lower == pytest.approx(190.0)

    @pytest.mark.asyncio
    async def test_ai_signal_overrides_market_signal_in_merged_technical(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """The signal field in the merged TechnicalSnapshot comes from the AI
        response, not from the market data technical snapshot."""
        market_technicals = TechnicalSnapshot(signal="neutral", sma_20=183.5)
        mock_market.get_technicals = AsyncMock(return_value=market_technicals)
        ai_response = dict(_MOCK_AI_RESPONSE)
        ai_response["signal"] = "strong_sell"
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_response)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.technical.signal == "strong_sell"

    @pytest.mark.asyncio
    async def test_company_fields_from_quote_not_ai(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """sector, industry, headquarters, company_description come from the quote
        dict, not from the AI response."""
        custom_quote = {
            **_MOCK_QUOTE,
            "ticker": "AAPL",
            "sector": "FinTech",
            "industry": "Payments",
            "headquarters": "San Francisco, CA",
            "company_description": "A custom description.",
        }
        mock_market.get_quote = AsyncMock(return_value=custom_quote)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.sector == "FinTech"
        assert result.industry == "Payments"
        assert result.headquarters == "San Francisco, CA"
        assert result.company_description == "A custom description."

    @pytest.mark.asyncio
    async def test_empty_historical_prices_list_propagated(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When get_historical returns an empty list, the response contains an
        empty historical_prices list — not None and no crash."""
        mock_market.get_historical = AsyncMock(return_value=[])
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.historical_prices == []

    @pytest.mark.asyncio
    async def test_all_none_technicals_merged_cleanly(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """A fully sparse TechnicalSnapshot (all fields None) from market data
        merges without raising — all indicator fields remain None."""
        empty_technicals = TechnicalSnapshot()  # all None, signal defaults to "neutral"
        mock_market.get_technicals = AsyncMock(return_value=empty_technicals)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        t = result.technical
        assert t is not None
        assert t.sma_20 is None
        assert t.sma_50 is None
        assert t.rsi_14 is None
        assert t.macd_line is None

    @pytest.mark.asyncio
    async def test_empty_support_and_resistance_in_ai_response(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When AI response has empty support_levels and resistance_levels, the
        merged technical snapshot contains empty lists (not None)."""
        ai_response = dict(_MOCK_AI_RESPONSE)
        ai_response["support_levels"] = []
        ai_response["resistance_levels"] = []
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_response)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.technical.support_levels == []
        assert result.technical.resistance_levels == []

    @pytest.mark.asyncio
    async def test_empty_news_list_from_ai_response(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When AI response returns an empty news list, result.news is an empty
        list — not None, not the default from a prior call."""
        ai_response = dict(_MOCK_AI_RESPONSE)
        ai_response["news"] = []
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_response)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.news == []

    @pytest.mark.asyncio
    async def test_empty_quarterly_earnings_from_ai_response(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When AI response returns an empty quarterly_earnings list, the response
        list is also empty."""
        ai_response = dict(_MOCK_AI_RESPONSE)
        ai_response["quarterly_earnings"] = []
        mock_provider.chat_completion_json = AsyncMock(return_value=ai_response)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        result = await service.analyze("AAPL")

        assert result.quarterly_earnings == []


# ---------------------------------------------------------------------------
# Error propagation — detailed scenarios
# ---------------------------------------------------------------------------


class TestErrorPropagationDetailed:
    @pytest.mark.asyncio
    async def test_stock_not_found_from_first_gather_propagates_after_second_fails(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """StockNotFoundError raised in the first gather triggers search_ticker.
        If the second gather also raises StockNotFoundError, it propagates as-is
        (not wrapped in AIAnalysisError)."""
        mock_market.get_quote = AsyncMock(side_effect=StockNotFoundError("GHOST"))
        mock_market.search_ticker = AsyncMock(return_value="GHOST")
        # Second gather also raises StockNotFoundError
        call_count = 0

        async def always_fail(t: str, **_: object) -> dict:
            nonlocal call_count
            call_count += 1
            raise StockNotFoundError(t)

        mock_market.get_quote = AsyncMock(side_effect=always_fail)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(StockNotFoundError):
            await service.analyze("GHOST")

    @pytest.mark.asyncio
    async def test_external_api_error_from_first_gather_triggers_search(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """ExternalAPIError in the first gather triggers the search_ticker fallback.
        If search succeeds but the second gather raises a generic error, it is
        wrapped in AIAnalysisError."""
        call_count = 0

        async def api_fail_then_runtime(t: str, **_: object) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ExternalAPIError("yfinance", "rate limited")
            raise RuntimeError("unexpected parse error")

        mock_market.get_quote = AsyncMock(side_effect=api_fail_then_runtime)
        mock_market.search_ticker = AsyncMock(return_value="AAPL")
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError, match="unexpected parse error"):
            await service.analyze("AAPL")

    @pytest.mark.asyncio
    async def test_generic_exception_from_market_is_wrapped_not_propagated_raw(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """A bare Exception from get_quote is caught and wrapped in AIAnalysisError —
        it must not leak as a raw Exception to the caller."""
        mock_market.get_quote = AsyncMock(side_effect=Exception("unexpected error"))
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        exc = None
        try:
            await service.analyze("AAPL")
        except AIAnalysisError as e:
            exc = e
        except Exception:
            pytest.fail("Raw Exception leaked; expected AIAnalysisError")

        assert exc is not None

    @pytest.mark.asyncio
    async def test_ai_analysis_error_is_not_wrapped_a_second_time(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """AIAnalysisError raised by the AI provider must pass through the
        generic `except Exception` guard without being double-wrapped."""
        original = AIAnalysisError("provider failure")
        mock_provider.chat_completion_json = AsyncMock(side_effect=original)
        service = AIAnalysisService(provider=mock_provider, market_data=mock_market)

        with pytest.raises(AIAnalysisError) as exc_info:
            await service.analyze("AAPL")

        # Same instance, not a new wrapper
        assert exc_info.value is original


# ---------------------------------------------------------------------------
# SharePoint research enrichment
# ---------------------------------------------------------------------------


class TestSharePointResearchEnrichment:
    @pytest.mark.asyncio
    async def test_research_context_included_in_response_when_sharepoint_present(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When a SharePoint provider is supplied and succeeds, research_context
        and research_sources are populated in the response."""
        sharepoint = AsyncMock()
        sharepoint.research_company = AsyncMock(
            return_value=(
                "Apple is expanding its AI features.",
                ["https://example.com/apple-ai"],
            )
        )
        service = AIAnalysisService(
            provider=mock_provider,
            market_data=mock_market,
            sharepoint=sharepoint,
        )

        result = await service.analyze("AAPL")

        assert result.research_context == "Apple is expanding its AI features."
        assert result.research_sources == ["https://example.com/apple-ai"]

    @pytest.mark.asyncio
    async def test_research_context_empty_when_no_sharepoint(
        self, service: AIAnalysisService
    ) -> None:
        """When no SharePoint provider is given, research_context and
        research_sources are empty in the response."""
        result = await service.analyze("AAPL")

        assert result.research_context == ""
        assert result.research_sources == []

    @pytest.mark.asyncio
    async def test_sharepoint_failure_is_non_blocking(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """A failing SharePoint call must not raise — analysis completes with
        empty research context and the exception is swallowed (logged only)."""
        sharepoint = AsyncMock()
        sharepoint.research_company = AsyncMock(
            side_effect=RuntimeError("SharePoint unreachable")
        )
        service = AIAnalysisService(
            provider=mock_provider,
            market_data=mock_market,
            sharepoint=sharepoint,
        )

        result = await service.analyze("AAPL")

        # Should still succeed with an empty research context
        assert isinstance(result, StockAnalysisResponse)
        assert result.research_context == ""
        assert result.research_sources == []

    @pytest.mark.asyncio
    async def test_research_section_injected_into_ai_prompt_when_present(
        self, mock_provider: AsyncMock, mock_market: AsyncMock
    ) -> None:
        """When research context is available it appears in the user_prompt
        forwarded to the AI provider."""
        sharepoint = AsyncMock()
        sharepoint.research_company = AsyncMock(
            return_value=("RESEARCH: key growth catalysts", [])
        )
        service = AIAnalysisService(
            provider=mock_provider,
            market_data=mock_market,
            sharepoint=sharepoint,
        )

        await service.analyze("AAPL")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "RESEARCH: key growth catalysts" in kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_research_section_absent_from_prompt_when_no_sharepoint(
        self, service: AIAnalysisService, mock_provider: AsyncMock
    ) -> None:
        """When no SharePoint provider is given, the 'RESEARCH CONTEXT' section
        header must not appear in the AI prompt."""
        await service.analyze("AAPL")

        _, kwargs = mock_provider.chat_completion_json.call_args
        assert "RESEARCH CONTEXT" not in kwargs["user_prompt"]


# ---------------------------------------------------------------------------
# _parse_long_term static method
# ---------------------------------------------------------------------------


class TestParseLongTerm:
    def test_returns_none_for_none_input(self) -> None:
        """None input returns None without raising."""
        assert AIAnalysisService._parse_long_term(None) is None

    def test_returns_none_for_empty_dict(self) -> None:
        """Empty dict is missing required keys so returns None."""
        assert AIAnalysisService._parse_long_term({}) is None

    def test_returns_none_for_non_dict_input(self) -> None:
        """Non-dict input (e.g. a string) returns None without raising."""
        assert AIAnalysisService._parse_long_term("not a dict") is None  # type: ignore[arg-type]

    def test_returns_none_for_list_input(self) -> None:
        """List input returns None (not a dict)."""
        assert AIAnalysisService._parse_long_term([1, 2, 3]) is None  # type: ignore[arg-type]

    def test_returns_none_when_required_forecast_key_missing(self) -> None:
        """Partial dict with missing 'one_year' key returns None."""
        partial: dict = {
            "five_year": {"low": 200.0, "mid": 300.0, "high": 400.0, "confidence": 0.5},
            "ten_year": {"low": 250.0, "mid": 450.0, "high": 650.0, "confidence": 0.4},
            "verdict": "buy",
        }
        assert AIAnalysisService._parse_long_term(partial) is None

    def test_returns_long_term_outlook_for_valid_full_data(self) -> None:
        """Full valid dict parses into a LongTermOutlook instance."""
        data = _MOCK_AI_RESPONSE["long_term_outlook"]
        result = AIAnalysisService._parse_long_term(data)

        assert isinstance(result, LongTermOutlook)
        assert result.verdict == "buy"
        assert result.compound_annual_return == pytest.approx(12.5)
        assert result.one_year.mid == pytest.approx(200.0)
        assert result.five_year.high == pytest.approx(400.0)
        assert result.ten_year.low == pytest.approx(250.0)

    def test_optional_fields_default_when_absent(self) -> None:
        """catalysts, long_term_risks, and verdict_rationale default to empty /
        empty string when absent from the dict."""
        data = {
            "one_year": {"low": 170.0, "mid": 200.0, "high": 230.0, "confidence": 0.7},
            "five_year": {"low": 200.0, "mid": 300.0, "high": 400.0, "confidence": 0.5},
            "ten_year": {"low": 250.0, "mid": 450.0, "high": 650.0, "confidence": 0.4},
            "verdict": "hold",
            "compound_annual_return": 8.0,
        }
        result = AIAnalysisService._parse_long_term(data)

        assert result is not None
        assert result.catalysts == []
        assert result.long_term_risks == []
        assert result.verdict_rationale == ""

    def test_compound_annual_return_defaults_to_zero_when_absent(self) -> None:
        """compound_annual_return defaults to 0.0 when not present in the dict."""
        data = {
            "one_year": {"low": 170.0, "mid": 200.0, "high": 230.0, "confidence": 0.7},
            "five_year": {"low": 200.0, "mid": 300.0, "high": 400.0, "confidence": 0.5},
            "ten_year": {"low": 250.0, "mid": 450.0, "high": 650.0, "confidence": 0.4},
            "verdict": "hold",
        }
        result = AIAnalysisService._parse_long_term(data)

        assert result is not None
        assert result.compound_annual_return == pytest.approx(0.0)
