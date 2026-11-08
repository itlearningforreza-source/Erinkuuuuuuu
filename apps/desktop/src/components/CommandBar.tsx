import { useState, useEffect, useRef, useCallback } from 'react';
import { useShortcuts } from '../contexts/ShortcutsContext';

interface Command {
  id: string;
  title: string;
  description: string;
  category: string;
  shortcut?: string;
  action: () => void;
  icon?: React.ReactNode;
}

const COMMANDS: Command[] = [
  { id: 'file.new-watchlist', title: 'New Watchlist', description: 'Create a new watchlist', category: 'File', shortcut: 'Ctrl+N', action: () => console.log('New Watchlist'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg> },
  { id: 'file.new-chart', title: 'New Chart', description: 'Open a new chart panel', category: 'File', shortcut: 'Ctrl+Shift+C', action: () => console.log('New Chart'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg> },
  { id: 'file.new-notebook', title: 'New Notebook', description: 'Create a new research notebook', category: 'File', shortcut: 'Ctrl+Shift+N', action: () => console.log('New Notebook'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 01-2 2H7a2 2 0 01-2-2V5a2 2 0 012-2h2.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H19a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 00-2-2h.008z" /></svg> },
  { id: 'file.save-layout', title: 'Save Layout', description: 'Save current panel layout', category: 'File', shortcut: 'Ctrl+S', action: () => console.log('Save Layout'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8.5a.5.5 0 00-1 0V13a2 2 0 01-2 2H5a2 2 0 01-2-2v-9a2 2 0 012-2h12.5" /></svg> },
  { id: 'file.load-layout', title: 'Load Layout', description: 'Load saved panel layout', category: 'File', shortcut: 'Ctrl+Shift+L', action: () => console.log('Load Layout'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg> },
  { id: 'view.toggle-theme', title: 'Toggle Theme', description: 'Switch between dark and light theme', category: 'View', shortcut: 'Ctrl+T', action: () => console.log('Toggle Theme'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg> },
  { id: 'view.toggle-fullscreen', title: 'Toggle Fullscreen', description: 'Enter/exit fullscreen mode', category: 'View', shortcut: 'F11', action: () => console.log('Toggle Fullscreen'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg> },
  { id: 'view.reset-layout', title: 'Reset Layout', description: 'Reset panel layout to default', category: 'View', shortcut: 'Ctrl+Shift+R', action: () => console.log('Reset Layout'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg> },
  { id: 'tools.valuation', title: 'Run Valuation', description: 'Open valuation engine', category: 'Tools', shortcut: 'Ctrl+V', action: () => console.log('Run Valuation'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> },
  { id: 'tools.portfolio', title: 'Portfolio Manager', description: 'Manage portfolios and positions', category: 'Tools', shortcut: 'Ctrl+P', action: () => console.log('Portfolio Manager'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg> },
  { id: 'tools.risk', title: 'Risk Analysis', description: 'VaR, stress testing, and risk metrics', category: 'Tools', shortcut: 'Ctrl+R', action: () => console.log('Risk Analysis'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg> },
  { id: 'tools.backtest', title: 'Run Backtest', description: 'Execute strategy backtest', category: 'Tools', shortcut: 'Ctrl+B', action: () => console.log('Run Backtest'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg> },
  { id: 'help.shortcuts', title: 'Keyboard Shortcuts', description: 'Show all keyboard shortcuts', category: 'Help', shortcut: 'Ctrl+/', action: () => console.log('Show Shortcuts'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542 7z" /></svg> },
  { id: 'help.documentation', title: 'Documentation', description: 'Open ERIN documentation', category: 'Help', shortcut: 'F1', action: () => console.log('Documentation'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 12 5c2.757 0 4.343 1.477 5 3.5m-10 0v13" /></svg> },
  { id: 'help.about', title: 'About ERIN', description: 'Show version and build info', category: 'Help', action: () => console.log('About'), icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> },
];

export function CommandBar() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filteredCommands, setFilteredCommands] = useState<Command[]>(COMMANDS);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const { registerShortcut } = useShortcuts();

  useEffect(() => {
    registerShortcut('command+k', () => setIsOpen(true), 'Open Command Bar');
    registerShortcut('ctrl+k', () => setIsOpen(true), 'Open Command Bar');
    return () => {};
  }, [registerShortcut]);

  useEffect(() => {
    if (!query.trim()) {
      setFilteredCommands(COMMANDS);
      setSelectedIndex(0);
      return;
    }
    const lowerQuery = query.toLowerCase();
    const filtered = COMMANDS.filter(
      (cmd) =>
        cmd.title.toLowerCase().includes(lowerQuery) ||
        cmd.description.toLowerCase().includes(lowerQuery) ||
        cmd.category.toLowerCase().includes(lowerQuery) ||
        cmd.shortcut?.toLowerCase().includes(lowerQuery)
    );
    setFilteredCommands(filtered);
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          setIsOpen(false);
          setQuery('');
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
            setIsOpen(false);
            setQuery('');
          }
          break;
        case 'Tab':
          e.preventDefault();
          setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
          break;
      }
    },
    [isOpen, filteredCommands, selectedIndex]
  );

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (listRef.current && filteredCommands[selectedIndex]) {
      const item = listRef.current.children[selectedIndex] as HTMLElement;
      item?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, filteredCommands]);

  if (!isOpen) return null;

  const renderCommandItem = (cmd: Command, index: number) => {
    const isSelected = index === selectedIndex;
    const baseClass = 'flex items-center gap-3 px-4 py-2.5 text-sm cursor-pointer transition-colors';
    const selectedClass = 'bg-primary-600/20 text-primary-100';
    const unselectedClass = 'hover:bg-base-800 text-base-300';
    const className = isSelected ? `${baseClass} ${selectedClass}` : `${baseClass} ${unselectedClass}`;

    return (
      <li
        key={cmd.id}
        className={className}
        role="option"
        aria-selected={isSelected}
        onClick={() => { cmd.action(); setIsOpen(false); setQuery(''); }}
      >
        {cmd.icon && <span className="flex-shrink-0 w-5 h-5 text-base-500">{cmd.icon}</span>}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{cmd.title}</span>
            <span className="text-xs text-base-500 uppercase">{cmd.category}</span>
          </div>
          <p className="text-xs text-base-500 truncate">{cmd.description}</p>
        </div>
        {cmd.shortcut && (
          <kbd className="px-2 py-0.5 text-xs text-base-500 bg-base-800 rounded font-mono">
            {cmd.shortcut.replace('Ctrl', 'Ctrl').replace('Shift', 'Shift').replace('Command', 'Cmd').replace('Alt', 'Alt')}
          </kbd>
        )}
      </li>
    );
  };

  return (
    <div className="command-bar-overlay fixed inset-0 z-50 flex items-start justify-center pt-20" onClick={() => setIsOpen(false)}>
      <div className="command-bar w-full max-w-2xl bg-base-900 border border-base-700 rounded-lg shadow-2xl overflow-hidden animate-slide-down" onClick={(e) => e.stopPropagation()}>
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-base-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="w-full pl-10 pr-4 py-3 bg-base-950 border-b border-base-700 text-base-100 placeholder-base-500 text-sm outline-none"
            autoComplete="off"
            spellCheck={false}
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-base-500 bg-base-800 rounded">Cmd+K</kbd>
        </div>
        <ul ref={listRef} className="max-h-96 overflow-y-auto" role="listbox">
          {filteredCommands.length === 0 ? (
            <li className="px-4 py-3 text-center text-base-500 text-sm">No commands found</li>
          ) : (
            filteredCommands.map((cmd, index) => renderCommandItem(cmd, index))
          )}
        </ul>
        <div className="px-4 py-2 border-t border-base-700 text-xs text-base-500"><span>Up/Down navigate Enter select Esc close</span></div>
      </div>
    </div>
  );
}