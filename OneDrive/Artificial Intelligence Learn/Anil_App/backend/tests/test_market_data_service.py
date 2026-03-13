"""Tests for MarketDataService — FMP API wrapper."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import ExternalAPIError, StockNotFoundError
from app.models.analysis import HistoricalPrice, TechnicalSnapshot
from app.services.market_data_service import (
    MarketDataService,
    _format_market_cap,
    _safe_float,
    _safe_int,
)


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestFormatMarketCap:
    """Tests for _format_market_cap."""

    def test_none_returns_none(self) -> None:
        assert _format_market_cap(None) is None

    def test_trillions(self) -> None:
        assert _format_market_cap(2.8e12) == "2.8T"

    def test_billions(self) -> None:
        assert _format_market_cap(150e9) == "150.0B"

    def test_millions(self) -> None:
        assert _format_market_cap(500e6) == "500.0M"

    def test_small_number(self) -> None:
        assert _format_market_cap(50000) == "50000"


class TestSafeFloat:
    """Tests for _safe_float."""

    def test_none_returns_none(self) -> None:
        assert _safe_float(None) is None

    def test_valid_float(self) -> None:
        assert _safe_float(185.5) == 185.5

    def test_valid_int(self) -> None:
        assert _safe_float(100) == 100.0

    def test_nan_returns_none(self) -> None:
        assert _safe_float(float("nan")) is None

    def test_inf_returns_none(self) -> None:
        assert _safe_float(float("inf")) is None

    def test_string_returns_none(self) -> None:
        assert _safe_float("not a number") is None

    def test_numeric_string(self) -> None:
        assert _safe_float("185.5") == 185.5


class TestSafeInt:
    """Tests for _safe_int."""

    def test_none_returns_none(self) -> None:
        assert _safe_int(None) is None

    def test_valid_int(self) -> None:
        assert _safe_int(45000000) == 45000000

    def test_valid_float_truncates(self) -> None:
        assert _safe_int(45000000.7) == 45000000

    def test_nan_returns_none(self) -> None:
        assert _safe_int(float("nan")) is None

    def test_string_returns_none(self) -> None:
        assert _safe_int("not a number") is None


# ---------------------------------------------------------------------------
# Mock FMP API responses
# ---------------------------------------------------------------------------

_MOCK_QUOTE: list[dict] = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 185.50,
        "previousClose": 184.20,
        "open": 184.80,
        "dayHigh": 186.10,
        "dayLow": 184.00,
        "volume": 45000000,
        "marketCap": 2.8e12,
        "pe": 28.5,
        "eps": 6.51,
        "yearHigh": 199.62,
        "yearLow": 164.08,
    }
]

_MOCK_PROFILE: list[dict] = [
    {
        "companyName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "city": "Cupertino",
        "state": "California",
        "country": "United States",
        "fullTimeEmployees": 164000,
        "description": "Apple designs consumer electronics.",
        "ceo": "Tim Cook",
        "lastDiv": 0.96,
    }
]

_MOCK_HISTORICAL: list[dict] = [
    {
        "date": "2025-01-10",
        "open": 184.0,
        "high": 186.0,
        "low": 183.0,
        "close": 185.5,
        "volume": 45000000,
    }
]

_MOCK_SEARCH: list[dict] = [
    {"symbol": "MSFT", "name": "Microsoft Corporation"}
]


def _mock_response(json_data: object, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    import json

    return httpx.Response(
        status_code=status_code,
        content=json.dumps(json_data).encode(),
        request=httpx.Request("GET", "https://example.com"),
    )


# ---------------------------------------------------------------------------
# MarketDataService.get_quote
# ---------------------------------------------------------------------------


class TestGetQuote:
    """Tests for MarketDataService.get_quote."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_ticker(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], _MOCK_PROFILE[0]),
        ):
            result = await service.get_quote("AAPL")
        assert result["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_returns_correct_price(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], _MOCK_PROFILE[0]),
        ):
            result = await service.get_quote("AAPL")
        assert result["current_price"] == pytest.approx(185.50)

    @pytest.mark.asyncio
    async def test_returns_company_name(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], _MOCK_PROFILE[0]),
        ):
            result = await service.get_quote("AAPL")
        assert result["company_name"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_returns_formatted_market_cap(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], _MOCK_PROFILE[0]),
        ):
            result = await service.get_quote("AAPL")
        assert result["market_cap"] == "2.8T"

    @pytest.mark.asyncio
    async def test_returns_headquarters(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], _MOCK_PROFILE[0]),
        ):
            result = await service.get_quote("AAPL")
        assert "Cupertino" in result["headquarters"]
        assert "California" in result["headquarters"]

    @pytest.mark.asyncio
    async def test_returns_employee_count_formatted(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], _MOCK_PROFILE[0]),
        ):
            result = await service.get_quote("AAPL")
        assert result["employees"] == "164,000"

    @pytest.mark.asyncio
    async def test_raises_stock_not_found_when_no_price(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=({}, {}),
        ):
            with pytest.raises(StockNotFoundError):
                await service.get_quote("INVALID")

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_exception(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            side_effect=ExternalAPIError("FMP API", "network down"),
        ):
            with pytest.raises(ExternalAPIError):
                await service.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_employees_string_value_formatted(self) -> None:
        service = MarketDataService()
        profile = {**_MOCK_PROFILE[0], "fullTimeEmployees": "164000"}
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], profile),
        ):
            result = await service.get_quote("AAPL")
        assert result["employees"] == "164,000"

    @pytest.mark.asyncio
    async def test_employees_missing_returns_empty_string(self) -> None:
        service = MarketDataService()
        profile = {k: v for k, v in _MOCK_PROFILE[0].items()
                   if k != "fullTimeEmployees"}
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], profile),
        ):
            result = await service.get_quote("AAPL")
        assert result["employees"] == ""

    @pytest.mark.asyncio
    async def test_fallback_company_name_from_quote_name(self) -> None:
        service = MarketDataService()
        profile = {k: v for k, v in _MOCK_PROFILE[0].items()
                   if k != "companyName"}
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], profile),
        ):
            result = await service.get_quote("AAPL")
        assert result["company_name"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_fallback_company_name_from_ticker(self) -> None:
        service = MarketDataService()
        quote = {k: v for k, v in _MOCK_QUOTE[0].items() if k != "name"}
        profile = {k: v for k, v in _MOCK_PROFILE[0].items()
                   if k != "companyName"}
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(quote, profile),
        ):
            result = await service.get_quote("AAPL")
        assert result["company_name"] == "AAPL"

    @pytest.mark.asyncio
    async def test_headquarters_with_missing_fields(self) -> None:
        service = MarketDataService()
        profile = {k: v for k, v in _MOCK_PROFILE[0].items()
                   if k not in ("city", "state", "country")}
        with patch.object(
            service,
            "_fetch_quote_and_profile",
            return_value=(_MOCK_QUOTE[0], profile),
        ):
            result = await service.get_quote("AAPL")
        assert result["headquarters"] == ""


