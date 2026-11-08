import { useRef, useEffect, useState } from 'react';
import type { PanelConfig } from '../contexts/LayoutContext';
import { useLayout } from '../contexts/LayoutContext';
import { cn } from '../utils/cn';

interface PanelProps {
  panel: PanelConfig;
  isActive: boolean;
}

export function Panel({ panel, isActive }: PanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);

  const { updatePanel, movePanel, resizePanel, focusPanel } = useLayout();
  const dragStartRef = useRef({ x: 0, y: 0 });
  const resizeStartRef = useRef({ x: 0, y: 0, w: 0, h: 0 });

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.panel-header')) {
      setIsDragging(true);
      dragStartRef.current = { x: e.clientX, y: e.clientY };
      focusPanel(panel.id);
    }
  };

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    resizeStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      w: panel.position.w,
      h: panel.position.h,
    };
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const dx = e.clientX - dragStartRef.current.x;
        const dy = e.clientY - dragStartRef.current.y;
        movePanel(panel.id, {
          x: panel.position.x + dx,
          y: panel.position.y + dy,
        });
        dragStartRef.current = { x: e.clientX, y: e.clientY };
      } else if (isResizing) {
        const dx = e.clientX - resizeStartRef.current.x;
        const dy = e.clientY - resizeStartRef.current.y;
        resizePanel(panel.id, {
          w: Math.max(panel.minW || 4, resizeStartRef.current.w + dx),
          h: Math.max(panel.minH || 3, resizeStartRef.current.h + dy),
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, panel.id, panel.position.x, panel.position.y, panel.minW, panel.minH]);

  const style: React.CSSProperties = {
    gridColumnStart: panel.position.x + 1,
    gridColumnEnd: `span ${panel.position.w}`,
    gridRowStart: panel.position.y + 1,
    gridRowEnd: `span ${panel.position.h}`,
    zIndex: panel.zIndex,
    opacity: panel.isVisible ? 1 : 0,
    pointerEvents: panel.isVisible ? 'auto' : 'none',
    transition: 'all 0.2s ease',
  };

  return (
    <div
      ref={panelRef}
      className={cn(
        'panel',
        isActive && 'panel-active',
        panel.isVisible ? 'panel-visible' : 'panel-hidden',
        'relative flex flex-col bg-base-900 border border-base-700 rounded-lg overflow-hidden'
      )}
      style={style}
      onMouseDown={handleMouseDown}
    >
      <div
        className="panel-header flex items-center justify-between px-2 py-1 bg-base-800 border-b border-base-700 cursor-move select-none"
      >
        <span className="text-xs font-medium text-base-300 truncate">{panel.title}</span>
        <div className="flex items-center gap-1">
          <button
            className="p-1 hover:bg-base-700 rounded transition-colors"
            onClick={(e) => { e.stopPropagation(); }} // Placeholder for panel actions
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
          <button
            className="p-1 hover:bg-base-700 rounded transition-colors"
            onClick={(e) => { e.stopPropagation(); updatePanel(panel.id, { isVisible: false }); }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      <div className="panel-content flex-1 overflow-hidden relative">
        {renderPanelContent(panel)}
        <div
          className="resize-handle se absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
          onMouseDown={handleResizeMouseDown}
        />
        <div
          className="resize-handle sw absolute bottom-0 left-0 w-4 h-4 cursor-sw-resize"
          onMouseDown={handleResizeMouseDown}
        />
        <div
          className="resize-handle ne absolute top-0 right-0 w-4 h-4 cursor-ne-resize"
          onMouseDown={handleResizeMouseDown}
        />
        <div
          className="resize-handle nw absolute top-0 left-0 w-4 h-4 cursor-nw-resize"
          onMouseDown={handleResizeMouseDown}
        />
      </div>
    </div>
  );
}

import { WatchlistPanel } from './WatchlistPanel';
import { ChartPanel } from './ChartPanel';

function renderPanelContent(panel: PanelConfig) {
  switch (panel.type) {
    case 'watchlist':
      return <WatchlistPanel />;
    case 'chart':
      return <ChartPanel />;
    case 'news':
      return <NewsPanel />;
    case 'notebook':
      return <NotebookPanel />;
    case 'settings':
      return <SettingsPanel />;
    default:
      return <div className="p-4 text-center text-base-500">Panel: {panel.title}</div>;
  }
}

// Placeholder panel components (to be implemented)
function NewsPanel() {
  return (
    <div className="h-full p-4">
      <h3 className="font-medium mb-4">News Feed</h3>
      <div className="space-y-3 text-sm">
        {[
          { title: 'Fed holds rates steady', source: 'Reuters', time: '2h ago' },
          { title: 'Apple reports record earnings', source: 'Bloomberg', time: '4h ago' },
          { title: 'Oil prices surge on supply concerns', source: 'WSJ', time: '6h ago' },
        ].map((news, i) => (
          <div key={i} className="p-3 bg-base-800 rounded border-l-4 border-primary-500">
            <p className="font-medium">{news.title}</p>
            <p className="text-xs text-base-500">{news.source} • {news.time}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function NotebookPanel() {
  return (
    <div className="h-full p-4">
      <h3 className="font-medium mb-4">Research Notebook</h3>
      <div className="h-[calc(100%-3rem)] bg-base-950 rounded p-4 font-mono text-sm text-base-300">
        Jupyter kernel integration here
      </div>
    </div>
  );
}

function SettingsPanel() {
  return (
    <div className="h-full p-4">
      <h3 className="font-medium mb-4">Settings</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Theme</label>
          <select className="w-full p-2 bg-base-800 border border-base-700 rounded">
            <option>Dark</option>
            <option>Light</option>
            <option>System</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Data Provider</label>
          <select className="w-full p-2 bg-base-800 border border-base-700 rounded">
            <option>OpenBB</option>
            <option>yfinance</option>
            <option>Alpha Vantage</option>
          </select>
        </div>
      </div>
    </div>
  );
}