import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import { ExplorerStatBlock } from './ExplorerStatBlock';
import { SegmentedControl } from './SegmentedControl';
import { VolumeChart } from './VolumeChart';
import { YearCompareChart } from './YearCompareChart';
import type { HomeYtdResponse, OverviewSport, YearCompareResponse } from '../types';
import { formatDistance, formatDurationChart } from '../utils/format';

const HISTORY_YEAR_MIN = 2020;

const HISTORY_SPORT_OPTIONS: Array<{ value: OverviewSport; label: string }> = [
  { value: 'duration', label: 'Overall' },
  { value: 'swimming', label: 'Swim' },
  { value: 'cycling', label: 'Bike' },
  { value: 'running', label: 'Run' },
  { value: 'hiking', label: 'Hike' },
];

function toChartPoints(series: Array<{ week: string; value: number }>) {
  return series.map((p) => ({ Week: p.week, total_duration: p.value, total_distance: p.value }));
}

function ChartMetricRow({ chart, stats }: { chart: ReactNode; stats: ReactNode }) {
  return (
    <div className="home-explorer-row">
      <div className="home-explorer-row-chart">{chart}</div>
      <div className="home-explorer-row-stats">{stats}</div>
    </div>
  );
}

function formatCompareTotal(metric: 'hours' | 'distance_km', value: number) {
  return metric === 'hours' ? formatDurationChart(value) : formatDistance(value, 1);
}

interface HomeTrainingExplorerProps {
  data: HomeYtdResponse;
  compactCharts?: boolean;
}