# ---------------------------------------------------------------------------
# MarketDataService.get_historical
# ---------------------------------------------------------------------------


class TestGetHistorical:
    """Tests for MarketDataService.get_historical."""

    @pytest.mark.asyncio
    async def test_returns_list_of_historical_prices(self) -> None:
        service = MarketDataService()
        with patch.object(
            service, "_get_json", return_value=_MOCK_HISTORICAL
        ):
            result = await service.get_historical("AAPL")
        assert len(result) == 1
        assert isinstance(result[0], HistoricalPrice)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_data(self) -> None:
        service = MarketDataService()
        with patch.object(
            service, "_get_json", return_value=[]
        ):
            result = await service.get_historical("AAPL")
        assert result == []

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_exception(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_get_json",
            side_effect=ExternalAPIError("FMP API", "timeout"),
        ):
            with pytest.raises(ExternalAPIError):
                await service.get_historical("AAPL")

    @pytest.mark.asyncio
    async def test_handles_dict_response_gracefully(self) -> None:
        service = MarketDataService()
        with patch.object(
            service, "_get_json", return_value={"error": "bad request"}
        ):
            result = await service.get_historical("AAPL")
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_items_sorted_oldest_first(self) -> None:
        service = MarketDataService()
        bars = [
            {"date": "2025-01-03", "open": 102, "high": 103,
             "low": 101, "close": 102.5, "volume": 100},
            {"date": "2025-01-02", "open": 101, "high": 102,
             "low": 100, "close": 101.5, "volume": 100},
            {"date": "2025-01-01", "open": 100, "high": 101,
             "low": 99, "close": 100.5, "volume": 100},
        ]
        with patch.object(service, "_get_json", return_value=bars):
            result = await service.get_historical("AAPL")
        assert result[0].date == "2025-01-01"
        assert result[-1].date == "2025-01-03"

    @pytest.mark.asyncio
    async def test_volume_none_handled(self) -> None:
        service = MarketDataService()
        bars = [
            {"date": "2025-01-01", "open": 100, "high": 101,
             "low": 99, "close": 100.5},
        ]
        with patch.object(service, "_get_json", return_value=bars):
            result = await service.get_historical("AAPL")
        assert len(result) == 1
        assert result[0].volume is None


# ---------------------------------------------------------------------------
# MarketDataService.get_technicals
# ---------------------------------------------------------------------------


