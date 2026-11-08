import React from 'react';
import { TerminalLayout } from './layouts/TerminalLayout';
import { CommandBar } from './components/CommandBar';
import { ThemeProvider } from './contexts/ThemeContext';
import { ShortcutsProvider } from './contexts/ShortcutsContext';
import { LayoutProvider } from './contexts/LayoutContext';
import { useTheme } from './contexts/ThemeContext';
import { useShortcuts as useShortcutsHook } from './contexts/ShortcutsContext';

function AppContent() {
  const { theme } = useTheme();
  const { registerShortcut } = useShortcutsHook();

  // Register global shortcuts
  React.useEffect(() => {
    registerShortcut('command+k', () => {}, 'Open Command Bar');
    registerShortcut('ctrl+k', () => {}, 'Open Command Bar');
    registerShortcut('command+shift+k', () => {}, 'Open Command History');
    registerShortcut('f11', () => {}, 'Toggle Fullscreen');
  }, [registerShortcut]);

  return (
    <div className={`erin-app ${theme}`} data-theme={theme}>
      <TerminalLayout />
      <CommandBar />
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <ShortcutsProvider>
        <LayoutProvider>
          <AppContent />
        </LayoutProvider>
      </ShortcutsProvider>
    </ThemeProvider>
  );
}