import React, { createContext, useContext, useCallback, useRef, useEffect } from 'react';

interface ShortcutAction {
  id: string;
  keys: string;
  description: string;
  action: () => void;
  scope?: 'global' | 'panel' | 'modal';
}

interface ShortcutsContextType {
  registerShortcut: (keys: string, action: () => void, description: string, scope?: 'global' | 'panel' | 'modal') => void;
  unregisterShortcut: (keys: string) => void;
  getShortcuts: () => ShortcutAction[];
}

const ShortcutsContext = createContext<ShortcutsContextType | undefined>(undefined);

export function ShortcutsProvider({ children }: { children: React.ReactNode }) {
  const shortcutsRef = useRef<Map<string, ShortcutAction>>(new Map());

  const registerShortcut = useCallback((
    keys: string,
    action: () => void,
    description: string,
    scope: 'global' | 'panel' | 'modal' = 'global'
  ) => {
    const normalizedKeys = keys.toLowerCase().replace(/\s+/g, '');
    shortcutsRef.current.set(normalizedKeys, {
      id: crypto.randomUUID(),
      keys: normalizedKeys,
      description,
      action,
      scope,
    });
  }, []);

  const unregisterShortcut = useCallback((keys: string) => {
    const normalizedKeys = keys.toLowerCase().replace(/\s+/g, '');
    shortcutsRef.current.delete(normalizedKeys);
  }, []);

  const getShortcuts = useCallback(() => {
    return Array.from(shortcutsRef.current.values());
  }, []);

  // Global keydown handler
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      const keys = [
        event.metaKey ? 'command' : '',
        event.ctrlKey ? 'ctrl' : '',
        event.altKey ? 'alt' : '',
        event.shiftKey ? 'shift' : '',
        event.key.toLowerCase(),
      ].filter(Boolean).join('+');

      const shortcut = shortcutsRef.current.get(keys);
      if (shortcut && (shortcut.scope === 'global' || shortcut.scope === 'panel')) {
        event.preventDefault();
        event.stopPropagation();
        shortcut.action();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <ShortcutsContext.Provider value={{ registerShortcut, unregisterShortcut, getShortcuts }}>
      {children}
    </ShortcutsContext.Provider>
  );
}

export function useShortcuts() {
  const context = useContext(ShortcutsContext);
  if (!context) {
    throw new Error('useShortcuts must be used within a ShortcutsProvider');
  }
  return context;
}