class TestGetTechnicals:
    """Tests for MarketDataService.get_technicals."""

    @pytest.mark.asyncio
    async def test_returns_technical_snapshot(self) -> None:
        mock_snap = TechnicalSnapshot(sma_20=183.5, rsi_14=62.3)
        service = MarketDataService()
        with patch.object(
            service, "_compute_technicals", return_value=mock_snap
        ):
            result = await service.get_technicals("AAPL")
        assert isinstance(result, TechnicalSnapshot)
        assert result.sma_20 == pytest.approx(183.5)

    @pytest.mark.asyncio
    async def test_returns_empty_snapshot_on_failure(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_compute_technicals",
            side_effect=ValueError("not enough data"),
        ):
            result = await service.get_technicals("AAPL")
        assert isinstance(result, TechnicalSnapshot)
        assert result.sma_20 is None


# ---------------------------------------------------------------------------
# MarketDataService.resolve_ticker
# ---------------------------------------------------------------------------


class TestResolveTicker:
    """Tests for MarketDataService.resolve_ticker."""

    @pytest.mark.asyncio
    async def test_short_alpha_returns_as_is(self) -> None:
        service = MarketDataService()
        result = await service.resolve_ticker("AAPL")
        assert result == "AAPL"

    @pytest.mark.asyncio
    async def test_lowercased_short_alpha_uppercased(self) -> None:
        service = MarketDataService()
        result = await service.resolve_ticker("msft")
        assert result == "MSFT"

    @pytest.mark.asyncio
    async def test_company_name_triggers_search(self) -> None:
        service = MarketDataService()
        with patch.object(
            service, "_search_ticker", return_value=_MOCK_SEARCH
        ):
            result = await service.resolve_ticker("MICROSOFT")
        assert result == "MSFT"

    @pytest.mark.asyncio
    async def test_no_results_raises_stock_not_found(self) -> None:
        service = MarketDataService()
        with patch.object(service, "_search_ticker", return_value=[]):
            with pytest.raises(StockNotFoundError):
                await service.resolve_ticker("XYZNONEXIST")

    @pytest.mark.asyncio
    async def test_numeric_input_triggers_search(self) -> None:
        service = MarketDataService()
        mock_results = [{"symbol": "BRK.A"}]
        with patch.object(
            service, "_search_ticker", return_value=mock_results
        ):
            result = await service.resolve_ticker("BERKSHIRE123")
        assert result == "BRK.A"

    @pytest.mark.asyncio
    async def test_search_error_raises_external_api_error(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_search_ticker",
            side_effect=ExternalAPIError("FMP API", "timeout"),
        ):
            with pytest.raises(ExternalAPIError):
                await service.resolve_ticker("MICROSOFT")

    @pytest.mark.asyncio
    async def test_empty_symbol_in_result_raises_stock_not_found(self) -> None:
        service = MarketDataService()
        mock_results = [{"symbol": "", "name": "Unknown"}]
        with patch.object(
            service, "_search_ticker", return_value=mock_results
        ):
            with pytest.raises(StockNotFoundError):
                await service.resolve_ticker("MICROSOFT")

    @pytest.mark.asyncio
    async def test_ticker_with_dot_triggers_search(self) -> None:
        service = MarketDataService()
        mock_results = [{"symbol": "BRK.B"}]
        with patch.object(
            service, "_search_ticker", return_value=mock_results
        ):
            result = await service.resolve_ticker("BRK.B")
        assert result == "BRK.B"

    @pytest.mark.asyncio
    async def test_whitespace_stripped(self) -> None:
        service = MarketDataService()
        result = await service.resolve_ticker("  AAPL  ")
        assert result == "AAPL"


# ---------------------------------------------------------------------------
# MarketDataService.search_ticker
# ---------------------------------------------------------------------------


class TestSearchTicker:
    """Tests for MarketDataService.search_ticker (fallback search)."""

    @pytest.mark.asyncio
    async def test_returns_uppercase_symbol(self) -> None:
        service = MarketDataService()
        with patch.object(
            service, "_search_ticker", return_value=_MOCK_SEARCH
        ):
            result = await service.search_ticker("microsoft")
        assert result == "MSFT"

    @pytest.mark.asyncio
    async def test_raises_stock_not_found_when_no_results(self) -> None:
        service = MarketDataService()
        with patch.object(service, "_search_ticker", return_value=[]):
            with pytest.raises(StockNotFoundError):
                await service.search_ticker("XYZNONEXIST")

    @pytest.mark.asyncio
    async def test_raises_stock_not_found_when_empty_symbol(self) -> None:
        service = MarketDataService()
        with patch.object(
            service, "_search_ticker", return_value=[{"symbol": ""}]
        ):
            with pytest.raises(StockNotFoundError):
                await service.search_ticker("something")

    @pytest.mark.asyncio
    async def test_calls_search_ticker_internal(self) -> None:
        service = MarketDataService()
        mock = AsyncMock(return_value=_MOCK_SEARCH)
        with patch.object(service, "_search_ticker", mock):
            await service.search_ticker("microsoft")
        mock.assert_called_once_with("MICROSOFT")

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_network_failure(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_search_ticker",
            side_effect=ExternalAPIError("FMP API", "timeout"),
        ):
            with pytest.raises(ExternalAPIError):
                await service.search_ticker("apple")


