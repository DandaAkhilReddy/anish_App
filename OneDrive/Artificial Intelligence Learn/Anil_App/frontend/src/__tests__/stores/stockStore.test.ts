import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useStockStore } from '../../stores/stockStore';
import { analyzeStock } from '../../services/stockApi';
import type { StockAnalysisResponse } from '../../types/analysis';

vi.mock('../../services/stockApi');

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

const INITIAL_STATE = {
  currentTicker: null,
  analysis: null,
  isLoading: false,
  error: null,
  activeTab: 'invest' as const,
};

const mockAnalysis: StockAnalysisResponse = {
  ticker: 'AAPL',
  company_name: 'Apple Inc.',
  current_price: 175.5,
  previous_close: 173.0,
  open: 174.0,
  day_high: 176.5,
  day_low: 173.5,
  volume: 55_000_000,
  market_cap: '2.7T',
  pe_ratio: 28.4,
  eps: 6.18,
  week_52_high: 198.23,
  week_52_low: 124.17,
  dividend_yield: 0.55,
  technical: {
    sma_20: 170.0,
    sma_50: 165.0,
    sma_200: 155.0,
    ema_12: 171.0,
    ema_26: 168.0,
    rsi_14: 58.3,
    macd_line: 1.2,
    macd_signal: 0.9,
    macd_histogram: 0.3,
    bollinger_upper: 180.0,
    bollinger_middle: 170.0,
    bollinger_lower: 160.0,
    support_levels: [165.0, 160.0],
    resistance_levels: [180.0, 185.0],
    signal: 'buy',
  },
  news: [
    { title: 'Apple beats earnings', source: 'Reuters', sentiment: 'positive' },
  ],
  quarterly_earnings: [
    {
      quarter: 'Q1 2025',
      revenue: 119_575_000_000,
      net_income: 36_330_000_000,
      eps: 2.4,
      yoy_revenue_growth: 4.0,
    },
  ],
  recommendation: 'buy',
  confidence_score: 0.82,
  summary: 'Apple shows strong fundamentals with consistent earnings growth.',
  bull_case: 'Services revenue continues to grow double digits.',
  bear_case: 'China headwinds and slowing iPhone upgrade cycle.',
  risk_assessment: {
    overall_risk: 'low',
    risk_factors: ['Regulatory scrutiny', 'Currency risk'],
    risk_score: 2.1,
  },
  price_predictions: {
    one_week: { low: 172.0, mid: 176.0, high: 180.0, confidence: 0.75 },
    one_month: { low: 168.0, mid: 178.0, high: 188.0, confidence: 0.65 },
    three_months: { low: 160.0, mid: 185.0, high: 205.0, confidence: 0.55 },
  },
  analysis_timestamp: '2025-01-15T10:00:00Z',
  model_used: 'gpt-4o',
  disclaimer: 'Not financial advice.',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetStore(): void {
  useStockStore.setState(INITIAL_STATE);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useStockStore', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  describe('initial state', () => {
    it('has currentTicker as null', () => {
      expect(useStockStore.getState().currentTicker).toBeNull();
    });

    it('has analysis as null', () => {
      expect(useStockStore.getState().analysis).toBeNull();
    });

    it('has isLoading as false', () => {
      expect(useStockStore.getState().isLoading).toBe(false);
    });

    it('has error as null', () => {
      expect(useStockStore.getState().error).toBeNull();
    });

    it('has activeTab as invest', () => {
      expect(useStockStore.getState().activeTab).toBe('invest');
    });
  });

  // -------------------------------------------------------------------------
  // setActiveTab
  // -------------------------------------------------------------------------

  describe('setActiveTab', () => {
    it('changes activeTab to financials', () => {
      useStockStore.getState().setActiveTab('financials');
      expect(useStockStore.getState().activeTab).toBe('financials');
    });

    it('changes activeTab to about', () => {
      useStockStore.getState().setActiveTab('about');
      expect(useStockStore.getState().activeTab).toBe('about');
    });

    it('changes activeTab back to news', () => {
      useStockStore.getState().setActiveTab('financials');
      useStockStore.getState().setActiveTab('news');
      expect(useStockStore.getState().activeTab).toBe('news');
    });
  });

  // -------------------------------------------------------------------------
  // fetchAnalysis — in-flight state
  // -------------------------------------------------------------------------

  describe('fetchAnalysis — pending state', () => {
    it('sets currentTicker immediately when called', async () => {
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      const promise = useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().currentTicker).toBe('AAPL');
      await promise;
    });

    it('sets isLoading to true immediately when called', async () => {
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      const promise = useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().isLoading).toBe(true);
      await promise;
    });

    it('clears a previous error when called', async () => {
      useStockStore.setState({ error: 'stale error' });
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      const promise = useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().error).toBeNull();
      await promise;
    });

    it('clears previous analysis when called', async () => {
      useStockStore.setState({ analysis: mockAnalysis });
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      const promise = useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().analysis).toBeNull();
      await promise;
    });

    it('resets activeTab to invest when called', async () => {
      useStockStore.setState({ activeTab: 'financials' });
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      const promise = useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().activeTab).toBe('invest');
      await promise;
    });
  });

  // -------------------------------------------------------------------------
  // fetchAnalysis — success
  // -------------------------------------------------------------------------

  describe('fetchAnalysis — success', () => {
    it('sets analysis from the resolved response', async () => {
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().analysis).toEqual(mockAnalysis);
    });

    it('sets isLoading to false after success', async () => {
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().isLoading).toBe(false);
    });

    it('sets currentTicker from the response ticker field', async () => {
      const responseWithDifferentTicker: StockAnalysisResponse = {
        ...mockAnalysis,
        ticker: 'AAPL',  // canonical form that may differ from user input
      };
      vi.mocked(analyzeStock).mockResolvedValue(responseWithDifferentTicker);

      await useStockStore.getState().fetchAnalysis('aapl');

      expect(useStockStore.getState().currentTicker).toBe('AAPL');
    });

    it('leaves error as null after success', async () => {
      useStockStore.setState({ error: 'old error' });
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().error).toBeNull();
    });

    it('calls analyzeStock with the provided ticker', async () => {
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('TSLA');

      expect(vi.mocked(analyzeStock)).toHaveBeenCalledOnce();
      expect(vi.mocked(analyzeStock)).toHaveBeenCalledWith('TSLA');
    });
  });

  // -------------------------------------------------------------------------
  // fetchAnalysis — error (Error instance)
  // -------------------------------------------------------------------------

  describe('fetchAnalysis — error (Error instance)', () => {
    it('sets error to the Error message', async () => {
      vi.mocked(analyzeStock).mockRejectedValue(new Error('Network timeout'));

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().error).toBe('Network timeout');
    });

    it('sets isLoading to false after error', async () => {
      vi.mocked(analyzeStock).mockRejectedValue(new Error('Network timeout'));

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().isLoading).toBe(false);
    });

    it('leaves analysis as null after error', async () => {
      vi.mocked(analyzeStock).mockRejectedValue(new Error('Network timeout'));

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().analysis).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // fetchAnalysis — error (non-Error thrown value)
  // -------------------------------------------------------------------------

  describe('fetchAnalysis — error (non-Error thrown value)', () => {
    it('sets error to "Analysis failed" for a thrown string', async () => {
      vi.mocked(analyzeStock).mockRejectedValue('something went wrong');

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().error).toBe('Analysis failed');
    });

    it('sets error to "Analysis failed" for a thrown plain object', async () => {
      vi.mocked(analyzeStock).mockRejectedValue({ code: 500 });

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().error).toBe('Analysis failed');
    });

    it('sets error to "Analysis failed" for a thrown null', async () => {
      vi.mocked(analyzeStock).mockRejectedValue(null);

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().error).toBe('Analysis failed');
    });

    it('sets isLoading to false for non-Error rejections', async () => {
      vi.mocked(analyzeStock).mockRejectedValue('plain string error');

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().isLoading).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // fetchAnalysis — activeTab reset
  // -------------------------------------------------------------------------

  describe('fetchAnalysis — activeTab reset', () => {
    it('resets activeTab to invest even when previously on financials', async () => {
      useStockStore.setState({ activeTab: 'financials' });
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().activeTab).toBe('invest');
    });

    it('resets activeTab to invest even when previously on about', async () => {
      useStockStore.setState({ activeTab: 'about' });
      vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('AAPL');

      expect(useStockStore.getState().activeTab).toBe('invest');
    });
  });

  // -------------------------------------------------------------------------
  // Multiple sequential fetches
  // -------------------------------------------------------------------------

  describe('sequential fetchAnalysis calls', () => {
    it('overrides state from a prior fetch with the newer ticker', async () => {
      vi.mocked(analyzeStock)
        .mockResolvedValueOnce({ ...mockAnalysis, ticker: 'TSLA' })
        .mockResolvedValueOnce({ ...mockAnalysis, ticker: 'MSFT' });

      await useStockStore.getState().fetchAnalysis('TSLA');
      await useStockStore.getState().fetchAnalysis('MSFT');

      expect(useStockStore.getState().currentTicker).toBe('MSFT');
      expect(useStockStore.getState().analysis?.ticker).toBe('MSFT');
    });

    it('clears a previous error when a subsequent fetch succeeds', async () => {
      vi.mocked(analyzeStock)
        .mockRejectedValueOnce(new Error('first failure'))
        .mockResolvedValueOnce(mockAnalysis);

      await useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().error).toBe('first failure');

      await useStockStore.getState().fetchAnalysis('AAPL');
      expect(useStockStore.getState().error).toBeNull();
    });
  });
});

