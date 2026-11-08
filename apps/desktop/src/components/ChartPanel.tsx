import { useEffect, useRef, useState } from 'react';

interface ChartData {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChartPanelProps {
  symbol?: string;
  timeframe?: '1D' | '1W' | '1M' | '3M' | '1Y' | '5Y';
}

export function ChartPanel({ symbol = 'AAPL.US', timeframe = '1D' }: ChartPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChartData = async (sym: string, tf: string): Promise<ChartData[]> => {
    try {
      const response = await fetch(`/api/v1/quotes/${sym}/history?interval=${tf}&limit=500`);
      if (!response.ok) throw new Error('Failed to fetch chart data');
      const data = await response.json();
      return data.bars || [];
    } catch (err) {
      console.error('Failed to fetch chart data:', err);
      return [];
    }
  };

  const loadChart = async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchChartData(symbol, timeframe);
      if (data.length > 0 && seriesRef.current) {
        seriesRef.current.setData(data.map(d => ({
          time: d.time,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        })));
      }
    } catch (err) {
      setError('Failed to load chart data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Dynamically import Lightweight Charts
    const initChart = async () => {
      try {
        const { createChart } = await import('lightweight-charts');
        
        if (!containerRef.current) return;
        
        const chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
          layout: {
            background: { color: '#0d1117' },
            textColor: '#e4e4e7',
          },
          grid: {
            vertLines: { color: '#1f2937' },
            horzLines: { color: '#1f2937' },
          },
          crosshair: {
            mode: 1, // CrosshairMode.Normal
          },
          rightPriceScale: {
            borderColor: '#1f2937',
          },
          timeScale: {
            borderColor: '#1f2937',
            timeVisible: true,
            secondsVisible: false,
          },
        });
        
        const series = chart.addCandlestickSeries({
          upColor: '#22c55e',
          downColor: '#ef4444',
          borderUpColor: '#22c55e',
          borderDownColor: '#ef4444',
          wickUpColor: '#22c55e',
          wickDownColor: '#ef4444',
        });
        
        chartRef.current = chart;
        seriesRef.current = series;
        
        // Handle resize
        const resizeObserver = new ResizeObserver(() => {
          if (containerRef.current && chartRef.current) {
            chartRef.current.applyOptions({
              width: containerRef.current.clientWidth,
              height: containerRef.current.clientHeight,
            });
          }
        });
        
        if (containerRef.current) {
          resizeObserver.observe(containerRef.current);
        }
        
        await loadChart();
      } catch (err) {
        console.error('Failed to initialize chart:', err);
        setError('Failed to initialize chart');
      } finally {
        setLoading(false);
      }
    };
    
    initChart();
    
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [symbol, timeframe]);

  useEffect(() => {
    loadChart();
  }, [symbol, timeframe]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-base-950">
        <div className="text-center text-base-500">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent mx-auto mb-2"></div>
          <p className="text-sm">Loading chart...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-base-950 text-red-400">
        <p className="text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-full bg-base-950 rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b border-base-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <select
            value={symbol}
            onChange={(e) => window.dispatchEvent(new CustomEvent('chart-symbol-change', { detail: e.target.value }))}
            className="px-2 py-1 bg-base-800 border border-base-700 rounded text-sm text-base-100 bg-base-800"
          >
            <option value="AAPL.US">AAPL.US</option>
            <option value="MSFT.US">MSFT.US</option>
            <option value="GOOGL.US">GOOGL.US</option>
            <option value="AMZN.US">AMZN.US</option>
            <option value="TSLA.US">TSLA.US</option>
            <option value="NVDA.US">NVDA.US</option>
            <option value="META.US">META.US</option>
          </select>
          <select
            value={timeframe}
            onChange={(e) => window.dispatchEvent(new CustomEvent('chart-timeframe-change', { detail: e.target.value }))}
            className="px-2 py-1 bg-base-800 border border-base-700 rounded text-sm text-base-100 bg-base-800 ml-2"
          >
            <option value="1D">1D</option>
            <option value="1W">1W</option>
            <option value="1M">1M</option>
            <option value="3M">3M</option>
            <option value="1Y">1Y</option>
            <option value="5Y">5Y</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-2 py-1 text-xs bg-base-800 hover:bg-base-700 rounded">Candle</button>
          <button className="px-2 py-1 text-xs bg-base-800 hover:bg-base-700 rounded">Line</button>
          <button className="px-2 py-1 text-xs bg-base-800 hover:bg-base-700 rounded">Area</button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="w-full h-[calc(100%-3rem)]"
        style={{ minHeight: 300 }}
      />
    </div>
  );
}