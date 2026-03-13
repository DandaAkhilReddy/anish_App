export interface SearchResult {
  symbol: string;
  name: string;
}

export type Recommendation = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
export type RiskLevel = 'low' | 'medium' | 'high' | 'very_high';
export type TechnicalSignal = 'strong_buy' | 'buy' | 'neutral' | 'sell' | 'strong_sell';
export type Sentiment = 'positive' | 'negative' | 'neutral';

export interface TechnicalSnapshot {
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_12: number | null;
  ema_26: number | null;
  rsi_14: number | null;
  macd_line: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  bollinger_upper: number | null;
  bollinger_middle: number | null;
  bollinger_lower: number | null;
  support_levels: number[];
  resistance_levels: number[];
  signal: TechnicalSignal;
}

export interface NewsItem {
  title: string;
  source: string | null;
  sentiment: Sentiment | null;
}

export interface QuarterlyEarning {
  quarter: string;
  revenue: number | null;
  net_income: number | null;
  eps: number | null;
  yoy_revenue_growth: number | null;
}

export interface HistoricalPrice {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export type AnalysisTab = 'chart' | 'news' | 'financials' | 'about' | 'invest';

export interface PriceForecast {
  low: number;
  mid: number;
  high: number;
  confidence: number;
}

export interface PricePredictions {
  one_week: PriceForecast;
  one_month: PriceForecast;
  three_months: PriceForecast;
}

export interface LongTermOutlook {
  one_year: PriceForecast;
  five_year: PriceForecast;
  ten_year: PriceForecast;
  verdict: Recommendation;
  verdict_rationale: string;
  catalysts: string[];
  long_term_risks: string[];
  compound_annual_return: number;
}

export interface RiskAssessment {
  overall_risk: RiskLevel;
  risk_factors: string[];
  risk_score: number;
}

export interface StockAnalysisResponse {
  ticker: string;
  company_name: string;
  current_price: number;
  previous_close: number | null;
  open: number | null;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  market_cap: string | null;
  pe_ratio: number | null;
  eps: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  dividend_yield: number | null;
  technical: TechnicalSnapshot | null;
  news: NewsItem[];
  quarterly_earnings: QuarterlyEarning[];
  historical_prices: HistoricalPrice[];
  company_description: string;
  sector: string;
  industry: string;
  headquarters: string;
  ceo: string;
  founded: string;
  employees: string;
  recommendation: Recommendation;
  confidence_score: number;
  summary: string;
  bull_case: string;
  bear_case: string;
  risk_assessment: RiskAssessment;
  price_predictions: PricePredictions;
  long_term_outlook: LongTermOutlook | null;
  research_context: string;
  research_sources: string[];
  analysis_timestamp: string;
  model_used: string;
  disclaimer: string;
}
