/**
 * Tests for useStockSearch hook.
 *
 * Uses renderHook from @testing-library/react to exercise state transitions
 * without needing a full component tree.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStockSearch } from '../../hooks/useStockSearch';
import { searchStocks } from '../../services/stockApi';
import type { SearchResult } from '../../types/analysis';

vi.mock('../../services/stockApi', () => ({
  searchStocks: vi.fn(),
}));

const mockedSearchStocks = vi.mocked(searchStocks);

const noop = vi.fn();

describe('useStockSearch', () => {
  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  it('initialises query as an empty string', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(result.current.query).toBe('');
  });

  it('exposes setQuery function', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(typeof result.current.setQuery).toBe('function');
  });

  it('exposes close function', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(typeof result.current.close).toBe('function');
  });

  it('exposes isOpen as false initially', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(result.current.isOpen).toBe(false);
  });

  it('exposes suggestions as empty array initially', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(result.current.suggestions).toEqual([]);
  });

  it('exposes selectedIndex as -1 initially', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(result.current.selectedIndex).toBe(-1);
  });

  // -------------------------------------------------------------------------
  // setQuery
  // -------------------------------------------------------------------------

  it('updates query via setQuery', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => {
      result.current.setQuery('AAPL');
    });

    expect(result.current.query).toBe('AAPL');
  });

  it('setQuery can set an arbitrary string value', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => {
      result.current.setQuery('Microsoft Corporation');
    });

    expect(result.current.query).toBe('Microsoft Corporation');
  });

  it('setQuery can set an empty string (explicit clear)', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => {
      result.current.setQuery('TSLA');
    });
    act(() => {
      result.current.setQuery('');
    });

    expect(result.current.query).toBe('');
  });

  // -------------------------------------------------------------------------
  // close
  // -------------------------------------------------------------------------

  it('close resets isOpen to false and selectedIndex to -1', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => {
      result.current.close();
    });

    expect(result.current.isOpen).toBe(false);
    expect(result.current.selectedIndex).toBe(-1);
  });

  it('close is a stable reference (useCallback — same ref across renders)', () => {
    const { result, rerender } = renderHook(() => useStockSearch(noop));

    const firstRef = result.current.close;
    rerender();
    const secondRef = result.current.close;

    expect(firstRef).toBe(secondRef);
  });

  // -------------------------------------------------------------------------
  // Min query length behaviour
  // -------------------------------------------------------------------------

  it('clears suggestions when query is empty (below min length)', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => { result.current.setQuery(''); });

    expect(result.current.suggestions).toEqual([]);
    expect(result.current.isOpen).toBe(false);
  });

  it('keeps suggestions state intact for a single-character query', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => { result.current.setQuery('A'); });

    // Query is set — debounced fetch will trigger (not instant)
    expect(result.current.query).toBe('A');
  });

  it('exposes isSearching as false initially', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(result.current.isSearching).toBe(false);
  });

  it('exposes handleKeyDown as a function', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(typeof result.current.handleKeyDown).toBe('function');
  });

  it('exposes selectSuggestion as a function', () => {
    const { result } = renderHook(() => useStockSearch(noop));
    expect(typeof result.current.selectSuggestion).toBe('function');
  });

  // -------------------------------------------------------------------------
  // Multiple sequential updates
  // -------------------------------------------------------------------------

  it('tracks multiple sequential setQuery updates correctly', () => {
    const { result } = renderHook(() => useStockSearch(noop));

    act(() => { result.current.setQuery('A'); });
    expect(result.current.query).toBe('A');

    act(() => { result.current.setQuery('AA'); });
    expect(result.current.query).toBe('AA');

    act(() => { result.current.setQuery('AAP'); });
    expect(result.current.query).toBe('AAP');

    act(() => { result.current.setQuery('AAPL'); });
    expect(result.current.query).toBe('AAPL');
  });
});

// ---------------------------------------------------------------------------
// Helpers shared by timer-driven tests
// ---------------------------------------------------------------------------

const RESULTS: SearchResult[] = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'AAPLX', name: 'Apple Extended' },
];

/** Render hook, type query, and advance the debounce timer. */
async function renderWithSuggestions(onSelect = vi.fn()) {
  const hook = renderHook(() => useStockSearch(onSelect));

  mockedSearchStocks.mockResolvedValueOnce(RESULTS);

  await act(async () => {
    hook.result.current.setQuery('AAPL');
  });

  await act(async () => {
    vi.advanceTimersByTime(300);
  });

  return hook;
}

