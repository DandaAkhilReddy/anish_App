"""Pydantic models for unified stock analysis response."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TechnicalSnapshot(BaseModel):
    """AI-estimated technical indicator values."""

    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    support_levels: list[float] = []
    resistance_levels: list[float] = []
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = "neutral"


class NewsItem(BaseModel):
    """A single news headline from AI analysis."""

    title: str
    source: str | None = None
    sentiment: Literal["positive", "negative", "neutral"] | None = None


class QuarterlyEarning(BaseModel):
    """One quarter of earnings data."""

    quarter: str
    revenue: float | None = None
    net_income: float | None = None
    eps: float | None = None
    yoy_revenue_growth: float | None = None


class PriceForecast(BaseModel):
    """Low / mid / high price forecast with a confidence score."""

    low: float
    mid: float
    high: float
    confidence: float


class PricePredictions(BaseModel):
    """Forecasts across three time horizons."""

    one_week: PriceForecast
    one_month: PriceForecast
    three_months: PriceForecast


class RiskAssessment(BaseModel):
    """Qualitative and quantitative risk evaluation."""

    overall_risk: Literal["low", "medium", "high", "very_high"]
    risk_factors: list[str]
    risk_score: float


class LongTermOutlook(BaseModel):
    """Long-term investment outlook with multi-year projections."""

    one_year: PriceForecast
    five_year: PriceForecast
    ten_year: PriceForecast
    verdict: Literal["strong_buy", "buy", "hold", "sell", "strong_sell"]
    verdict_rationale: str
    catalysts: list[str] = []
    long_term_risks: list[str] = []
    compound_annual_return: float


class HistoricalPrice(BaseModel):
    """Single day OHLC price point for charting."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


class StockAnalysisResponse(BaseModel):
    """Full unified stock analysis — everything from one AI call."""

    model_config = ConfigDict(protected_namespaces=())

    # Quote data
    ticker: str
    company_name: str
    current_price: float
    previous_close: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    # Fundamentals
    market_cap: str | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    dividend_yield: float | None = None
    # Technical
    technical: TechnicalSnapshot | None = None
    # News
    news: list[NewsItem] = []
    quarterly_earnings: list[QuarterlyEarning] = []
    # Historical
    historical_prices: list[HistoricalPrice] = []
    # Company info
    company_description: str = ""
    sector: str = ""
    industry: str = ""
    headquarters: str = ""
    ceo: str = ""
    founded: str = ""
    employees: str = ""
    # AI Analysis
    recommendation: Literal["strong_buy", "buy", "hold", "sell", "strong_sell"]
    confidence_score: float
    summary: str
    bull_case: str
    bear_case: str
    risk_assessment: RiskAssessment
    price_predictions: PricePredictions
    long_term_outlook: LongTermOutlook | None = None
    # Research enrichment
    research_context: str = ""
    research_sources: list[str] = []
    # Metadata
    analysis_timestamp: datetime
    model_used: str = "gpt-5.3"
    disclaimer: str = (
        "Price data sourced from Financial Modeling Prep. "
        "Analysis and predictions are AI-generated — not financial advice."
    )
