import { useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { useStockStore } from '../../stores/stockStore';
import { useStockSearch } from '../../hooks/useStockSearch';

export function StockSearchBar() {
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isLoading = useStockStore((s) => s.isLoading);

  const {
    query,
    setQuery,
    suggestions,
    selectedIndex,
    isOpen,
    isSearching,
    handleKeyDown: handleSuggestionKeyDown,
    selectSuggestion,
    close,
  } = useStockSearch((symbol) => {
    if (!isLoading) {
      useStockStore.getState().fetchAnalysis(symbol);
    }
  });

  const handleSubmit = (): void => {
    const ticker = query.trim().toUpperCase();
    if (ticker.length > 0 && !isLoading) {
      close();
      useStockStore.getState().fetchAnalysis(ticker);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter' && selectedIndex < 0) {
      handleSubmit();
      return;
    }
    handleSuggestionKeyDown(e);
    if (e.key === 'Escape' && !isOpen) {
      inputRef.current?.blur();
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        close();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [close]);

  return (
    <div className="relative">
      <div className="flex items-center bg-stone-100 border border-stone-300 rounded-lg px-3 py-2 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-colors">
        <Search size={18} className="text-stone-400 shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search stocks — type to see suggestions (e.g., A for Apple)"
          className="bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400 ml-2 w-full text-sm"
        />
        {isLoading || isSearching ? (
          <Loader2 size={16} className="text-indigo-500 animate-spin shrink-0" />
        ) : (
          <button
            onClick={handleSubmit}
            className="text-stone-400 hover:text-indigo-600 transition-colors shrink-0"
            aria-label="Search"
          >
            <Search size={16} />
          </button>
        )}
      </div>

      {isOpen && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 mt-1 w-full bg-white border border-stone-200 rounded-lg shadow-lg overflow-hidden"
        >
          {suggestions.map((item, i) => (
            <button
              key={item.symbol}
              type="button"
              className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between transition-colors ${
                i === selectedIndex
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'hover:bg-stone-50 text-stone-700'
              }`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => selectSuggestion(i)}
              onMouseEnter={() => undefined}
            >
              <span className="truncate">{item.name}</span>
              <span className="ml-2 font-mono text-xs font-semibold text-stone-400 shrink-0">
                {item.symbol}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
