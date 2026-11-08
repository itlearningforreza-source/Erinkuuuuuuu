import { useState, useEffect, useCallback } from 'react';

interface WatchlistItem {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  lastUpdate: string;
}

export function WatchlistPanel() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newSymbol, setNewSymbol] = useState('');

  const fetchQuotes = useCallback(async (symbols: string[]) => {
    try {
      const response = await fetch(`/api/v1/quotes?symbols=${symbols.join(',')}`);
      if (!response.ok) throw new Error('Failed to fetch quotes');
      const data = await response.json();
      return data.quotes || {};
    } catch (err) {
      console.error('Failed to fetch quotes:', err);
      return {};
    }
  }, []);

  const loadWatchlist = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const defaultSymbols = ['AAPL.US', 'MSFT.US', 'GOOGL.US', 'AMZN.US', 'TSLA.US', 'META.US', 'NVDA.US', 'JPM.US'];
      const quotes = await fetchQuotes(defaultSymbols);
      
      const newItems: WatchlistItem[] = defaultSymbols.map(symbol => {
        const quote = quotes[symbol];
        if (quote) {
          return {
            symbol: quote.symbol,
            name: quote.name || symbol,
            price: quote.last || 0,
            change: quote.change || 0,
            changePercent: quote.changePercent || 0,
            volume: quote.volume || 0,
            lastUpdate: quote.timestamp || new Date().toISOString(),
          };
        }
        return {
          symbol,
          name: symbol,
          price: 0,
          change: 0,
          changePercent: 0,
          volume: 0,
          lastUpdate: new Date().toISOString(),
        };
      });
      
      setItems(newItems);
    } catch (err) {
      setError('Failed to load watchlist');
    } finally {
      setLoading(false);
    }
  }, [fetchQuotes]);

  const addSymbol = useCallback(async () => {
    if (!newSymbol.trim()) return;
    const symbol = newSymbol.trim().toUpperCase();
    if (items.some(item => item.symbol === symbol)) return;
    
    setNewSymbol('');
    await loadWatchlist();
  }, [newSymbol, items, loadWatchlist]);

  const removeSymbol = useCallback((symbol: string) => {
    setItems(prev => prev.filter(item => item.symbol !== symbol));
  }, []);

  useEffect(() => {
    loadWatchlist();
    const interval = setInterval(loadWatchlist, 30000);
    return () => clearInterval(interval);
  }, [loadWatchlist]);

  const formatChange = (change: number, percent: number) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)} (${sign}${percent.toFixed(2)}%)`;
  };

  const renderItem = (item: WatchlistItem) => (
    <div key={item.symbol} className="flex items-center justify-between p-2 bg-base-800 rounded hover:bg-base-700/50 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <span className="font-mono font-medium text-sm truncate max-w-[100px]">{item.symbol}</span>
        <span className="text-xs text-base-500 truncate max-w-[120px]">{item.name}</span>
      </div>
      <div className="flex items-center gap-4 text-right">
        <span className="font-mono text-sm">{item.price > 0 ? `$${item.price.toFixed(2)}` : '—'}</span>
        <span className="font-mono text-sm"> {formatChange(item.change, item.changePercent)}</span>
        <span className="text-xs text-base-500 font-mono">Vol: {item.volume > 0 ? (item.volume / 1e6).toFixed(1) + 'M' : '—'}</span>
        <button onClick={() => removeSymbol(item.symbol)} className="p-1 hover:bg-base-700 rounded text-base-500 hover:text-red-400 transition-colors" aria-label="Remove from watchlist">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </div>
  );

  return (
    <div className="h-full p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-medium">Watchlist</h3>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addSymbol()}
            placeholder="Add symbol (e.g., AAPL.US)"
            className="px-2 py-1 bg-base-800 border border-base-700 rounded text-sm text-base-100 placeholder-base-500 w-40"
            autoComplete="off"
          />
          <button onClick={addSymbol} disabled={!newSymbol.trim()} className="px-2 py-1 text-xs bg-primary-600 hover:bg-primary-700 rounded disabled:opacity-50">Add</button>
        </div>
      </div>
      
      {error && (
        <div className="mb-4 p-2 bg-danger-600/20 border border-danger-600 rounded text-sm text-danger-400">
          {error}
        </div>
      )}
      
      {loading && items.length === 0 ? (
        <div className="flex items-center justify-center h-[calc(100%-3rem)] text-base-500">
          Loading watchlist...
        </div>
      ) : (
        <div className="space-y-1 overflow-y-auto h-[calc(100%-3rem)]">
          {items.length === 0 ? (
            <div className="text-center text-base-500 py-8">
              No symbols in watchlist. Add a symbol to get started.
            </div>
          ) : (
            items.map(renderItem)
          )}
        </div>
      )}
    </div>
  );
}