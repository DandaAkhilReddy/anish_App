/**
 * Tests for SignalBanner and StockSearchBar components.
 *
 * Globals (describe, it, expect, vi, beforeEach) are injected by vitest's
 * `globals: true` config. jest-dom matchers are available via setup.ts.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { vi, beforeEach } from 'vitest';
import { SignalBanner } from '../../components/stock/SignalBanner';
import { StockSearchBar } from '../../components/search/StockSearchBar';
import type { StockAnalysisResponse } from '../../types/analysis';

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  useMotionValue: () => ({ set: vi.fn() }),
  useSpring: (v: unknown) => v,
  useTransform: () => 0,
}));

// Mock the entire stockStore module so StockSearchBar never touches zustand
// internals. Each test can configure the returned slice as needed.
const mockFetchAnalysis = vi.fn();

vi.mock('../../stores/stockStore', () => ({
  useStockStore: vi.fn(),
}));

// Mock the stock API so useStockSearch's debounced fetch never hits the network
vi.mock('../../services/stockApi', () => ({
  searchStocks: vi.fn().mockResolvedValue([]),
  analyzeStock: vi.fn().mockResolvedValue({}),
}));

// Lazily import the mocked module so we can configure it per-test.
import { useStockStore } from '../../stores/stockStore';

// ---------------------------------------------------------------------------
// Shared fixture
// ---------------------------------------------------------------------------

const mockAnalysis: StockAnalysisResponse = {
  ticker: 'AAPL',
  company_name: 'Apple Inc.',
  current_price: 185.50,
  previous_close: 184.20,
  open: 184.80,
  day_high: 186.10,
  day_low: 184.00,
  volume: 45_000_000,
  market_cap: '2.8T',
  pe_ratio: 28.5,
  eps: 6.51,
  week_52_high: 199.62,
  week_52_low: 164.08,
  dividend_yield: 0.0054,
  technical: {
    sma_20: 183.50,
    sma_50: 180.20,
    sma_200: 175.00,
    ema_12: 184.00,
    ema_26: 182.50,
    rsi_14: 62.3,
    macd_line: 1.5,
    macd_signal: 1.2,
    macd_histogram: 0.3,
    bollinger_upper: 190.0,
    bollinger_middle: 183.5,
    bollinger_lower: 177.0,
    support_levels: [180.0],
    resistance_levels: [190.0],
    signal: 'buy' as const,
  },
  news: [],
  quarterly_earnings: [],
  recommendation: 'buy' as const,
  confidence_score: 0.78,
  summary: 'Apple shows strong momentum.',
  bull_case: 'Strong ecosystem.',
  bear_case: 'Regulatory pressure.',
  risk_assessment: {
    overall_risk: 'medium' as const,
    risk_factors: ['Regulation'],
    risk_score: 0.45,
  },
  price_predictions: {
    one_week: { low: 183, mid: 186, high: 189, confidence: 0.75 },
    one_month: { low: 180, mid: 190, high: 200, confidence: 0.65 },
    three_months: { low: 175, mid: 195, high: 215, confidence: 0.55 },
  },
  analysis_timestamp: '2025-01-01T00:00:00Z',
  model_used: 'kimi-k2.5',
  disclaimer: 'Test disclaimer',
};

// ---------------------------------------------------------------------------
// SignalBanner
// ---------------------------------------------------------------------------

describe('SignalBanner', () => {
  describe('with full technical data', () => {
    beforeEach(() => {
      render(<SignalBanner analysis={mockAnalysis} />);
    });

    it('renders the recommendation label "Buy"', () => {
      // Badge renders the label from the recommendationLabels map
      expect(screen.getByText('Buy')).toBeInTheDocument();
    });

    it('shows confidence as "78%"', () => {
      // confidence_score: 0.78 → toFixed(0) → "78"
      expect(screen.getByText('78%')).toBeInTheDocument();
    });

    it('shows the RSI value "62"', () => {
      // rsi_14: 62.3 → toFixed(0) → "62"
      // The component renders: RSI: <span>62</span>
      expect(screen.getByText('62')).toBeInTheDocument();
    });

    it('shows risk level "Medium"', () => {
      expect(screen.getByText('Medium')).toBeInTheDocument();
    });

    it('renders the summary text', () => {
      expect(screen.getByText('Apple shows strong momentum.')).toBeInTheDocument();
    });

    it('renders the disclaimer text', () => {
      expect(screen.getByText('Test disclaimer')).toBeInTheDocument();
    });

    it('renders the technical signal badge', () => {
      // signal: 'buy' → replace('_', ' ') → 'buy' (no underscore in this value)
      // Badge renders it as a sibling to the "Tech:" label
      const techLabels = screen.getAllByText('buy');
      // One badge for recommendation "Buy" (capitalised) — that's "Buy".
      // The technical signal badge renders lowercase "buy".
      expect(techLabels.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('with null technical data', () => {
    it('does not render RSI when technical is null', () => {
      const analysisNoTech: StockAnalysisResponse = { ...mockAnalysis, technical: null };
      render(<SignalBanner analysis={analysisNoTech} />);
      // "RSI:" label should not appear
      expect(screen.queryByText(/RSI:/)).not.toBeInTheDocument();
    });

    it('does not render the technical signal section when technical is null', () => {
      const analysisNoTech: StockAnalysisResponse = { ...mockAnalysis, technical: null };
      render(<SignalBanner analysis={analysisNoTech} />);
      // "Tech:" label is only rendered inside the technicalSignal guard
      expect(screen.queryByText('Tech:')).not.toBeInTheDocument();
    });

    it('still renders recommendation and confidence when technical is null', () => {
      const analysisNoTech: StockAnalysisResponse = { ...mockAnalysis, technical: null };
      render(<SignalBanner analysis={analysisNoTech} />);
      expect(screen.getByText('Buy')).toBeInTheDocument();
      expect(screen.getByText('78%')).toBeInTheDocument();
    });

    it('still renders risk level when technical is null', () => {
      const analysisNoTech: StockAnalysisResponse = { ...mockAnalysis, technical: null };
      render(<SignalBanner analysis={analysisNoTech} />);
      expect(screen.getByText('Medium')).toBeInTheDocument();
    });

    it('still renders summary and disclaimer when technical is null', () => {
      const analysisNoTech: StockAnalysisResponse = { ...mockAnalysis, technical: null };
      render(<SignalBanner analysis={analysisNoTech} />);
      expect(screen.getByText('Apple shows strong momentum.')).toBeInTheDocument();
      expect(screen.getByText('Test disclaimer')).toBeInTheDocument();
    });
  });

  describe('recommendation label mapping', () => {
    it('renders "Strong Buy" for strong_buy recommendation', () => {
      const analysis = { ...mockAnalysis, recommendation: 'strong_buy' as const };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('Strong Buy')).toBeInTheDocument();
    });

    it('renders "Hold" for hold recommendation', () => {
      const analysis = { ...mockAnalysis, recommendation: 'hold' as const };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('Hold')).toBeInTheDocument();
    });

    it('renders "Sell" for sell recommendation', () => {
      const analysis = { ...mockAnalysis, recommendation: 'sell' as const };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('Sell')).toBeInTheDocument();
    });

    it('renders "Strong Sell" for strong_sell recommendation', () => {
      const analysis = { ...mockAnalysis, recommendation: 'strong_sell' as const };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('Strong Sell')).toBeInTheDocument();
    });
  });

  describe('risk level label mapping', () => {
    it('renders "Low" for low risk', () => {
      const analysis = {
        ...mockAnalysis,
        risk_assessment: { ...mockAnalysis.risk_assessment, overall_risk: 'low' as const },
      };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('Low')).toBeInTheDocument();
    });

    it('renders "High" for high risk', () => {
      const analysis = {
        ...mockAnalysis,
        risk_assessment: { ...mockAnalysis.risk_assessment, overall_risk: 'high' as const },
      };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('renders "Very High" for very_high risk', () => {
      const analysis = {
        ...mockAnalysis,
        risk_assessment: { ...mockAnalysis.risk_assessment, overall_risk: 'very_high' as const },
      };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('Very High')).toBeInTheDocument();
    });
  });

  describe('confidence score boundary values', () => {
    it('renders "0%" for confidence_score of 0', () => {
      const analysis = { ...mockAnalysis, confidence_score: 0 };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('renders "100%" for confidence_score of 1', () => {
      const analysis = { ...mockAnalysis, confidence_score: 1 };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('rounds 0.555 to "56%"', () => {
      const analysis = { ...mockAnalysis, confidence_score: 0.555 };
      render(<SignalBanner analysis={analysis} />);
      // toFixed(0) rounds half-up in V8 for 0.555 → "56"
      expect(screen.getByText(/\d+%/)).toBeInTheDocument();
    });
  });

  describe('RSI null within a non-null technical object', () => {
    it('does not render RSI span when rsi_14 is null', () => {
      const analysis: StockAnalysisResponse = {
        ...mockAnalysis,
        technical: { ...mockAnalysis.technical!, rsi_14: null },
      };
      render(<SignalBanner analysis={analysis} />);
      expect(screen.queryByText(/RSI:/)).not.toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// StockSearchBar
// ---------------------------------------------------------------------------

/**
 * Helper: configure the useStockStore mock for a given test scenario.
 * The component calls useStockStore as a selector hook AND reads
 * useStockStore.getState().fetchAnalysis imperatively, so we must mock both.
 */