export function HomeTrainingExplorer({ data, compactCharts }: HomeTrainingExplorerProps) {
  const [historySport, setHistorySport] = useState<OverviewSport>('duration');
  const [compareYear, setCompareYear] = useState(data.year);
  const [baselineYear, setBaselineYear] = useState(data.year - 1);
  const [yearCompare, setYearCompare] = useState<YearCompareResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const compareCache = useRef(new Map<string, YearCompareResponse>());

  const yearOptions = useMemo(() => {
    const years: number[] = [];
    for (let y = HISTORY_YEAR_MIN; y <= data.year; y += 1) {
      years.push(y);
    }
    return years;
  }, [data.year]);

  const compareCacheKey = `${historySport}:${compareYear}:${baselineYear}`;

  useEffect(() => {
    if (baselineYear === compareYear) {
      return;
    }

    const cached = compareCache.current.get(compareCacheKey);
    if (cached) {
      setYearCompare(cached);
      return;
    }

    let cancelled = false;
    setHistoryLoading(true);
    api.overview
      .yearCompare(historySport, { compareYear, baselineYear })
      .then((payload) => {
        if (cancelled) return;
        compareCache.current.set(compareCacheKey, payload);
        setYearCompare(payload);
      })
      .catch(() => {
        if (!cancelled) setYearCompare(null);
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [historySport, compareYear, baselineYear, compareCacheKey]);

  const chartHeight = compactCharts ? 168 : 190;
  const s = data.summary;
  const weekly = data.weekly;
  const metric = yearCompare?.metric ?? 'hours';

  return (
    <>
      <div className="home-explorer-head">
        <h2 className="section-title">Training · YTD</h2>
        <div className="explorer-stat-block explorer-stat-block--plain explorer-stat-block--inline">
          <div className="explorer-stat-label">Sessions</div>
          <div className="explorer-stat-total">{s.total_sessions}</div>
        </div>
      </div>
      <div className="home-explorer-rows">
        <ChartMetricRow
          chart={
            <VolumeChart
              points={toChartPoints(weekly.hours)}
              yColumn="total_duration"
              yLabel="Hours"
              title="Volume (hours / week)"
              valueFormat="duration"
              height={chartHeight}
            />
          }
          stats={
            <ExplorerStatBlock
              layout="split"
              title="Hours"
              total={formatDurationChart(s.total_hours)}
              weeklyAvg={formatDurationChart(s.weekly_avg_hours)}
            />
          }
        />
        <ChartMetricRow
          chart={
            <VolumeChart
              points={toChartPoints(weekly.swim_km)}
              yColumn="total_distance"
              yLabel="km"
              title="Swim"
              valueFormat="distance"
              colorTheme="green"
              height={chartHeight}
            />
          }
          stats={
            <ExplorerStatBlock
              layout="split"
              title="Swim"
              total={formatDistance(s.total_swim_km, 1)}
              weeklyAvg={formatDistance(s.weekly_avg_swim_km, 1)}
            />
          }
        />
        <ChartMetricRow
          chart={
            <VolumeChart
              points={toChartPoints(weekly.bike_km)}
              yColumn="total_distance"
              yLabel="km"
              title="Bike"
              valueFormat="distance"
              colorTheme="orange"
              height={chartHeight}
            />
          }
          stats={
            <ExplorerStatBlock
              layout="split"
              title="Bike"
              total={formatDistance(s.total_bike_km, 1)}
              weeklyAvg={formatDistance(s.weekly_avg_bike_km, 1)}
            />
          }
        />
        <ChartMetricRow
          chart={
            <VolumeChart
              points={toChartPoints(weekly.run_km)}
              yColumn="total_distance"
              yLabel="km"
              title="Run"
              valueFormat="distance"
              colorTheme="purple"
              height={chartHeight}
            />
          }
          stats={
            <ExplorerStatBlock
              layout="split"
              title="Run"
              total={formatDistance(s.total_run_km, 1)}
              weeklyAvg={formatDistance(s.weekly_avg_run_km, 1)}
            />
          }
        />
        <ChartMetricRow
          chart={
            <VolumeChart
              points={toChartPoints(weekly.hike_km ?? [])}
              yColumn="total_distance"
              yLabel="km"
              title="Hike"
              valueFormat="distance"
              colorTheme="green"
              height={chartHeight}
            />
          }
          stats={
            <ExplorerStatBlock
              layout="split"
              title="Hike"
              total={formatDistance(s.total_hike_km ?? 0, 1)}
              weeklyAvg={formatDistance(s.weekly_avg_hike_km ?? 0, 1)}
            />
          }
        />
      </div>

      <section className="surface tone-gold home-history">
        <div className="home-history-head">
          <h2 className="section-title">
            History · {baselineYear} vs {compareYear}
          </h2>
          <div className="home-history-year-pickers">
            <label className="year-picker">
              <span className="year-picker-label">Year</span>
              <select
                className="year-picker-select"
                value={compareYear}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setCompareYear(next);
                  if (baselineYear === next) {
                    setBaselineYear(next - 1);
                  }
                }}
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>
            <span className="year-picker-vs">vs</span>
            <label className="year-picker">
              <span className="year-picker-label">Compare to</span>
              <select
                className="year-picker-select"
                value={baselineYear}
                onChange={(e) => {
                  const next = Number(e.target.value);
                  setBaselineYear(next);
                  if (next === compareYear) {
                    setCompareYear(Math.min(data.year, next + 1));
                  }
                }}
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <SegmentedControl
          options={HISTORY_SPORT_OPTIONS}
          value={historySport}
          onChange={setHistorySport}
        />
        <div style={{ height: 12 }} />
        {historyLoading && !yearCompare ? <div className="loading">Loading comparison…</div> : null}
        {yearCompare ? (
          <ChartMetricRow
            chart={
              <YearCompareChart
                points={yearCompare.points}
                priorYear={yearCompare.prior_year}
                currentYear={yearCompare.current_year}
                metric={yearCompare.metric}
                height={chartHeight}
              />
            }
            stats={
              <div className="home-year-compare-stats">
                <ExplorerStatBlock
                  layout="split"
                  title={String(yearCompare.prior_year)}
                  total={formatCompareTotal(metric, yearCompare.summary.prior.total)}
                  weeklyAvg={formatCompareTotal(metric, yearCompare.summary.prior.weekly_avg)}
                />
                <ExplorerStatBlock
                  layout="split"
                  title={String(yearCompare.current_year)}
                  total={formatCompareTotal(metric, yearCompare.summary.current.total)}
                  weeklyAvg={formatCompareTotal(metric, yearCompare.summary.current.weekly_avg)}
                />
              </div>
            }
          />
        ) : null}
      </section>
    </>
  );
}
