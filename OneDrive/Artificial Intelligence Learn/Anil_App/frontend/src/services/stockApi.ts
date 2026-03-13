import { get, post } from './api';
import type { SearchResult, StockAnalysisResponse } from '../types/analysis';

export function searchStocks(query: string): Promise<SearchResult[]> {
  return get<SearchResult[]>(`/api/search?q=${encodeURIComponent(query)}`);
}

export function analyzeStock(ticker: string): Promise<StockAnalysisResponse> {
  return post<StockAnalysisResponse>(`/api/analyze/${encodeURIComponent(ticker)}`);
}
