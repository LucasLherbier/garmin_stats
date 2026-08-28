/** Shared chart styling — purple bars on dark cards, orange for key metrics. */

export const CHART = {
  accent: '#ff6b2c',
  accentBright: '#ff8f5c',
  accentMid: '#ff6b2c',
  accentDeep: '#e85d04',
  accentDim: 'rgba(255, 107, 44, 0.35)',
  accentFill: 'rgba(255, 107, 44, 0.18)',
  chart: '#a78bfa',
  chartBright: '#c4b5fd',
  chartMid: '#8b5cf6',
  chartDeep: '#6366f1',
  chartFill: 'rgba(167, 139, 250, 0.18)',
  grid: 'rgba(255, 255, 255, 0.06)',
  tick: '#9ca3af',
  tooltipBg: 'rgba(28, 28, 30, 0.96)',
  tooltipBorder: 'rgba(255, 255, 255, 0.1)',
  swim: '#2dd4bf',
  bike: '#ff6b2c',
  run: '#a78bfa',
  secondary: '#a3a3a3',
  route: '#ff6b2c',
} as const;

export const tooltipStyle = {
  background: CHART.tooltipBg,
  border: `1px solid ${CHART.tooltipBorder}`,
  borderRadius: 14,
  fontSize: 12,
  color: '#fff',
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
};

export function formatChartValue(value: number, decimals = 1): string {
  if (!Number.isFinite(value)) return '0';
  if (Math.abs(value) >= 100) return value.toFixed(0);
  return value.toFixed(decimals);
}