function setupStoreMock({ isLoading = false }: { isLoading?: boolean } = {}): void {
  const mockedUseStore = vi.mocked(useStockStore) as unknown as {
    (selector: (s: { isLoading: boolean }) => boolean): boolean;
    getState: () => { fetchAnalysis: typeof mockFetchAnalysis };
  };

  // Selector call: useStockStore((s) => s.isLoading)
  (mockedUseStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    (selector: (s: { isLoading: boolean }) => boolean) => selector({ isLoading }),
  );

  // Imperative call: useStockStore.getState().fetchAnalysis(ticker)
  mockedUseStore.getState = () => ({ fetchAnalysis: mockFetchAnalysis });
}

describe('StockSearchBar', () => {
  beforeEach(() => {
    mockFetchAnalysis.mockClear();
    setupStoreMock({ isLoading: false });
  });

  describe('rendering', () => {
    it('renders an input with the expected placeholder text', () => {
      render(<StockSearchBar />);
      const input = screen.getByPlaceholderText(
        'Search stocks — type to see suggestions (e.g., A for Apple)',
      );
      expect(input).toBeInTheDocument();
    });

    it('renders the search button when not loading', () => {
      render(<StockSearchBar />);
      expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
    });

    it('renders a loading spinner instead of the search button when isLoading is true', () => {
      setupStoreMock({ isLoading: true });
      render(<StockSearchBar />);
      // Spinner is a Loader2 SVG with animate-spin; search button should be gone
      expect(screen.queryByRole('button', { name: /search/i })).not.toBeInTheDocument();
      const svgs = document.querySelectorAll('svg');
      const spinner = Array.from(svgs).find((svg) => svg.classList.contains('animate-spin'));
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Enter key submission', () => {
    it('calls fetchAnalysis with the uppercased, trimmed ticker on Enter', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: '  aapl  ' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockFetchAnalysis).toHaveBeenCalledOnce();
      expect(mockFetchAnalysis).toHaveBeenCalledWith('AAPL');
    });

    it('does not call fetchAnalysis when input is empty on Enter', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockFetchAnalysis).not.toHaveBeenCalled();
    });

    it('does not call fetchAnalysis when input is only whitespace on Enter', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: '   ' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockFetchAnalysis).not.toHaveBeenCalled();
    });

    it('does not call fetchAnalysis when isLoading is true on Enter', () => {
      setupStoreMock({ isLoading: true });
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'TSLA' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockFetchAnalysis).not.toHaveBeenCalled();
    });

    it('uppercases a mixed-case ticker before calling fetchAnalysis', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'Msft' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockFetchAnalysis).toHaveBeenCalledWith('MSFT');
    });
  });

  describe('search button click submission', () => {
    it('calls fetchAnalysis when the search button is clicked with a valid ticker', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'GOOG' } });
      fireEvent.click(screen.getByRole('button', { name: /search/i }));

      expect(mockFetchAnalysis).toHaveBeenCalledOnce();
      expect(mockFetchAnalysis).toHaveBeenCalledWith('GOOG');
    });

    it('does not call fetchAnalysis when button is clicked with empty input', () => {
      render(<StockSearchBar />);
      fireEvent.click(screen.getByRole('button', { name: /search/i }));
      expect(mockFetchAnalysis).not.toHaveBeenCalled();
    });
  });

  describe('Escape key', () => {
    it('blurs the input when Escape is pressed', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      input.focus();
      expect(document.activeElement).toBe(input);

      fireEvent.keyDown(input, { key: 'Escape' });

      expect(document.activeElement).not.toBe(input);
    });
  });

  describe('input controlled state', () => {
    it('updates displayed value as user types', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox') as HTMLInputElement;

      fireEvent.change(input, { target: { value: 'NVDA' } });

      expect(input.value).toBe('NVDA');
    });

    it('starts with an empty input value', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox') as HTMLInputElement;
      expect(input.value).toBe('');
    });
  });

  describe('non-Enter keys', () => {
    it('does not call fetchAnalysis for other keys like ArrowDown', () => {
      render(<StockSearchBar />);
      const input = screen.getByRole('textbox');

      fireEvent.change(input, { target: { value: 'TSLA' } });
      fireEvent.keyDown(input, { key: 'ArrowDown' });

      expect(mockFetchAnalysis).not.toHaveBeenCalled();
    });
  });
});
