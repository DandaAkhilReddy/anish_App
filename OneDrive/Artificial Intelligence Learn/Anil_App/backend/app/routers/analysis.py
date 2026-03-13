"""Router for AI-powered stock analysis."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.logging import get_logger
from app.models.analysis import StockAnalysisResponse
from app.providers.sharepoint_agent import SharePointAgentProvider
from app.services.ai_analysis_service import AIAnalysisService
from app.services.market_data_service import MarketDataService

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])

_market_service = MarketDataService()
_sharepoint = (
    SharePointAgentProvider() if settings.sharepoint_agent_endpoint else None
)
_ai_service = AIAnalysisService(
    market_data=_market_service, sharepoint=_sharepoint
)


@router.get("/search")
async def search_stocks(
    q: str = Query(min_length=1, max_length=100),
) -> list[dict[str, str]]:
    """Return stock search suggestions for autocomplete.

    Args:
        q: Search query (ticker or company name fragment).

    Returns:
        List of {symbol, name} dicts matching the query.
    """
    return await _market_service.search_suggestions(q)


@router.post("/analyze/{ticker}", response_model=StockAnalysisResponse)
async def analyze_stock(ticker: str) -> StockAnalysisResponse:
    """Run comprehensive stock analysis.

    Fetches real market data from Financial Modeling Prep, then uses AI
    for qualitative analysis (recommendation, news, predictions).
    """
    logger.info("analysis_request", ticker=ticker)
    result = await _ai_service.analyze(ticker)
    logger.info("analysis_complete", ticker=ticker, recommendation=result.recommendation)
    return result
