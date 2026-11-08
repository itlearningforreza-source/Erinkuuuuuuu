import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface PanelConfig {
  id: string;
  type: 'watchlist' | 'chart' | 'news' | 'notebook' | 'settings' | 'custom';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
  isVisible: boolean;
  isFocused: boolean;
  zIndex: number;
  props?: Record<string, any>;
}

interface LayoutState {
  panels: PanelConfig[];
  activePanelId: string | null;
  gridCols: number;
  gridRows: number;
  compact: boolean;
}

interface LayoutContextType {
  state: LayoutState;
  addPanel: (panel: Omit<PanelConfig, 'id' | 'zIndex'>) => string;
  removePanel: (id: string) => void;
  updatePanel: (id: string, updates: Partial<PanelConfig>) => void;
  movePanel: (id: string, position: { x: number; y: number }) => void;
  resizePanel: (id: string, size: { w: number; h: number }) => void;
  focusPanel: (id: string) => void;
  saveLayout: () => void;
  loadLayout: () => void;
  resetLayout: () => void;
}

const LayoutContext = createContext<LayoutContextType | undefined>(undefined);

const DEFAULT_LAYOUT: LayoutState = {
  panels: [],
  activePanelId: null,
  gridCols: 12,
  gridRows: 10,
  compact: true,
};

export function LayoutProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<LayoutState>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('erin-layout');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          return DEFAULT_LAYOUT;
        }
      }
    }
    return DEFAULT_LAYOUT;
  });

  // Persist layout changes
  useEffect(() => {
    localStorage.setItem('erin-layout', JSON.stringify(state));
  }, [state]);

  const addPanel = useCallback((panel: Omit<PanelConfig, 'id' | 'zIndex'>) => {
    const id = crypto.randomUUID();
    const newPanel: PanelConfig = {
      ...panel,
      id,
      zIndex: Date.now(),
    };
    setState((prev) => ({
      ...prev,
      panels: [...prev.panels, newPanel],
      activePanelId: newPanel.id,
    }));
    return id;
  }, []);

  const removePanel = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      panels: prev.panels.filter((p) => p.id !== id),
      activePanelId: prev.activePanelId === id ? null : prev.activePanelId,
    }));
  }, []);

  const updatePanel = useCallback((id: string, updates: Partial<PanelConfig>) => {
    setState((prev) => ({
      ...prev,
      panels: prev.panels.map((p) => (p.id === id ? { ...p, ...updates } : p)),
    }));
  }, []);

  const movePanel = useCallback((id: string, position: { x: number; y: number }) => {
    updatePanel(id, { position } as Partial<PanelConfig>);
  }, [updatePanel]);

  const resizePanel = useCallback((id: string, size: { w: number; h: number }) => {
    updatePanel(id, { position: { ...size, x: 0, y: 0 } } as Partial<PanelConfig>);
  }, [updatePanel]);

  const focusPanel = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      activePanelId: id,
      panels: prev.panels.map((p) =>
        p.id === id ? { ...p, zIndex: Date.now(), isFocused: true } : { ...p, isFocused: false }
      ),
    }));
  }, []);

  const saveLayout = useCallback(() => {
    localStorage.setItem('erin-layout', JSON.stringify(state));
  }, [state]);

  const loadLayout = useCallback(() => {
    const saved = localStorage.getItem('erin-layout');
    if (saved) {
      try {
        setState(JSON.parse(saved));
      } catch {
        setState(DEFAULT_LAYOUT);
      }
    }
  }, []);

  const resetLayout = useCallback(() => {
    setState(DEFAULT_LAYOUT);
    localStorage.removeItem('erin-layout');
  }, []);

  return (
    <LayoutContext.Provider
      value={{
        state,
        addPanel,
        removePanel,
        updatePanel,
        movePanel,
        resizePanel,
        focusPanel,
        saveLayout,
        loadLayout,
        resetLayout,
      }}
    >
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayout() {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error('useLayout must be used within a LayoutProvider');
  }
  return context;
}