// ---------------------------------------------------------------------------
// Debounced search
// ---------------------------------------------------------------------------

describe('useStockSearch — debounced search', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedSearchStocks.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls searchStocks after 300 ms debounce', async () => {
    mockedSearchStocks.mockResolvedValueOnce(RESULTS);

    const { result } = renderHook(() => useStockSearch(noop));

    await act(async () => { result.current.setQuery('AAPL'); });

    expect(mockedSearchStocks).not.toHaveBeenCalled();

    await act(async () => { vi.advanceTimersByTime(300); });

    expect(mockedSearchStocks).toHaveBeenCalledOnce();
    expect(mockedSearchStocks).toHaveBeenCalledWith('AAPL');
  });

  it('does not call searchStocks before the debounce window elapses', async () => {
    mockedSearchStocks.mockResolvedValueOnce(RESULTS);

    const { result } = renderHook(() => useStockSearch(noop));

    await act(async () => { result.current.setQuery('AAPL'); });
    await act(async () => { vi.advanceTimersByTime(299); });

    expect(mockedSearchStocks).not.toHaveBeenCalled();
  });

  it('populates suggestions and opens dropdown on successful search', async () => {
    const { result } = await renderWithSuggestions();

    expect(result.current.suggestions).toEqual(RESULTS);
    expect(result.current.isOpen).toBe(true);
    expect(result.current.selectedIndex).toBe(-1);
  });

  it('sets isSearching to true during the async call and false after', async () => {
    let resolveSearch!: (value: SearchResult[]) => void;
    mockedSearchStocks.mockReturnValueOnce(
      new Promise<SearchResult[]>((res) => { resolveSearch = res; })
    );

    const { result } = renderHook(() => useStockSearch(noop));

    await act(async () => { result.current.setQuery('TSLA'); });
    await act(async () => { vi.advanceTimersByTime(300); });

    // isSearching should be true while the promise is in-flight
    expect(result.current.isSearching).toBe(true);

    await act(async () => { resolveSearch(RESULTS); });

    expect(result.current.isSearching).toBe(false);
  });

  it('clears suggestions and sets isSearching to false when searchStocks rejects', async () => {
    mockedSearchStocks.mockRejectedValueOnce(new Error('network error'));

    const { result } = renderHook(() => useStockSearch(noop));

    await act(async () => { result.current.setQuery('AAPL'); });
    await act(async () => { vi.advanceTimersByTime(300); });

    expect(result.current.suggestions).toEqual([]);
    expect(result.current.isSearching).toBe(false);
  });

  it('keeps isOpen false when searchStocks resolves with an empty array', async () => {
    mockedSearchStocks.mockResolvedValueOnce([]);

    const { result } = renderHook(() => useStockSearch(noop));

    await act(async () => { result.current.setQuery('ZZZNOMATCH'); });
    await act(async () => { vi.advanceTimersByTime(300); });

    expect(result.current.isOpen).toBe(false);
    expect(result.current.suggestions).toEqual([]);
  });

  it('debounces rapid successive keystrokes — only one network call', async () => {
    mockedSearchStocks.mockResolvedValue(RESULTS);

    const { result } = renderHook(() => useStockSearch(noop));

    await act(async () => { result.current.setQuery('A'); });
    await act(async () => { vi.advanceTimersByTime(100); });
    await act(async () => { result.current.setQuery('AA'); });
    await act(async () => { vi.advanceTimersByTime(100); });
    await act(async () => { result.current.setQuery('AAPL'); });
    await act(async () => { vi.advanceTimersByTime(300); });

    expect(mockedSearchStocks).toHaveBeenCalledOnce();
    expect(mockedSearchStocks).toHaveBeenCalledWith('AAPL');
  });

  it('resets suggestions and closes dropdown when query is cleared after a search', async () => {
    const { result } = await renderWithSuggestions();

    expect(result.current.isOpen).toBe(true);

    await act(async () => { result.current.setQuery(''); });

    expect(result.current.suggestions).toEqual([]);
    expect(result.current.isOpen).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// selectSuggestion
// ---------------------------------------------------------------------------

describe('useStockSearch — selectSuggestion', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedSearchStocks.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('sets query to the selected symbol', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    await act(async () => { result.current.selectSuggestion(0); });

    expect(result.current.query).toBe('AAPL');
  });

  it('closes the dropdown after selection', async () => {
    const { result } = await renderWithSuggestions();

    await act(async () => { result.current.selectSuggestion(0); });

    expect(result.current.isOpen).toBe(false);
    expect(result.current.selectedIndex).toBe(-1);
  });

  it('calls onSelect with the item symbol', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    await act(async () => { result.current.selectSuggestion(0); });

    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledWith('AAPL');
  });

  it('selects the second suggestion when index is 1', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    await act(async () => { result.current.selectSuggestion(1); });

    expect(result.current.query).toBe('AAPLX');
    expect(onSelect).toHaveBeenCalledWith('AAPLX');
  });

  it('does nothing for an out-of-bounds index', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    await act(async () => { result.current.selectSuggestion(99); });

    expect(onSelect).not.toHaveBeenCalled();
    // isOpen stays true — nothing changed
    expect(result.current.isOpen).toBe(true);
  });

  it('does nothing for a negative index', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    await act(async () => { result.current.selectSuggestion(-1); });

    expect(onSelect).not.toHaveBeenCalled();
    expect(result.current.isOpen).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// handleKeyDown
// ---------------------------------------------------------------------------

describe('useStockSearch — handleKeyDown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedSearchStocks.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function makeKeyEvent(key: string) {
    return { key, preventDefault: vi.fn() } as unknown as React.KeyboardEvent;
  }

  it('ArrowDown increments selectedIndex', async () => {
    const { result } = await renderWithSuggestions();

    const event = makeKeyEvent('ArrowDown');
    await act(async () => { result.current.handleKeyDown(event); });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(result.current.selectedIndex).toBe(0);
  });

  it('ArrowDown wraps from last item back to index 0', async () => {
    const { result } = await renderWithSuggestions();

    // RESULTS has 2 items; -1 → 0 → 1 → wraps to 0
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowDown')); });
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowDown')); });
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowDown')); });

    expect(result.current.selectedIndex).toBe(0);
  });

  it('ArrowUp from index 0 wraps to the last item', async () => {
    const { result } = await renderWithSuggestions();

    const event = makeKeyEvent('ArrowUp');
    await act(async () => { result.current.handleKeyDown(event); });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(result.current.selectedIndex).toBe(RESULTS.length - 1);
  });

  it('ArrowUp decrements selectedIndex when not at 0', async () => {
    const { result } = await renderWithSuggestions();

    // -1 → 0 → 1
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowDown')); });
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowDown')); });
    expect(result.current.selectedIndex).toBe(1);

    // 1 → 0
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowUp')); });
    expect(result.current.selectedIndex).toBe(0);
  });

  it('Enter calls selectSuggestion for the highlighted item', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    // Highlight first item
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('ArrowDown')); });

    const event = makeKeyEvent('Enter');
    await act(async () => { result.current.handleKeyDown(event); });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledWith('AAPL');
    expect(result.current.isOpen).toBe(false);
  });

  it('Enter does nothing when selectedIndex is -1 (no item highlighted)', async () => {
    const onSelect = vi.fn();
    const { result } = await renderWithSuggestions(onSelect);

    // selectedIndex is -1 — no item highlighted yet
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('Enter')); });

    expect(onSelect).not.toHaveBeenCalled();
    expect(result.current.isOpen).toBe(true);
  });

  it('Escape closes the dropdown', async () => {
    const { result } = await renderWithSuggestions();

    await act(async () => { result.current.handleKeyDown(makeKeyEvent('Escape')); });

    expect(result.current.isOpen).toBe(false);
    expect(result.current.selectedIndex).toBe(-1);
  });

  it('unrecognised keys are ignored without state change', async () => {
    const { result } = await renderWithSuggestions();

    const before = result.current.selectedIndex;
    await act(async () => { result.current.handleKeyDown(makeKeyEvent('Tab')); });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.selectedIndex).toBe(before);
  });

  it('all keyboard handlers are no-ops when dropdown is closed', async () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useStockSearch(onSelect));

    // isOpen is false, suggestions is empty
    for (const key of ['ArrowDown', 'ArrowUp', 'Enter', 'Escape']) {
      await act(async () => { result.current.handleKeyDown(makeKeyEvent(key)); });
    }

    expect(onSelect).not.toHaveBeenCalled();
    expect(result.current.isOpen).toBe(false);
  });
});