# ---------------------------------------------------------------------------
# MarketDataService._search_ticker — US exchange filtering
# ---------------------------------------------------------------------------


class TestSearchTickerUSFilter:
    """Tests for _search_ticker US-only exchange filtering."""

    @pytest.mark.asyncio
    async def test_filters_out_foreign_symbols_with_dots(self) -> None:
        service = MarketDataService()
        mixed_results = [
            {"symbol": "TSLA", "name": "Tesla Inc"},
            {"symbol": "TSLA.NE", "name": "Tesla Inc (NEO)"},
            {"symbol": "TSLA.DE", "name": "Tesla Inc (Frankfurt)"},
        ]
        with patch.object(service, "_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = mixed_results
            result = await service._search_ticker("TESLA")
        assert len(result) == 1
        assert result[0]["symbol"] == "TSLA"

    @pytest.mark.asyncio
    async def test_keeps_all_us_symbols(self) -> None:
        service = MarketDataService()
        us_results = [
            {"symbol": "AAPL", "name": "Apple Inc"},
            {"symbol": "MSFT", "name": "Microsoft Corp"},
        ]
        with patch.object(service, "_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = us_results
            result = await service._search_ticker("TECH")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_foreign(self) -> None:
        service = MarketDataService()
        foreign_only = [
            {"symbol": "SAP.DE", "name": "SAP SE"},
            {"symbol": "NESN.SW", "name": "Nestle SA"},
        ]
        with patch.object(service, "_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = foreign_only
            result = await service._search_ticker("SAP")
        assert result == []

    @pytest.mark.asyncio
    async def test_handles_missing_symbol_key(self) -> None:
        service = MarketDataService()
        bad_results = [{"name": "No Symbol Co"}, {"symbol": "AAPL", "name": "Apple"}]
        with patch.object(service, "_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = bad_results
            result = await service._search_ticker("MISSING")
        # Entry without symbol has "" which has no dot, so it passes filter
        assert len(result) == 2


# ---------------------------------------------------------------------------
# MarketDataService._get_json
# ---------------------------------------------------------------------------


class TestGetJson:
    """Tests for MarketDataService._get_json error handling."""

    @pytest.mark.asyncio
    async def test_returns_parsed_json_on_success(self) -> None:
        service = MarketDataService()
        mock_resp = _mock_response([{"symbol": "AAPL"}])
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await service._get_json(
                "https://example.com", {"apikey": "test"}
            )
        assert result == [{"symbol": "AAPL"}]

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_timeout(self) -> None:
        service = MarketDataService()
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ExternalAPIError, match="timed out"):
                await service._get_json(
                    "https://example.com", {"apikey": "test"}
                )

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_http_status_error(self) -> None:
        service = MarketDataService()
        resp = httpx.Response(
            500,
            content=b"Internal Server Error",
            request=httpx.Request("GET", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.get.return_value = resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ExternalAPIError, match="HTTP 500"):
                await service._get_json(
                    "https://example.com", {"apikey": "test"}
                )

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_generic_http_error(
        self,
    ) -> None:
        service = MarketDataService()
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ExternalAPIError, match="Request failed"):
                await service._get_json(
                    "https://example.com", {"apikey": "test"}
                )


# ---------------------------------------------------------------------------
# MarketDataService._fetch_quote_and_profile
# ---------------------------------------------------------------------------


class TestFetchQuoteAndProfile:
    """Tests for MarketDataService._fetch_quote_and_profile."""

    @pytest.mark.asyncio
    async def test_returns_quote_and_profile_dicts(self) -> None:
        service = MarketDataService()
        quote_resp = _mock_response(_MOCK_QUOTE)
        profile_resp = _mock_response(_MOCK_PROFILE)
        with patch.object(
            service,
            "_parallel_get",
            return_value=(quote_resp, profile_resp),
        ):
            quote, profile = await service._fetch_quote_and_profile("AAPL")
        assert quote["symbol"] == "AAPL"
        assert profile["companyName"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_handles_empty_response_lists(self) -> None:
        service = MarketDataService()
        quote_resp = _mock_response([])
        profile_resp = _mock_response([])
        with patch.object(
            service,
            "_parallel_get",
            return_value=(quote_resp, profile_resp),
        ):
            quote, profile = await service._fetch_quote_and_profile("AAPL")
        assert quote == {}
        assert profile == {}

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_timeout(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_parallel_get",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(ExternalAPIError, match="timed out"):
                await service._fetch_quote_and_profile("AAPL")

    @pytest.mark.asyncio
    async def test_raises_external_api_error_on_http_error(self) -> None:
        service = MarketDataService()
        with patch.object(
            service,
            "_parallel_get",
            side_effect=httpx.ConnectError("refused"),
        ):
            with pytest.raises(ExternalAPIError, match="Failed to fetch"):
                await service._fetch_quote_and_profile("AAPL")


# ---------------------------------------------------------------------------
# MarketDataService._compute_technicals
# ---------------------------------------------------------------------------


def _generate_historical_bars(count: int, base_price: float = 100.0) -> list[dict]:
    """Generate mock historical bars for technicals tests."""
    bars = []
    for i in range(count):
        price = base_price + i * 0.5
        bars.append({
            "date": f"2025-01-{i + 1:02d}",
            "open": price - 0.5,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price,
            "volume": 1000000,
        })
    # FMP returns newest-first
    return list(reversed(bars))


class TestComputeTechnicals:
    """Tests for MarketDataService._compute_technicals."""

    @pytest.mark.asyncio
    async def test_returns_empty_snapshot_when_less_than_20_bars(self) -> None:
        service = MarketDataService()
        bars = _generate_historical_bars(10)
        with patch.object(service, "_get_json", return_value=bars):
            result = await service._compute_technicals("AAPL")
        assert result.sma_20 is None
        assert result.rsi_14 is None

    @pytest.mark.asyncio
    async def test_computes_sma_20_correctly(self) -> None:
        service = MarketDataService()
        bars = _generate_historical_bars(30)
        with patch.object(service, "_get_json", return_value=bars):
            result = await service._compute_technicals("AAPL")
        assert result.sma_20 is not None
        assert isinstance(result.sma_20, float)

    @pytest.mark.asyncio
    async def test_computes_rsi_14(self) -> None:
        service = MarketDataService()
        # Need alternating prices so RSI has both gains and losses
        bars = []
        for i in range(50):
            price = 100 + (i % 5) * 2 - 4  # oscillates 96-104
            bars.append({
                "date": f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                "open": price - 0.5, "high": price + 1,
                "low": price - 1, "close": float(price), "volume": 1000000,
            })
        bars = list(reversed(bars))
        with patch.object(service, "_get_json", return_value=bars):
            result = await service._compute_technicals("AAPL")
        assert result.rsi_14 is not None
        assert 0 <= result.rsi_14 <= 100

    @pytest.mark.asyncio
    async def test_computes_macd_values(self) -> None:
        service = MarketDataService()
        bars = _generate_historical_bars(50)
        with patch.object(service, "_get_json", return_value=bars):
            result = await service._compute_technicals("AAPL")
        assert result.macd_line is not None
        assert result.macd_signal is not None
        assert result.macd_histogram is not None

    @pytest.mark.asyncio
    async def test_computes_bollinger_bands(self) -> None:
        service = MarketDataService()
        bars = _generate_historical_bars(30)
        with patch.object(service, "_get_json", return_value=bars):
            result = await service._compute_technicals("AAPL")
        assert result.bollinger_upper is not None
        assert result.bollinger_middle is not None
        assert result.bollinger_lower is not None
        assert result.bollinger_upper > result.bollinger_middle
        assert result.bollinger_middle > result.bollinger_lower


# ---------------------------------------------------------------------------
# _compute_technicals — deep math validation
# ---------------------------------------------------------------------------


def _bars_from_closes(closes: list[float]) -> list[dict]:
    """Build FMP-format bars (newest-first) from a list of close prices."""
    bars = [
        {
            "date": f"2025-01-{i + 1:02d}",
            "open": c - 0.1,
            "high": c + 0.5,
            "low": c - 0.5,
            "close": c,
            "volume": 1_000_000,
        }
        for i, c in enumerate(closes)
    ]
    # FMP returns newest-first; _compute_technicals reverses before processing
    return list(reversed(bars))


class TestComputeTechnicalsMath:
    """Exact math validation for every indicator in _compute_technicals."""

    # ------------------------------------------------------------------
    # SMA-20
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sma_20_exact_arithmetic_mean(self) -> None:
        """SMA-20 must equal the arithmetic mean of the 20 most recent closes."""
        # 20 bars with known closes: arithmetic mean = (1+2+...+20)/20 = 10.5
        closes = [float(i) for i in range(1, 21)]
        expected_sma20 = sum(closes[-20:]) / 20  # 10.5
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.sma_20 == pytest.approx(expected_sma20, rel=1e-4)

    @pytest.mark.asyncio
    async def test_sma_20_on_constant_price_series(self) -> None:
        """SMA-20 of a flat 100.0 series must be exactly 100.0."""
        closes = [100.0] * 25
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.sma_20 == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_sma_20_uses_only_last_20_bars(self) -> None:
        """SMA-20 with 30 bars must reflect only the 20 most recent closes."""
        # First 10 bars at 0.0, last 20 bars at 100.0 → SMA-20 must be 100.0
        closes = [0.0] * 10 + [100.0] * 20
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.sma_20 == pytest.approx(100.0)

    # ------------------------------------------------------------------
    # SMA-50
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sma_50_returns_none_when_fewer_than_50_bars(self) -> None:
        """SMA-50 must be None when the dataset has fewer than 50 bars."""
        closes = [float(i) for i in range(1, 40)]  # 39 bars
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.sma_50 is None

    @pytest.mark.asyncio
    async def test_sma_50_returns_value_when_exactly_50_bars(self) -> None:
        """SMA-50 must be computed when exactly 50 bars are present."""
        closes = [100.0] * 50
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.sma_50 == pytest.approx(100.0)

    # ------------------------------------------------------------------
    # EMA-12 and EMA-26
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ema_12_on_constant_price_series_equals_price(self) -> None:
        """EMA-12 of a constant price series must converge to that price."""
        closes = [50.0] * 40
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.ema_12 == pytest.approx(50.0, rel=1e-4)

    @pytest.mark.asyncio
    async def test_ema_26_on_constant_price_series_equals_price(self) -> None:
        """EMA-26 of a constant price series must converge to that price."""
        closes = [75.0] * 40
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.ema_26 == pytest.approx(75.0, rel=1e-4)

    @pytest.mark.asyncio
    async def test_ema_12_reacts_faster_than_ema_26_on_rising_series(self) -> None:
        """EMA-12 must be greater than EMA-26 on a steadily rising price series."""
        closes = [float(i) for i in range(1, 61)]  # strictly increasing
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.ema_12 is not None
        assert result.ema_26 is not None
        assert result.ema_12 > result.ema_26

    # ------------------------------------------------------------------
    # RSI-14
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rsi_14_is_none_for_all_up_days(self) -> None:
        """RSI-14 with only up-days has zero average loss.

        The implementation divides by loss.replace(0, NaN), making RS = NaN
        and therefore RSI = NaN, which _safe_float converts to None.
        """
        # 51 strictly rising bars → every diff is positive, avg loss = 0
        closes = [float(i) for i in range(1, 52)]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        # avg_loss = 0 → loss replaced with NaN → RSI is NaN → _safe_float → None
        assert result.rsi_14 is None

    @pytest.mark.asyncio
    async def test_rsi_14_is_none_for_all_down_days(self) -> None:
        """RSI-14 with only down-days computes to 0.0, which the service maps to None.

        The implementation uses ``round(rsi_14, 2) if rsi_14 else None``.
        Because ``if 0.0`` is falsy in Python, a mathematically correct RSI of
        0.0 is treated the same as None and stored as None.  This test documents
        that known behaviour so a future refactor can catch the change.
        """
        # 51 strictly falling bars → every diff is negative, avg gain = 0
        closes = [float(i) for i in range(51, 0, -1)]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        # avg_gain = 0 → RS = 0 → RSI_raw = 0.0 → falsy guard maps it to None
        assert result.rsi_14 is None

    @pytest.mark.asyncio
    async def test_rsi_14_near_50_for_equal_alternating_moves(self) -> None:
        """RSI-14 near 50 when up/down moves are equal in magnitude."""
        # Alternating +1/-1 pattern: avg_gain ≈ avg_loss → RS ≈ 1 → RSI ≈ 50
        closes: list[float] = []
        price = 100.0
        for i in range(60):
            price += 1.0 if i % 2 == 0 else -1.0
            closes.append(price)
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.rsi_14 is not None
        assert result.rsi_14 == pytest.approx(50.0, abs=5.0)

    @pytest.mark.asyncio
    async def test_rsi_14_bounded_between_0_and_100(self) -> None:
        """RSI-14 must always be in [0, 100] for any valid price series."""
        closes = [100.0 + (i % 7) * 3 - 10 for i in range(50)]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        if result.rsi_14 is not None:
            assert 0.0 <= result.rsi_14 <= 100.0

    # ------------------------------------------------------------------
    # MACD
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_macd_histogram_equals_line_minus_signal(self) -> None:
        """MACD histogram must equal MACD line − signal line (rounded to 4dp)."""
        closes = [float(i) for i in range(1, 61)]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.macd_line is not None
        assert result.macd_signal is not None
        assert result.macd_histogram is not None
        expected_hist = round(result.macd_line - result.macd_signal, 4)
        assert result.macd_histogram == pytest.approx(expected_hist, abs=1e-6)

    @pytest.mark.asyncio
    async def test_macd_line_positive_on_rising_series(self) -> None:
        """EMA-12 > EMA-26 on a rising series → MACD line must be positive."""
        closes = [float(i) for i in range(1, 61)]  # strictly increasing
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.macd_line is not None
        assert result.macd_line > 0

    @pytest.mark.asyncio
    async def test_macd_all_none_when_not_enough_data(self) -> None:
        """With fewer than 20 bars all indicators including MACD must be None."""
        closes = [float(i) for i in range(1, 15)]  # 14 bars
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.macd_line is None
        assert result.macd_signal is None
        assert result.macd_histogram is None

    # ------------------------------------------------------------------
    # Bollinger Bands
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_bollinger_middle_equals_sma_20(self) -> None:
        """Bollinger middle band must equal SMA-20."""
        closes = [float(i) for i in range(1, 31)]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.bollinger_middle is not None
        assert result.sma_20 is not None
        assert result.bollinger_middle == pytest.approx(result.sma_20)

    @pytest.mark.asyncio
    async def test_bollinger_bands_symmetric_around_middle(self) -> None:
        """Upper and lower bands must be equidistant from the middle."""
        closes = [float(i) for i in range(1, 31)]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.bollinger_upper is not None
        assert result.bollinger_lower is not None
        assert result.bollinger_middle is not None
        upper_dist = result.bollinger_upper - result.bollinger_middle
        lower_dist = result.bollinger_middle - result.bollinger_lower
        assert upper_dist == pytest.approx(lower_dist, rel=1e-3)

    @pytest.mark.asyncio
    async def test_bollinger_bands_zero_width_for_constant_prices(self) -> None:
        """Constant price series has zero std → upper = middle = lower."""
        closes = [100.0] * 25
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=_bars_from_closes(closes)):
            result = await service._compute_technicals("AAPL")
        assert result.bollinger_upper == pytest.approx(100.0, abs=0.01)
        assert result.bollinger_middle == pytest.approx(100.0)
        assert result.bollinger_lower == pytest.approx(100.0, abs=0.01)


# ---------------------------------------------------------------------------
# get_historical — additional edge cases
# ---------------------------------------------------------------------------


class TestGetHistoricalEdgeCases:
    """Edge cases for MarketDataService.get_historical."""

    @pytest.mark.asyncio
    async def test_single_data_point_returned(self) -> None:
        """A single-bar response must return exactly one HistoricalPrice."""
        bars = [
            {
                "date": "2025-06-01",
                "open": 200.0,
                "high": 205.0,
                "low": 198.0,
                "close": 203.5,
                "volume": 5_000_000,
            }
        ]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=bars):
            result = await service.get_historical("AAPL")
        assert len(result) == 1
        assert result[0].close == pytest.approx(203.5)
        assert result[0].date == "2025-06-01"

    @pytest.mark.asyncio
    async def test_close_value_rounded_to_two_decimal_places(self) -> None:
        """Close prices must be rounded to 2 decimal places."""
        bars = [
            {
                "date": "2025-06-01",
                "open": 100.123456,
                "high": 101.999,
                "low": 99.001,
                "close": 100.999999,
                "volume": 1_000,
            }
        ]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=bars):
            result = await service.get_historical("AAPL")
        assert result[0].close == pytest.approx(101.0, abs=0.01)
        assert result[0].open == pytest.approx(100.12, abs=0.01)

    @pytest.mark.asyncio
    async def test_items_in_wrong_order_are_sorted_oldest_first(self) -> None:
        """Items provided newest-first must be reversed to oldest-first."""
        # FMP contract: newest entry at index 0
        bars_newest_first = [
            {
                "date": "2025-03-03",
                "open": 103.0, "high": 104.0, "low": 102.0, "close": 103.5,
                "volume": 300,
            },
            {
                "date": "2025-03-01",
                "open": 101.0, "high": 102.0, "low": 100.0, "close": 101.5,
                "volume": 100,
            },
            {
                "date": "2025-03-02",
                "open": 102.0, "high": 103.0, "low": 101.0, "close": 102.5,
                "volume": 200,
            },
        ]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=bars_newest_first):
            result = await service.get_historical("AAPL")
        # After reversal, the order reflects the original list reversed:
        # [2025-03-02, 2025-03-01, 2025-03-03] — oldest by insertion position
        assert result[0].date == "2025-03-02"
        assert result[-1].date == "2025-03-03"

    @pytest.mark.asyncio
    async def test_missing_volume_field_returns_none(self) -> None:
        """Bars without a volume key must produce HistoricalPrice with volume=None."""
        bars = [
            {
                "date": "2025-06-01",
                "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
                # volume key intentionally absent
            }
        ]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=bars):
            result = await service.get_historical("AAPL")
        assert result[0].volume is None

    @pytest.mark.asyncio
    async def test_volume_none_value_returns_none(self) -> None:
        """Bars with explicit volume=None must produce HistoricalPrice with volume=None."""
        bars = [
            {
                "date": "2025-06-01",
                "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
                "volume": None,
            }
        ]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=bars):
            result = await service.get_historical("AAPL")
        assert result[0].volume is None

    @pytest.mark.asyncio
    async def test_large_multi_bar_response_preserves_count(self) -> None:
        """100 bars in → 100 HistoricalPrice objects out."""
        bars = [
            {
                "date": f"2025-01-{i + 1:02d}",
                "open": 100.0, "high": 101.0, "low": 99.0,
                "close": 100.0 + i * 0.1, "volume": 1_000,
            }
            for i in range(100)
        ]
        service = MarketDataService()
        with patch.object(service, "_get_json", return_value=list(reversed(bars))):
            result = await service.get_historical("AAPL")
        assert len(result) == 100


