/**
 * Tests for layout components: AppLayout, Header.
 *
 * Header renders StockSearchBar which depends on useStockStore — the store is
 * mocked here so the test remains isolated and synchronous.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mock the store so StockSearchBar (rendered inside Header) doesn't hit zustand
// ---------------------------------------------------------------------------

const mockStore = {
  currentTicker: null as string | null,
  isLoading: false,
};

vi.mock('../../stores/stockStore', () => ({
  useStockStore: vi.fn((selector: (s: typeof mockStore) => unknown) =>
    selector(mockStore),
  ),
}));

// Mock the stock API so useStockSearch's debounced fetch never hits the network
vi.mock('../../services/stockApi', () => ({
  searchStocks: vi.fn().mockResolvedValue([]),
  analyzeStock: vi.fn().mockResolvedValue({}),
}));

// Attach getState so the imperative call in StockSearchBar works too
import { useStockStore } from '../../stores/stockStore';
(useStockStore as unknown as { getState: () => { fetchAnalysis: () => void } }).getState = () => ({
  fetchAnalysis: vi.fn(),
});

import { AppLayout } from '../../components/layout/AppLayout';
import { Header } from '../../components/layout/Header';

// ===========================================================================
// AppLayout
// ===========================================================================

describe('AppLayout', () => {
  beforeEach(() => {
    mockStore.currentTicker = null;
    mockStore.isLoading = false;
  });

  it('renders children inside the layout', () => {
    render(
      <AppLayout>
        <span>inner content</span>
      </AppLayout>,
    );
    expect(screen.getByText('inner content')).toBeInTheDocument();
  });

  it('renders the Header inside AppLayout (Stock Analyzer brand text is present)', () => {
    render(
      <AppLayout>
        <span>child</span>
      </AppLayout>,
    );
    expect(screen.getByText('Stock Analyzer')).toBeInTheDocument();
  });

  it('renders a <main> element that wraps children', () => {
    render(
      <AppLayout>
        <p data-testid="child-node">content</p>
      </AppLayout>,
    );
    const main = document.querySelector('main');
    expect(main).toBeInTheDocument();
    expect(main).toContainElement(screen.getByTestId('child-node'));
  });

  it('wraps everything in a min-h-screen container', () => {
    const { container } = render(<AppLayout><span /></AppLayout>);
    const root = container.firstElementChild as HTMLElement;
    expect(root).toHaveClass('min-h-screen');
  });

  it('renders multiple children correctly', () => {
    render(
      <AppLayout>
        <span>first</span>
        <span>second</span>
      </AppLayout>,
    );
    expect(screen.getByText('first')).toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
  });

  it('main has max-w-5xl class when currentTicker is set', () => {
    mockStore.currentTicker = 'AAPL';
    render(<AppLayout><span /></AppLayout>);
    const main = document.querySelector('main') as HTMLElement;
    expect(main).toHaveClass('max-w-5xl');
  });
});

// ===========================================================================
// Header
// ===========================================================================

describe('Header', () => {
  beforeEach(() => {
    mockStore.currentTicker = null;
    mockStore.isLoading = false;
  });

  afterEach(() => {
    mockStore.currentTicker = null;
  });

  it('renders the "Stock Analyzer" brand title', () => {
    render(<Header />);
    expect(screen.getByText('Stock Analyzer')).toBeInTheDocument();
  });

  it('renders the "AI-Powered Analysis" subtitle', () => {
    render(<Header />);
    expect(screen.getByText('AI-Powered Analysis')).toBeInTheDocument();
  });

  it('renders a <header> element', () => {
    render(<Header />);
    expect(document.querySelector('header')).toBeInTheDocument();
  });

  it('renders the StockSearchBar input within the header when currentTicker is set', () => {
    mockStore.currentTicker = 'AAPL';
    render(<Header />);
    const input = screen.getByPlaceholderText(
      'Search stocks — type to see suggestions (e.g., A for Apple)',
    );
    expect(input).toBeInTheDocument();
  });

  it('does not render the search bar when currentTicker is null (landing state)', () => {
    render(<Header />);
    expect(
      screen.queryByPlaceholderText(
        'Search stocks — type to see suggestions (e.g., A for Apple)',
      ),
    ).not.toBeInTheDocument();
  });

  it('header has bg-transparent class when currentTicker is null (landing state)', () => {
    render(<Header />);
    const header = document.querySelector('header') as HTMLElement;
    expect(header).toHaveClass('bg-transparent');
  });

  it('header has sticky positioning class', () => {
    render(<Header />);
    const header = document.querySelector('header') as HTMLElement;
    expect(header).toHaveClass('sticky');
  });
});
