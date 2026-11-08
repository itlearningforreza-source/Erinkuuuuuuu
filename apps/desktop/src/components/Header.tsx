import { useTheme } from '../contexts/ThemeContext';
import { useLayout } from '../contexts/LayoutContext';

export function Header() {
  const { theme, toggleTheme } = useTheme();
  const { addPanel } = useLayout();

  const handleAddWatchlist = () => {
    addPanel({
      type: 'watchlist',
      title: 'Watchlist',
      position: { x: 0, y: 0, w: 4, h: 6 },
      isVisible: true,
      isFocused: false,
    });
  };

  const handleAddChart = () => {
    addPanel({
      type: 'chart',
      title: 'Chart',
      position: { x: 4, y: 0, w: 8, h: 6 },
      isVisible: true,
      isFocused: false,
    });
  };

  return (
    <header className="terminal-header h-10 px-4 flex items-center justify-between bg-base-900 border-b border-base-800 select-none">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <svg className="w-6 h-6 text-primary-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span className="font-mono font-bold text-lg text-base-100">ERIN</span>
          <span className="text-xs px-2 py-0.5 bg-primary-600 text-primary-100 rounded">v0.1.0</span>
        </div>
        <div className="hidden md:flex items-center gap-1 border-l border-base-800 pl-4">
          <button className="px-3 py-1.5 text-sm hover:bg-base-800 rounded transition-colors" onClick={handleAddWatchlist}>
            + Watchlist
          </button>
          <button className="px-3 py-1.5 text-sm hover:bg-base-800 rounded transition-colors" onClick={handleAddChart}>
            + Chart
          </button>
          <button className="px-3 py-1.5 text-sm hover:bg-base-800 rounded transition-colors">
            + News
          </button>
          <button className="px-3 py-1.5 text-sm hover:bg-base-800 rounded transition-colors">
            + Notebook
          </button>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-base-800 rounded border border-base-700">
          <svg className="w-4 h-4 text-base-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search symbols, commands..."
            className="bg-transparent border-none outline-none text-sm text-base-100 placeholder-base-500 w-64"
          />
        </div>
        <button
          className="p-2 hover:bg-base-800 rounded transition-colors"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
        <button className="p-2 hover:bg-base-800 rounded transition-colors" aria-label="Settings">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
        <div className="w-px h-6 bg-base-700 mx-2" />
        <button className="p-2 hover:bg-base-800 rounded transition-colors" aria-label="Toggle fullscreen">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      </div>
    </header>
  );
}