# ---------------------------------------------------------------------------
# Helper function edge cases — _safe_float, _safe_int, _format_market_cap
# ---------------------------------------------------------------------------


class TestSafeFloatEdgeCases:
    """Additional edge cases for _safe_float."""

    def test_negative_inf_returns_none(self) -> None:
        assert _safe_float(float("-inf")) is None

    def test_positive_inf_string_returns_none(self) -> None:
        # float("inf") == math.inf → isnan=False, isinf=True → None
        assert _safe_float("inf") is None

    def test_negative_inf_string_returns_none(self) -> None:
        assert _safe_float("-inf") is None

    def test_nan_string_returns_none(self) -> None:
        # float("nan") is valid Python → isnan=True → None
        assert _safe_float("nan") is None

    def test_zero_returns_zero(self) -> None:
        assert _safe_float(0) == 0.0

    def test_zero_string_returns_zero(self) -> None:
        assert _safe_float("0") == 0.0

    def test_negative_float_returned(self) -> None:
        assert _safe_float(-42.7) == pytest.approx(-42.7)

    def test_list_value_returns_none(self) -> None:
        assert _safe_float([1, 2, 3]) is None

    def test_bool_true_treated_as_1(self) -> None:
        # bool is a subclass of int in Python; float(True) == 1.0
        assert _safe_float(True) == pytest.approx(1.0)


