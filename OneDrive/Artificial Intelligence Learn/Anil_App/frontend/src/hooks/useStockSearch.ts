import { useCallback, useEffect, useRef, useState } from 'react';
import type { SearchResult } from '../types/analysis';
import { searchStocks } from '../services/stockApi';

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 1;

interface UseStockSearchReturn {
  query: string;
  setQuery: (value: string) => void;
  suggestions: SearchResult[];
  selectedIndex: number;
  isOpen: boolean;
  isSearching: boolean;
  handleKeyDown: (e: React.KeyboardEvent) => void;
  selectSuggestion: (index: number) => void;
  close: () => void;
}

export function useStockSearch(
  onSelect: (symbol: string) => void,
): UseStockSearchReturn {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced search effect
  useEffect(() => {
    const trimmed = query.trim();

    if (trimmed.length < MIN_QUERY_LENGTH) {
      setSuggestions([]);
      setIsOpen(false);
      setSelectedIndex(-1);
      return;
    }

    // Cancel previous timer
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      // Cancel in-flight request
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      setIsSearching(true);
      try {
        const results = await searchStocks(trimmed);
        setSuggestions(results);
        setIsOpen(results.length > 0);
        setSelectedIndex(-1);
      } catch {
        // Silently ignore — user keeps typing
        setSuggestions([]);
      } finally {
        setIsSearching(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  const close = useCallback(() => {
    setIsOpen(false);
    setSelectedIndex(-1);
  }, []);

  const selectSuggestion = useCallback(
    (index: number) => {
      const item = suggestions[index];
      if (!item) return;
      setQuery(item.symbol);
      close();
      onSelect(item.symbol);
    },
    [suggestions, close, onSelect],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen || suggestions.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : 0,
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : suggestions.length - 1,
        );
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        selectSuggestion(selectedIndex);
      } else if (e.key === 'Escape') {
        close();
      }
    },
    [isOpen, suggestions.length, selectedIndex, selectSuggestion, close],
  );

  return {
    query,
    setQuery,
    suggestions,
    selectedIndex,
    isOpen,
    isSearching,
    handleKeyDown,
    selectSuggestion,
    close,
  };
}
