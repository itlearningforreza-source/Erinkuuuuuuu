import { useLayout } from '../contexts/LayoutContext';
import { Panel } from '../components/Panel';
import { Header } from '../components/Header';
import { StatusBar } from '../components/StatusBar';
import { useTheme } from '../contexts/ThemeContext';

export function TerminalLayout() {
  const { state } = useLayout();
  const { theme } = useTheme();

  return (
    <div className={`terminal-layout ${theme}`}>
      <Header />
      <div className="terminal-main">
        <div className="terminal-grid" style={{ gridTemplateColumns: `repeat(${state.gridCols}, 1fr)`, gridTemplateRows: `repeat(${state.gridRows}, 1fr)` }}>
          {state.panels.map((panel) => (
            <Panel
              key={panel.id}
              panel={panel}
              isActive={state.activePanelId === panel.id}
            />
          ))}
        </div>
      </div>
      <StatusBar />
    </div>
  );
}