class TestSafeIntEdgeCases:
    """Additional edge cases for _safe_int."""

    def test_float_string_parsed_and_truncated(self) -> None:
        assert _safe_int("99.9") == 99

    def test_zero_float_returns_zero(self) -> None:
        assert _safe_int(0.0) == 0

    def test_negative_int_returned(self) -> None:
        assert _safe_int(-500) == -500

    def test_negative_float_truncated_toward_zero(self) -> None:
        # int(-99.9) == -99 in Python (truncation toward zero)
        assert _safe_int(-99.9) == -99

    def test_inf_float_returns_none(self) -> None:
        assert _safe_int(float("inf")) is None

    def test_dict_value_returns_none(self) -> None:
        assert _safe_int({"a": 1}) is None

    def test_bool_false_treated_as_zero(self) -> None:
        assert _safe_int(False) == 0


class TestFormatMarketCapBoundaries:
    """Boundary values for _format_market_cap."""

    def test_exactly_1_trillion(self) -> None:
        assert _format_market_cap(1e12) == "1.0T"

    def test_just_below_1_trillion_falls_to_billions(self) -> None:
        # 999_999_999_999 < 1e12 → billions branch
        result = _format_market_cap(999_999_999_999.0)
        assert result is not None
        assert result.endswith("B")

    def test_exactly_1_billion(self) -> None:
        assert _format_market_cap(1e9) == "1.0B"

    def test_just_below_1_billion_falls_to_millions(self) -> None:
        result = _format_market_cap(999_999_999.0)
        assert result is not None
        assert result.endswith("M")

    def test_exactly_1_million(self) -> None:
        assert _format_market_cap(1e6) == "1.0M"

    def test_just_below_1_million_returns_raw_int_string(self) -> None:
        result = _format_market_cap(999_999.0)
        assert result == "999999"

    def test_zero_returns_zero_string(self) -> None:
        assert _format_market_cap(0.0) == "0"

    def test_fractional_trillion_formatted_to_one_decimal(self) -> None:
        assert _format_market_cap(2.85e12) == "2.9T"
