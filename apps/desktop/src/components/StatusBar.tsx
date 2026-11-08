import { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';

export function StatusBar() {
  const { theme } = useTheme();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <footer className="terminal-statusbar h-7 px-4 flex items-center justify-between bg-base-900 border-t border-base-800 select-none text-xs">
      <div className="flex items-center gap-4">
        <span className="text-base-500">Ready</span>
        <span className="text-base-500">|</span>
        <span className="text-base-500 font-mono">ERIN v0.1.0-dev</span>
        <span className="text-base-500">|</span>
        <span className="text-base-500 font-mono">Mode: {theme}</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-base-500 font-mono">
          {time.toLocaleTimeString()}
        </span>
        <span className="text-base-500">|</span>
        <span className="flex items-center gap-1 text-green-400">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span>Connected</span>
        </span>
      </div>
    </footer>
  );
}