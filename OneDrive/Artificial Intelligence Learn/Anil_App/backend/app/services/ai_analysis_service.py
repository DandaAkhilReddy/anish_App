"""AI analysis service — two-phase: real market data + AI qualitative analysis."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.exceptions import AIAnalysisError, ExternalAPIError, StockNotFoundError
from app.core.logging import get_logger
from app.models.analysis import (
    HistoricalPrice,
    LongTermOutlook,
    NewsItem,
    PriceForecast,
    PricePredictions,
    QuarterlyEarning,
    RiskAssessment,
    StockAnalysisResponse,
    TechnicalSnapshot,
)
from app.providers.openai_provider import OpenAIProvider
from app.providers.sharepoint_agent import SharePointAgentProvider
from app.services.market_data_service import MarketDataService

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a senior equity research analyst. You will be given REAL "
    "current market data for a stock. Your job is to provide qualitative "
    "analysis only.\n\n"
    "IMPORTANT: If the user provides a company name, misspelling, or "
    "informal name instead of a valid ticker symbol, you MUST identify "
    "the correct official ticker symbol (e.g., 'microsft' → 'MSFT', "
    "'apple' → 'AAPL', 'google' → 'GOOGL').\n\n"
    "Do NOT invent or override any price data — it is provided to you "
    "from real market data.\n\n"
    "Respond in valid JSON matching the exact schema provided. "
    "No markdown, no code blocks, just raw JSON."
)

_USER_PROMPT_TEMPLATE = """Analyze the stock: {ticker} ({company_name})

=== REAL MARKET DATA (do NOT override) ===
Current Price: ${current_price}
Previous Close: ${previous_close}
Day Range: ${day_low} – ${day_high}
52-Week Range: ${week_52_low} – ${week_52_high}
Volume: {volume}
Market Cap: {market_cap}
P/E Ratio: {pe_ratio} | EPS: ${eps}

Technical Indicators (computed from real data):
  SMA-20: {sma_20} | SMA-50: {sma_50} | SMA-200: {sma_200}
  RSI-14: {rsi_14}
  MACD: {macd_line} | Signal: {macd_signal}

