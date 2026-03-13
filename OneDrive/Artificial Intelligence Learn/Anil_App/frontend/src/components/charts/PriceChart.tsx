import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { HistoricalPrice } from '../../types/analysis';

interface PriceChartProps {
  data: HistoricalPrice[];
  currentPrice: number;
}

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y' | 'ALL';

function filterByRange(data: HistoricalPrice[], range: TimeRange): HistoricalPrice[] {
  if (data.length === 0) return [];
  if (range === 'ALL') return data;
  const now = new Date();
  const days: Record<Exclude<TimeRange, 'ALL'>, number> = {
    '1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '5Y': 1825,
  };
  const cutoff = new Date(now.getTime() - days[range] * 24 * 60 * 60 * 1000);
  const cutoffStr = cutoff.toISOString().split('T')[0];
  return data.filter((d) => d.date >= cutoffStr);
}

export function PriceChart({ data, currentPrice: _currentPrice }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const [range, setRange] = useState<TimeRange>('ALL');

  const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));
  const filtered = filterByRange(sorted, range);

  useEffect(() => {
    if (!containerRef.current || filtered.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#78716c',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#f5f5f4' },
        horzLines: { color: '#f5f5f4' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#e7e5e4', autoScale: true },
      timeScale: { borderColor: '#e7e5e4', timeVisible: true, fixLeftEdge: true, fixRightEdge: true },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#059669',
      downColor: '#dc2626',
      borderUpColor: '#059669',
      borderDownColor: '#dc2626',
      wickUpColor: '#059669',
      wickDownColor: '#dc2626',
    });

    candleSeries.setData(
      filtered.map((d) => ({
        time: d.date as `${number}-${number}-${number}`,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })),
    );

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(
      filtered
        .filter((d) => d.volume !== null)
        .map((d) => ({
          time: d.date as `${number}-${number}-${number}`,
          value: d.volume!,
          color: d.close >= d.open ? 'rgba(5, 150, 105, 0.3)' : 'rgba(220, 38, 38, 0.3)',
        })),
    );

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [filtered]);

  const ranges: TimeRange[] = ['1W', '1M', '3M', '6M', '1Y', '5Y', 'ALL'];

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-stone-400">
        No historical price data available
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-lg font-semibold text-stone-900">Price Chart</div>
        <div className="flex gap-1">
          {ranges.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                range === r
                  ? 'bg-indigo-600 text-white'
                  : 'text-stone-500 hover:bg-stone-100'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div
        ref={containerRef}
        className="rounded-xl overflow-hidden border border-stone-200"
      />
    </div>
  );
}
