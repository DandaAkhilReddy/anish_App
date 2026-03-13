import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { StockAnalysisResponse, AnalysisTab } from '../types/analysis';
import { analyzeStock } from '../services/stockApi';

interface StockState {
  currentTicker: string | null;
  analysis: StockAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  activeTab: AnalysisTab;
  fetchAnalysis: (ticker: string) => Promise<void>;
  setActiveTab: (tab: AnalysisTab) => void;
}

export const useStockStore = create<StockState>()(
  persist(
    (set) => ({
      currentTicker: null,
      analysis: null,
      isLoading: false,
      error: null,
      activeTab: 'invest',

      fetchAnalysis: async (ticker: string) => {
        set({ currentTicker: ticker, isLoading: true, error: null, analysis: null, activeTab: 'invest' });
        try {
          const analysis = await analyzeStock(ticker);
          set({ analysis, isLoading: false, currentTicker: analysis.ticker });
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Analysis failed';
          set({ error: message, isLoading: false });
        }
      },

      setActiveTab: (tab: AnalysisTab) => set({ activeTab: tab }),
    }),
    {
      name: 'stock-analyzer-state',
      partialize: (state) => ({
        currentTicker: state.currentTicker,
        activeTab: state.activeTab,
      }),
      onRehydrate: () => (state) => {
        if (state?.currentTicker) {
          state.fetchAnalysis(state.currentTicker);
        }
      },
    },
  ),
);