{research_section}
Based on the above real data, provide your qualitative analysis as JSON:
{{
  "recommendation": "strong_buy" | "buy" | "hold" | "sell" | "strong_sell",
  "confidence_score": <float 0.0-1.0>,
  "summary": "<2-3 sentence analysis summary>",
  "bull_case": "<paragraph explaining bullish thesis>",
  "bear_case": "<paragraph explaining bearish thesis>",
  "risk_assessment": {{
    "overall_risk": "low" | "medium" | "high" | "very_high",
    "risk_factors": ["<factor 1>", "<factor 2>", ...],
    "risk_score": <float 0.0-1.0>
  }},
  "price_predictions": {{
    "one_week": {{"low": <float>, "mid": <float>, "high": <float>, "confidence": <float>}},
    "one_month": {{"low": <float>, "mid": <float>, "high": <float>, "confidence": <float>}},
    "three_months": {{"low": <float>, "mid": <float>, "high": <float>, "confidence": <float>}}
  }},
  "news": [
    {{"title": "<headline>", "source": "<source name>", "sentiment": "positive" | "negative" | "neutral"}},
    ... (5-10 recent headlines)
  ],
  "quarterly_earnings": [
    {{"quarter": "<e.g. Q1 2025>", "revenue": <float in millions USD or null>, "net_income": <float in millions USD or null>, "eps": <float or null>, "yoy_revenue_growth": <float as decimal like 0.12 for 12% or null>}},
    ... (last 4 reported quarters, most recent first)
  ],
  "long_term_outlook": {{
    "one_year": {{"low": <float>, "mid": <float>, "high": <float>, "confidence": <float 0-1>}},
    "five_year": {{"low": <float>, "mid": <float>, "high": <float>, "confidence": <float 0-1>}},
    "ten_year": {{"low": <float>, "mid": <float>, "high": <float>, "confidence": <float 0-1>}},
    "verdict": "strong_buy" | "buy" | "hold" | "sell" | "strong_sell",
    "verdict_rationale": "<2-3 sentences: why this stock is or isn't a good long-term hold>",
    "catalysts": ["<growth driver 1>", "<growth driver 2>", ...up to 5],
    "long_term_risks": ["<risk 1>", "<risk 2>", ...up to 5],
    "compound_annual_return": <estimated CAGR as percent e.g. 12.5>
  }},
  "support_levels": [<float>, ...],
  "resistance_levels": [<float>, ...],
  "signal": "strong_buy" | "buy" | "neutral" | "sell" | "strong_sell",
  "ceo": "<current CEO name>",
  "founded": "<e.g. 1976>"
}}"""


class AIAnalysisService:
    """Two-phase stock analysis: real market data + AI qualitative."""

    def __init__(
        self,
        provider: OpenAIProvider | None = None,
        market_data: MarketDataService | None = None,
        sharepoint: SharePointAgentProvider | None = None,
    ) -> None:
        """Initialise with an OpenAI provider, market data, and research agent.

        Args:
            provider: An ``OpenAIProvider`` instance.
            market_data: A ``MarketDataService`` for real prices.
            sharepoint: Optional ``SharePointAgentProvider`` for research.
        """
        self._provider = provider or OpenAIProvider()
        self._market = market_data or MarketDataService()
        self._sharepoint = sharepoint

    async def analyze(self, ticker: str) -> StockAnalysisResponse:
        """Run two-phase analysis: real data fetch + AI qualitative.

        Args:
            ticker: Stock ticker symbol or company name.

        Returns:
            Complete stock analysis response with real prices.

        Raises:
            AIAnalysisError: If the AI call or data fetch fails.
        """
        ticker = ticker.upper().strip()
        logger.info("analysis_starting", ticker=ticker)

        # Phase 0: Resolve company name → ticker symbol
        ticker = await self._market.resolve_ticker(ticker)

        # Phase 1: Fetch real market data (quote + history + technicals)
        try:
            quote, history, technicals = await asyncio.gather(
                self._market.get_quote(ticker),
                self._market.get_historical(ticker, period="6mo"),
                self._market.get_technicals(ticker, period="1y"),
            )
        except (StockNotFoundError, ExternalAPIError):
            # Fast-path ticker guess failed — fall back to search
            ticker = await self._market.search_ticker(ticker)
            try:
                quote, history, technicals = await asyncio.gather(
                    self._market.get_quote(ticker),
                    self._market.get_historical(ticker, period="6mo"),
                    self._market.get_technicals(ticker, period="1y"),
                )
            except (StockNotFoundError, ExternalAPIError):
                raise
            except Exception as exc:
                raise AIAnalysisError(
                    f"Failed to fetch market data for {ticker}: {exc}"
                ) from exc
        except Exception as exc:
            logger.error(
                "market_data_fetch_failed",
                ticker=ticker,
                error=str(exc),
            )
            raise AIAnalysisError(
                f"Failed to fetch market data for {ticker}: {exc}"
            ) from exc

        # Use resolved ticker from FMP
        resolved_ticker = quote.get("ticker", ticker)

        # Phase 1.5: Research enrichment (non-blocking)
        research_context = ""
        research_sources: list[str] = []
        if self._sharepoint:
            try:
                research_context, research_sources = (
                    await self._sharepoint.research_company(
                        resolved_ticker,
                        quote.get("company_name", resolved_ticker),
                    )
                )
            except Exception as exc:
                logger.warning(
                    "sharepoint_research_failed",
                    ticker=resolved_ticker,
                    error=str(exc),
                )

        # Phase 2: AI qualitative analysis with real data context
        research_section = ""
        if research_context:
            research_section = (
                "\n=== RESEARCH CONTEXT (from web search) ===\n"
                f"{research_context}\n"
            )

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            ticker=resolved_ticker,
            company_name=quote.get("company_name", resolved_ticker),
            current_price=quote["current_price"],
            previous_close=quote.get("previous_close") or "N/A",
            day_low=quote.get("day_low") or "N/A",
            day_high=quote.get("day_high") or "N/A",
            week_52_low=quote.get("week_52_low") or "N/A",
            week_52_high=quote.get("week_52_high") or "N/A",
            volume=f"{quote['volume']:,}" if quote.get("volume") else "N/A",
            market_cap=quote.get("market_cap") or "N/A",
            pe_ratio=quote.get("pe_ratio") or "N/A",
            eps=quote.get("eps") or "N/A",
            sma_20=technicals.sma_20 or "N/A",
            sma_50=technicals.sma_50 or "N/A",
            sma_200=technicals.sma_200 or "N/A",
            rsi_14=technicals.rsi_14 or "N/A",
            macd_line=technicals.macd_line or "N/A",
            macd_signal=technicals.macd_signal or "N/A",
            research_section=research_section,
        )

        try:
            ai_result = await self._provider.chat_completion_json(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=8000,
            )
        except AIAnalysisError:
            raise
        except Exception as exc:
            logger.error(
                "ai_analysis_failed", ticker=ticker, error=str(exc)
            )
            raise AIAnalysisError(str(exc)) from exc

        # Phase 3: Merge real data + AI qualitative
        response = self._merge_response(
            resolved_ticker, quote, history, technicals, ai_result,
            research_context=research_context,
            research_sources=research_sources,
        )
        logger.info(
            "analysis_complete",
            ticker=resolved_ticker,
            recommendation=response.recommendation,
        )
        return response

    def _merge_response(
        self,
        ticker: str,
        quote: dict,
        history: list[HistoricalPrice],
        technicals: TechnicalSnapshot,
        ai_data: dict,
        research_context: str = "",
        research_sources: list[str] | None = None,
    ) -> StockAnalysisResponse:
        """Merge real market data with AI qualitative analysis.

        Args:
            ticker: Resolved ticker symbol.
            quote: Real quote data from FMP.
            history: Real historical OHLC data.
            technicals: Computed technical indicators.
            ai_data: Qualitative analysis from AI.
            research_context: Research text from SharePoint agent.
            research_sources: URLs consulted by the research agent.

        Returns:
            Fully populated ``StockAnalysisResponse``.

        Raises:
            AIAnalysisError: If required AI fields are missing.
        """
        logger.debug(
            "merging_response", ticker=ticker, ai_keys=list(ai_data.keys())
        )
        try:
            # Merge AI support/resistance into technicals
            support = ai_data.get("support_levels", [])
            resistance = ai_data.get("resistance_levels", [])
            signal = ai_data.get("signal", technicals.signal)

            merged_technical = TechnicalSnapshot(
                sma_20=technicals.sma_20,
                sma_50=technicals.sma_50,
                sma_200=technicals.sma_200,
                ema_12=technicals.ema_12,
                ema_26=technicals.ema_26,
                rsi_14=technicals.rsi_14,
                macd_line=technicals.macd_line,
                macd_signal=technicals.macd_signal,
                macd_histogram=technicals.macd_histogram,
                bollinger_upper=technicals.bollinger_upper,
                bollinger_middle=technicals.bollinger_middle,
                bollinger_lower=technicals.bollinger_lower,
                support_levels=[float(s) for s in support],
                resistance_levels=[float(r) for r in resistance],
                signal=signal,
            )

            news = [
                NewsItem(**n) for n in ai_data.get("news", [])
            ]
            earnings = [
                QuarterlyEarning(**e)
                for e in ai_data.get("quarterly_earnings", [])
            ]

            predictions_data = ai_data.get("price_predictions", {})
            risk_data = ai_data.get("risk_assessment", {})

            return StockAnalysisResponse(
                # Real data from yfinance
                ticker=ticker,
                company_name=quote.get("company_name", ticker),
                current_price=quote["current_price"],
                previous_close=quote.get("previous_close"),
                open=quote.get("open"),
                day_high=quote.get("day_high"),
                day_low=quote.get("day_low"),
                volume=quote.get("volume"),
                market_cap=quote.get("market_cap"),
                pe_ratio=quote.get("pe_ratio"),
                eps=quote.get("eps"),
                week_52_high=quote.get("week_52_high"),
                week_52_low=quote.get("week_52_low"),
                dividend_yield=quote.get("dividend_yield"),
                historical_prices=history,
                technical=merged_technical,
                # Company info from yfinance
                company_description=quote.get("company_description", ""),
                sector=quote.get("sector", ""),
                industry=quote.get("industry", ""),
                headquarters=quote.get("headquarters", ""),
                ceo=ai_data.get("ceo", ""),
                founded=ai_data.get("founded", ""),
                employees=quote.get("employees", ""),
                # AI qualitative analysis
                news=news,
                quarterly_earnings=earnings,
                recommendation=ai_data["recommendation"],
                confidence_score=float(ai_data["confidence_score"]),
                summary=ai_data["summary"],
                bull_case=ai_data["bull_case"],
                bear_case=ai_data["bear_case"],
                risk_assessment=RiskAssessment(
                    overall_risk=risk_data["overall_risk"],
                    risk_factors=risk_data.get("risk_factors", []),
                    risk_score=float(risk_data.get("risk_score", 0.5)),
                ),
                price_predictions=PricePredictions(
                    one_week=PriceForecast(
                        **predictions_data["one_week"]
                    ),
                    one_month=PriceForecast(
                        **predictions_data["one_month"]
                    ),
                    three_months=PriceForecast(
                        **predictions_data["three_months"]
                    ),
                ),
                long_term_outlook=self._parse_long_term(
                    ai_data.get("long_term_outlook")
                ),
                research_context=research_context,
                research_sources=research_sources or [],
                analysis_timestamp=datetime.now(timezone.utc),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.error(
                "response_merge_error",
                ticker=ticker,
                error=str(exc),
                ai_data=str(ai_data)[:500],
            )
            raise AIAnalysisError(
                f"Failed to parse AI response: {exc}"
            ) from exc

    @staticmethod
    def _parse_long_term(
        data: dict | None,
    ) -> LongTermOutlook | None:
        """Parse long-term outlook from AI response, returning None on failure."""
        if not data or not isinstance(data, dict):
            return None
        try:
            return LongTermOutlook(
                one_year=PriceForecast(**data["one_year"]),
                five_year=PriceForecast(**data["five_year"]),
                ten_year=PriceForecast(**data["ten_year"]),
                verdict=data["verdict"],
                verdict_rationale=data.get("verdict_rationale", ""),
                catalysts=data.get("catalysts", []),
                long_term_risks=data.get("long_term_risks", []),
                compound_annual_return=float(
                    data.get("compound_annual_return", 0)
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "long_term_outlook_parse_failed", error=str(exc)
            )
            return None