// ---------------------------------------------------------------------------
// onRehydrate
// ---------------------------------------------------------------------------

describe('onRehydrate', () => {
  it('calls fetchAnalysis when rehydrated state has a currentTicker', () => {
    const mockFetch = vi.fn();
    const state = { currentTicker: 'AAPL', fetchAnalysis: mockFetch } as any;

    const options = (useStockStore.persist as any).getOptions();
    const rehydrateCallback = options.onRehydrate();
    rehydrateCallback(state);

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(mockFetch).toHaveBeenCalledWith('AAPL');
  });

  it('does not call fetchAnalysis when rehydrated state has null currentTicker', () => {
    const mockFetch = vi.fn();
    const state = { currentTicker: null, fetchAnalysis: mockFetch } as any;

    const options = (useStockStore.persist as any).getOptions();
    const rehydrateCallback = options.onRehydrate();
    rehydrateCallback(state);

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('handles undefined state gracefully without throwing', () => {
    const options = (useStockStore.persist as any).getOptions();
    const rehydrateCallback = options.onRehydrate();

    expect(() => rehydrateCallback(undefined)).not.toThrow();
  });

  it('does not call fetchAnalysis when state has an empty string ticker', () => {
    const mockFetch = vi.fn();
    const state = { currentTicker: '', fetchAnalysis: mockFetch } as any;

    const options = (useStockStore.persist as any).getOptions();
    const rehydrateCallback = options.onRehydrate();
    rehydrateCallback(state);

    expect(mockFetch).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Persist middleware
// ---------------------------------------------------------------------------

describe('persist middleware', () => {
  const STORAGE_KEY = 'stock-analyzer-state';

  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY);
    useStockStore.setState({
      currentTicker: null,
      analysis: null,
      isLoading: false,
      error: null,
      activeTab: 'invest',
    });
    vi.clearAllMocks();
  });

  it('writes currentTicker to localStorage when set', async () => {
    vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

    await useStockStore.getState().fetchAnalysis('AAPL');

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored.state.currentTicker).toBe('AAPL');
  });

  it('writes activeTab to localStorage when changed', () => {
    useStockStore.getState().setActiveTab('financials');

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored.state.activeTab).toBe('financials');
  });

  it('does not persist analysis object to localStorage', async () => {
    vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

    await useStockStore.getState().fetchAnalysis('AAPL');

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored.state.analysis).toBeUndefined();
  });

  it('does not persist isLoading to localStorage', async () => {
    vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

    const promise = useStockStore.getState().fetchAnalysis('AAPL');
    // isLoading is true in store but should not be in storage
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored.state.isLoading).toBeUndefined();
    await promise;
  });

  it('does not persist error to localStorage', async () => {
    vi.mocked(analyzeStock).mockRejectedValue(new Error('fail'));

    await useStockStore.getState().fetchAnalysis('AAPL');

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored.state.error).toBeUndefined();
  });

  it('stores data under the key "stock-analyzer-state"', async () => {
    vi.mocked(analyzeStock).mockResolvedValue(mockAnalysis);

    await useStockStore.getState().fetchAnalysis('AAPL');

    expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull();
  });
});
