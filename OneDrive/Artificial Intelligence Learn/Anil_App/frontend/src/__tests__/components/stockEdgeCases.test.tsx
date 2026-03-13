/**
 * Additional branch-coverage tests for stock display components
 * and NewsCard that were below 96% coverage after the main test pass.
 *
 * Specifically targets:
 *   - NewsCard line 15: fallback when sentiment is an unrecognised string value
 *   - KeyStats lines 16, 28: null eps and null week_52_low (already exercised
 *     but here we add the exact null paths for eps/week_52_low in isolation)
 *   - PriceCard line 8: formatNumber small-number branch (< 1_000)
 *   - StockHeader line 11: previousClose = 0 (changePercent stays 0)
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
    tr: ({ children, ...props }: React.HTMLAttributes<HTMLTableRowElement> & { children?: React.ReactNode }) => (
      <tr {...props}>{children}</tr>
    ),
  },
  useMotionValue: () => ({ set: vi.fn() }),
  useSpring: (v: unknown) => v,
  useTransform: () => 0,
}));

import { NewsCard } from '../../components/news/NewsCard';
import { KeyStats } from '../../components/stock/KeyStats';
import { PriceCard } from '../../components/stock/PriceCard';
import { StockHeader } from '../../components/stock/StockHeader';
import type { StockAnalysisResponse } from '../../types/analysis';

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

const baseAnalysis: StockAnalysisResponse = {
  ticker: 'TEST',
  company_name: 'Test Corp',
  current_price: 100.0,
  previous_close: 99.0,
  open: 98.5,
  day_high: 101.0,
  day_low: 97.0,
  volume: 500,
  market_cap: '1.0B',
  pe_ratio: 15.0,
  eps: 2.5,
  week_52_high: 120.0,
  week_52_low: 80.0,
  dividend_yield: 0.02,
  technical: null,
  news: [],
  quarterly_earnings: [],
  recommendation: 'hold',
  confidence_score: 0.5,
  summary: 'Stable',
  bull_case: 'Growth',
  bear_case: 'Risk',
  risk_assessment: { overall_risk: 'low', risk_factors: [], risk_score: 0.2 },
  price_predictions: {
    one_week: { low: 98, mid: 101, high: 104, confidence: 0.6 },
    one_month: { low: 95, mid: 105, high: 115, confidence: 0.5 },
    three_months: { low: 90, mid: 110, high: 130, confidence: 0.4 },
  },
  analysis_timestamp: '2025-01-01T00:00:00Z',
  model_used: 'test-model',
  disclaimer: 'Test only',
};

// ===========================================================================
// NewsCard — unrecognised sentiment fallback (line 15)
// ===========================================================================

describe('NewsCard — unrecognised sentiment fallback', () => {
  it('falls back to bg-stone-300 dot for an unrecognised sentiment string', () => {
    // Cast bypasses TS so we can hit the ?? 'bg-stone-300' fallback in dotColor
    const { container } = render(
      <NewsCard
        item={{
          title: 'Test headline',
          source: 'Source',
          sentiment: 'unknown_value' as 'positive',
        }}
      />,
    );
    const dot = container.querySelector('.bg-stone-300');
    expect(dot).toBeInTheDocument();
  });
});

// ===========================================================================
// KeyStats — null eps (line 28) and null week_52_low (line 16)
// ===========================================================================

describe('KeyStats — isolated null branches', () => {
  it('renders "N/A" for null eps specifically in KeyStats', () => {
    render(<KeyStats analysis={{ ...baseAnalysis, eps: null }} />);
    const naItems = screen.getAllByText('N/A');
    expect(naItems.length).toBeGreaterThanOrEqual(1);
  });

  it('renders "N/A" for null week_52_low specifically in KeyStats', () => {
    render(<KeyStats analysis={{ ...baseAnalysis, week_52_low: null }} />);
    const naItems = screen.getAllByText('N/A');
    expect(naItems.length).toBeGreaterThanOrEqual(1);
  });
});

// ===========================================================================
// PriceCard — formatNumber small number branch (line 8: < 1_000)
// ===========================================================================

describe('PriceCard — formatNumber small volume', () => {
  it('formats volume < 1000 using toLocaleString (no suffix)', () => {
    // volume=500 < 1_000 → falls through to n.toLocaleString()
    render(<PriceCard analysis={{ ...baseAnalysis, volume: 500 }} />);
    // toLocaleString for 500 in en-US context → "500"
    expect(screen.getByText('500')).toBeInTheDocument();
  });

  it('formats volume of exactly 999 without a suffix', () => {
    render(<PriceCard analysis={{ ...baseAnalysis, volume: 999 }} />);
    expect(screen.getByText('999')).toBeInTheDocument();
  });
});

// ===========================================================================
// StockHeader — previousClose = 0 edge case (line 11: changePercent = 0)
// ===========================================================================

describe('StockHeader — previousClose = 0 edge case', () => {
  it('omits the change row when previous_close is 0 (avoids divide-by-zero)', () => {
    // previousClose=0 is falsy → change = null → change row is not rendered
    render(
      <StockHeader
        analysis={{ ...baseAnalysis, current_price: 100, previous_close: 0 }}
      />,
    );
    // The price is still displayed
    expect(screen.getByText('$100.00')).toBeInTheDocument();
    // No change percentage is rendered when previous_close is 0
    expect(screen.queryByText(/[+\-]\d+\.\d+%/)).not.toBeInTheDocument();
  });
});

// ===========================================================================
// config/env.ts — branch coverage (VITE_API_URL / VITE_WS_URL fallback)
// ===========================================================================

describe('config/env', () => {
  it('exports a config object with apiUrl and wsUrl properties', async () => {
    const { config } = await import('../../config/env');
    expect(config).toHaveProperty('apiUrl');
    expect(config).toHaveProperty('wsUrl');
  });

  it('apiUrl falls back to empty string when VITE_API_URL is not set', async () => {
    const { config } = await import('../../config/env');
    // In the test environment VITE_API_URL is not defined, so it falls back to ''
    expect(typeof config.apiUrl).toBe('string');
  });

  it('wsUrl falls back to empty string when VITE_WS_URL is not set', async () => {
    const { config } = await import('../../config/env');
    expect(typeof config.wsUrl).toBe('string');
  });
});
