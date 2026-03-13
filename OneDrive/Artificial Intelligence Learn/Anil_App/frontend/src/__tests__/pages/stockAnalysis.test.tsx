/**
 * Tests for the StockAnalysis page component.
 *
 * The page reads from useStockStore — that store is mocked to control which
 * conditional branch renders.  framer-motion is mocked so motion.div /
 * AnimatePresence render as plain wrappers.
 *
 * Branches tested:
 *   1. No ticker selected  → empty-state prompt
 *   2. Loading in progress → spinner + ticker name
 *   3. Error state         → error message + retry button
 *   4. Analysis available, activeTab = 'chart'      → PriceChart visible
 *   5. Analysis available, activeTab = 'news'       → NewsFeed visible
 *   6. Analysis available, activeTab = 'financials' → QuarterlyEarnings visible
 *   7. Analysis available, activeTab = 'about'      → CompanyAbout visible
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Module mocks — must appear before any import of the mocked modules
// ---------------------------------------------------------------------------

vi.mock('framer-motion', () => {
  const createMotionComponent = (tag: string) => {
    const Component = ({ children, ...props }: any) => {
      const Tag = tag as any;
      return <Tag {...props}>{children}</Tag>;
    };
    Component.displayName = `motion.${tag}`;
    return Component;
  };
  return {
    motion: new Proxy({}, {
      get: (_target, prop: string) => createMotionComponent(prop),
    }),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useMotionValue: () => ({ set: () => {} }),
    useSpring: (v: any) => v,
    useTransform: () => 0,
  };
});

// Mock lightweight-charts so PriceChart renders without a real DOM canvas
vi.mock('lightweight-charts', () => ({
  createChart: () => ({
    addSeries: () => ({ setData: vi.fn() }),
    priceScale: () => ({ applyOptions: vi.fn() }),
    timeScale: () => ({ fitContent: vi.fn(), borderColor: '' }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  }),
  ColorType: { Solid: 'solid' },
  CrosshairMode: { Normal: 1 },
  CandlestickSeries: 'CandlestickSeries',
  HistogramSeries: 'HistogramSeries',
}));

// Stub ResizeObserver for chart tests (jsdom doesn't provide it)
vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
});

const mockFetchAnalysis = vi.fn();
const mockSetActiveTab = vi.fn();

vi.mock('../../stores/stockStore', () => ({
  useStockStore: vi.fn(),
}));

import { useStockStore } from '../../stores/stockStore';
import { StockAnalysis } from '../../pages/StockAnalysis';
import type { StockAnalysisResponse, AnalysisTab } from '../../types/analysis';

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

const mockAnalysis: StockAnalysisResponse = {
  ticker: 'AAPL',
  company_name: 'Apple Inc.',
  current_price: 185.5,
  previous_close: 184.2,
  open: 184.8,
  day_high: 186.1,
  day_low: 184.0,
  volume: 45_000_000,
  market_cap: '2.8T',
  pe_ratio: 28.5,
  eps: 6.51,
  week_52_high: 199.62,
  week_52_low: 164.08,
  dividend_yield: 0.0054,
  technical: {
    sma_20: 183.5,
    sma_50: 180.2,
    sma_200: 175.0,
    ema_12: 184.0,
    ema_26: 182.5,
    rsi_14: 62.3,
    macd_line: 1.5,
    macd_signal: 1.2,
    macd_histogram: 0.3,
    bollinger_upper: 190.0,
    bollinger_middle: 183.5,
    bollinger_lower: 177.0,
    support_levels: [180.0],
    resistance_levels: [190.0],
    signal: 'buy',
  },
  news: [{ title: 'Apple quarterly results', source: 'Reuters', sentiment: 'positive' }],
  quarterly_earnings: [
    { quarter: 'Q1 2025', revenue: 94_900, net_income: 23_600, eps: 1.53, yoy_revenue_growth: 0.05 },
  ],
  historical_prices: [],
  recommendation: 'buy',
  confidence_score: 0.78,
  summary: 'Apple shows strong momentum.',
  bull_case: 'Strong ecosystem.',
  bear_case: 'Regulatory pressure.',
  risk_assessment: { overall_risk: 'medium', risk_factors: ['Regulation'], risk_score: 0.45 },
  price_predictions: {
    one_week: { low: 183, mid: 186, high: 189, confidence: 0.75 },
    one_month: { low: 180, mid: 190, high: 200, confidence: 0.65 },
    three_months: { low: 175, mid: 195, high: 215, confidence: 0.55 },
  },
  analysis_timestamp: '2025-01-01T00:00:00Z',
  model_used: 'kimi-k2.5',
  sector: 'Technology',
  industry: 'Consumer Electronics',
  headquarters: 'Cupertino, CA',
  ceo: 'Tim Cook',
  founded: '1976',
  employees: '164,000',
  company_description: 'Apple designs and sells consumer electronics.',
  disclaimer: 'Not financial advice.',
};

// ---------------------------------------------------------------------------
// Helper: configure what useStockStore returns for each selector call
// ---------------------------------------------------------------------------

interface StoreSlice {
  currentTicker: string | null;
  analysis: StockAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  activeTab: AnalysisTab;
  setActiveTab: typeof mockSetActiveTab;
  fetchAnalysis: typeof mockFetchAnalysis;
}

function setupStore(overrides: Partial<StoreSlice> = {}): void {
  const store: StoreSlice = {
    currentTicker: null,
    analysis: null,
    isLoading: false,
    error: null,
    activeTab: 'chart',
    setActiveTab: mockSetActiveTab,
    fetchAnalysis: mockFetchAnalysis,
    ...overrides,
  };

  vi.mocked(useStockStore).mockImplementation(
    (selector: (s: StoreSlice) => unknown) => selector(store),
  );

  // Imperative getState used by the Retry button
  (useStockStore as unknown as { getState: () => StoreSlice }).getState = () => store;

  // Persist middleware API used by hydration guard
  (useStockStore as unknown as Record<string, unknown>).persist = {
    hasHydrated: () => true,
    onFinishHydration: () => () => {},
  };
}

// ===========================================================================
// StockAnalysis page
// ===========================================================================

describe('StockAnalysis', () => {
  beforeEach(() => {
    mockFetchAnalysis.mockClear();
    mockSetActiveTab.mockClear();
  });

  // -------------------------------------------------------------------------
  // 1. Empty state — no ticker
  // -------------------------------------------------------------------------

  describe('empty state (no currentTicker)', () => {
    beforeEach(() => setupStore({ currentTicker: null }));

    it('shows the "AI-Powered" heading from LandingHero', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/AI-Powered/i)).toBeInTheDocument();
    });

    it('shows the "Stock Analysis" text from LandingHero', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/Stock Analysis/i)).toBeInTheDocument();
    });

    it('does not show a loading spinner', () => {
      render(<StockAnalysis />);
      const svgs = document.querySelectorAll('svg');
      const spinner = Array.from(svgs).find((svg) => svg.classList.contains('animate-spin'));
      expect(spinner).toBeUndefined();
    });
  });

  // -------------------------------------------------------------------------
  // 2. Loading state
  // -------------------------------------------------------------------------

  describe('loading state', () => {
    beforeEach(() => setupStore({ currentTicker: 'AAPL', isLoading: true }));

    it('shows "Analyzing AAPL..." text', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/Analyzing AAPL/)).toBeInTheDocument();
    });

    it('shows the loading spinner (animate-spin class)', () => {
      render(<StockAnalysis />);
      const svgs = document.querySelectorAll('svg');
      const spinner = Array.from(svgs).find((svg) => svg.classList.contains('animate-spin'));
      expect(spinner).toBeInTheDocument();
    });

    it('does not show error UI during loading', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText(/Error analyzing/)).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 3. Error state
  // -------------------------------------------------------------------------

  describe('error state', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'AAPL', isLoading: false, error: 'Ticker not found' }),
    );

    it('shows "Error analyzing AAPL" heading', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Error analyzing AAPL')).toBeInTheDocument();
    });

    it('shows the error message text', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Ticker not found')).toBeInTheDocument();
    });

    it('renders a Try Again button', () => {
      render(<StockAnalysis />);
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('calls fetchAnalysis with the current ticker when Try Again is clicked', () => {
      render(<StockAnalysis />);
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));
      expect(mockFetchAnalysis).toHaveBeenCalledOnce();
      expect(mockFetchAnalysis).toHaveBeenCalledWith('AAPL');
    });
  });

  // -------------------------------------------------------------------------
  // 4. Analysis available — chart tab (default)
  // -------------------------------------------------------------------------

  describe('analysis loaded — chart tab', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'AAPL', analysis: mockAnalysis, activeTab: 'chart' }),
    );

    it('renders StockHeader with ticker', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });

    it('renders the company name', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    });

    it('renders the TabBar with all 4 tabs', () => {
      render(<StockAnalysis />);
      expect(screen.getByRole('button', { name: /chart/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /news/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /financials/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /about/i })).toBeInTheDocument();
    });

    it('renders the PriceChart area when activeTab is chart', () => {
      render(<StockAnalysis />);
      // With empty historical_prices, the empty state message renders
      expect(
        screen.getByText('No historical price data available'),
      ).toBeInTheDocument();
    });

    it('does not render NewsFeed on the chart tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Latest News')).not.toBeInTheDocument();
    });

    it('calls setActiveTab when a tab button is clicked', () => {
      render(<StockAnalysis />);
      fireEvent.click(screen.getByRole('button', { name: /financials/i }));
      expect(mockSetActiveTab).toHaveBeenCalledWith('financials');
    });
  });

  // -------------------------------------------------------------------------
  // 4b. Chart with historical price data — time range buttons
  // -------------------------------------------------------------------------

  describe('chart time range buttons', () => {
    const priceData = [
      { date: '2020-01-02', open: 74, high: 75, low: 73, close: 74.5, volume: 1000 },
      { date: '2023-06-15', open: 180, high: 182, low: 179, close: 181, volume: 2000 },
      { date: '2025-03-10', open: 185, high: 186, low: 184, close: 185.5, volume: 3000 },
    ];

    beforeEach(() =>
      setupStore({
        currentTicker: 'AAPL',
        analysis: { ...mockAnalysis, historical_prices: priceData },
        activeTab: 'chart',
      }),
    );

    it('renders all 7 time range buttons including 1Y, 5Y, ALL', () => {
      render(<StockAnalysis />);
      for (const label of ['1W', '1M', '3M', '6M', '1Y', '5Y', 'ALL']) {
        expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
      }
    });

    it('renders Price Chart heading when data is available', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Price Chart')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 5. Analysis available — news tab
  // -------------------------------------------------------------------------

  describe('analysis loaded — news tab', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'AAPL', analysis: mockAnalysis, activeTab: 'news' }),
    );

    it('renders the NewsFeed when activeTab is news', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Latest News')).toBeInTheDocument();
    });

    it('renders the news article title', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Apple quarterly results')).toBeInTheDocument();
    });

    it('does not render QuarterlyEarnings on the news tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Quarterly Earnings')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 6. Analysis available — financials tab
  // -------------------------------------------------------------------------

  describe('analysis loaded — financials tab', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'AAPL', analysis: mockAnalysis, activeTab: 'financials' }),
    );

    it('renders QuarterlyEarnings heading on financials tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Quarterly Earnings')).toBeInTheDocument();
    });

    it('renders Price Data card on financials tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Price Data')).toBeInTheDocument();
    });

    it('renders Technical Summary on financials tab when technical data exists', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Technical Summary')).toBeInTheDocument();
    });

    it('renders Price Predictions on financials tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Price Predictions')).toBeInTheDocument();
    });

    it('does not render NewsFeed (Latest News) on financials tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Latest News')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 7. Analysis available — about tab
  // -------------------------------------------------------------------------

  describe('analysis loaded — about tab', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'AAPL', analysis: mockAnalysis, activeTab: 'about' }),
    );

    it('renders the company description on the about tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/Apple designs and sells consumer electronics/)).toBeInTheDocument();
    });

    it('renders AI Analysis Summary on the about tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('AI Analysis Summary')).toBeInTheDocument();
    });

    it('renders Bull Case section on the about tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Bull Case')).toBeInTheDocument();
    });

    it('renders Bear Case section on the about tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Bear Case')).toBeInTheDocument();
    });

    it('renders Risk Assessment heading on the about tab', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Risk Assessment')).toBeInTheDocument();
    });

    it('does not render NewsFeed on about tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Latest News')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 8. Ticker present but analysis is null and not loading (returns null)
  // -------------------------------------------------------------------------

  describe('ticker set but analysis is null and not loading or erroring', () => {
    it('renders nothing (returns null) when ticker is set but analysis is null', () => {
      setupStore({ currentTicker: 'AAPL', analysis: null, isLoading: false, error: null });
      const { container } = render(<StockAnalysis />);
      expect(container.firstChild).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // 9. Analysis available — invest tab with long_term_outlook present
  // -------------------------------------------------------------------------

  const mockOutlook = {
    one_year: { low: 190, mid: 210, high: 230, confidence: 0.72 },
    five_year: { low: 240, mid: 290, high: 350, confidence: 0.6 },
    ten_year: { low: 300, mid: 400, high: 520, confidence: 0.45 },
    verdict: 'buy' as const,
    verdict_rationale: 'Strong fundamentals support long-term appreciation.',
    catalysts: ['AI integration', 'Services growth'],
    long_term_risks: ['Regulatory headwinds'],
    compound_annual_return: 12.5,
  };

  const mockAnalysisWithOutlook: StockAnalysisResponse = {
    ...mockAnalysis,
    long_term_outlook: mockOutlook,
  };

  describe('analysis loaded — invest tab (with outlook)', () => {
    beforeEach(() =>
      setupStore({
        currentTicker: 'AAPL',
        analysis: mockAnalysisWithOutlook,
        activeTab: 'invest',
      }),
    );

    it('renders the verdict banner with BUY FOR LONG TERM', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('BUY FOR LONG TERM')).toBeInTheDocument();
    });

    it('renders the verdict_rationale text', () => {
      render(<StockAnalysis />);
      expect(
        screen.getByText('Strong fundamentals support long-term appreciation.'),
      ).toBeInTheDocument();
    });

    it('renders the Price Trajectory section heading', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Price Trajectory')).toBeInTheDocument();
    });

    it('renders all three time horizon labels', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('1 Year')).toBeInTheDocument();
      expect(screen.getByText('5 Years')).toBeInTheDocument();
      expect(screen.getByText('10 Years')).toBeInTheDocument();
    });

    it('renders Growth Catalysts section', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Growth Catalysts')).toBeInTheDocument();
    });

    it('renders catalyst items from outlook data', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('AI integration')).toBeInTheDocument();
      expect(screen.getByText('Services growth')).toBeInTheDocument();
    });

    it('renders Long-Term Risks section', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Long-Term Risks')).toBeInTheDocument();
    });

    it('renders risk items from outlook data', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Regulatory headwinds')).toBeInTheDocument();
    });

    it('renders the CAGR estimate', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/12\.5%\s*CAGR/)).toBeInTheDocument();
    });

    it('renders the bottom-line ticker summary', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/for long-term investors/i)).toBeInTheDocument();
    });

    it('does not render the "not available" fallback message', () => {
      render(<StockAnalysis />);
      expect(
        screen.queryByText('Long-term outlook data not available for this stock.'),
      ).not.toBeInTheDocument();
    });

    it('does not render NewsFeed on the invest tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Latest News')).not.toBeInTheDocument();
    });

    it('does not render QuarterlyEarnings on the invest tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Quarterly Earnings')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 10. Analysis available — invest tab without long_term_outlook
  // -------------------------------------------------------------------------

  describe('analysis loaded — invest tab (no outlook)', () => {
    beforeEach(() =>
      setupStore({
        currentTicker: 'AAPL',
        analysis: { ...mockAnalysis, long_term_outlook: null },
        activeTab: 'invest',
      }),
    );

    it('renders the "not available" fallback message', () => {
      render(<StockAnalysis />);
      expect(
        screen.getByText('Long-term outlook data not available for this stock.'),
      ).toBeInTheDocument();
    });

    it('does not render the verdict banner', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText(/FOR LONG TERM/)).not.toBeInTheDocument();
    });

    it('does not render Price Trajectory', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Price Trajectory')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 11. Loading state — timer messages
  // -------------------------------------------------------------------------

  describe('loading state — timer messages', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'TSLA', isLoading: true }),
    );

    it('renders the ticker name in the "Analyzing…" line', () => {
      render(<StockAnalysis />);
      expect(screen.getByText(/Analyzing TSLA/)).toBeInTheDocument();
    });

    it('shows the initial agent message at second 0', () => {
      render(<StockAnalysis />);
      // loadingSeconds starts at 0 → messageIndex 0 → first message
      expect(
        screen.getByText('Your AI agent is analyzing market data...'),
      ).toBeInTheDocument();
    });

    it('does not render analysis content while loading', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText('Price Trajectory')).not.toBeInTheDocument();
      expect(screen.queryByText('Latest News')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // 12. Analysis available — about tab (CompanyAbout component coverage)
  // -------------------------------------------------------------------------

  describe('analysis loaded — about tab (CompanyAbout deep coverage)', () => {
    beforeEach(() =>
      setupStore({ currentTicker: 'AAPL', analysis: mockAnalysis, activeTab: 'about' }),
    );

    it('renders the "About Apple Inc." heading from CompanyAbout', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('About Apple Inc.')).toBeInTheDocument();
    });

    it('renders the Company Info section', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Company Info')).toBeInTheDocument();
    });

    it('renders the Key Statistics section', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Key Statistics')).toBeInTheDocument();
    });

    it('renders the CEO value from analysis fixture', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Tim Cook')).toBeInTheDocument();
    });

    it('renders the headquarters value', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Cupertino, CA')).toBeInTheDocument();
    });

    it('renders the disclaimer text', () => {
      render(<StockAnalysis />);
      expect(screen.getByText('Not financial advice.')).toBeInTheDocument();
    });

    it('does not render invest-tab content on the about tab', () => {
      render(<StockAnalysis />);
      expect(screen.queryByText(/FOR LONG TERM/)).not.toBeInTheDocument();
      expect(
        screen.queryByText('Long-term outlook data not available for this stock.'),
      ).not.toBeInTheDocument();
    });
  });
});
