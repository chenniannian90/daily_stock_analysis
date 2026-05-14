import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, CalendarDays } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { LegendPayload } from 'recharts';
import { marketSentimentApi, type SentimentSnapshot } from '../api/marketSentiment';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';

const formatDate = (d: Date) => d.toISOString().slice(0, 10);

const UP_COLORS = ['#ef4444', '#f97316', '#e11d48', '#dc2626', '#ea580c', '#b91c1c', '#fdba74', '#fca5a5'];
const DOWN_COLORS = ['#22c55e', '#3b82f6', '#10b981', '#06b6d4', '#6366f1', '#14b8a6', '#8b5cf6', '#2563eb'];
const STROKE_WIDTH = 2;
const DOT_R = 3;

const TIME_POINTS = ['09:30','10:00','10:30','11:00','11:30','13:30','14:00','14:30','15:00'];

type TabKey = 'intraday' | 'daily';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'intraday', label: '30分钟情绪' },
  { key: 'daily', label: '每日情绪' },
];

const MarketSentimentPage: React.FC = () => {
  const today = new Date();
  const [startDate, setStartDate] = useState(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - 5);
    return formatDate(d);
  });
  const [endDate, setEndDate] = useState(() => formatDate(today));
  const [snapshots, setSnapshots] = useState<SentimentSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('intraday');
  const [hiddenLegends, setHiddenLegends] = useState<Set<string>>(new Set());

  const fetchData = useCallback(async (start: string, end: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await marketSentimentApi.getRange(start, end);
      setSnapshots(result.snapshots);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败';
      setError({ title: '加载失败', message: msg, rawMessage: msg, category: 'unknown' });
      setSnapshots([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(startDate, endDate);
  }, [startDate, endDate, fetchData]);

  const handleLegendClick = useCallback((e: LegendPayload, _index?: number) => {
    const dk = e.dataKey;
    if (dk == null) return;
    const key = typeof dk === 'function' ? dk({} as never) : String(dk);
    setHiddenLegends((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const days = useMemo(() => {
    const set = new Set<string>();
    for (const s of snapshots) {
      if (s.date) set.add(s.date);
    }
    return Array.from(set).sort();
  }, [snapshots]);

  const intradayChartData = useMemo(() => {
    const map = new Map<string, Record<string, number | string>>();
    for (const tp of TIME_POINTS) {
      map.set(tp, { time: tp });
    }
    for (const s of snapshots) {
      const day = s.date;
      if (!day || !s.time || !map.has(s.time)) continue;
      const entry = map.get(s.time)!;
      entry[`${day}_up`] = s.upCount;
      entry[`${day}_down`] = s.downCount;
      entry[`${day}_limitUp`] = s.limitUpCount;
      entry[`${day}_limitDown`] = s.limitDownCount;
      entry[`${day}_amount`] = s.totalAmount;
      entry[`${day}_allMedian`] = s.allMedianPct;
      entry[`${day}_allAvg`] = s.allAvgPct;
    }
    return Array.from(map.values());
  }, [snapshots]);

  const dailyData = useMemo(() => {
    const closing = snapshots.filter((s) => s.time === '15:00');
    closing.sort((a, b) => a.date.localeCompare(b.date));
    return closing.map((s) => ({
      date: s.date,
      upCount: s.upCount,
      downCount: s.downCount,
      limitUpCount: s.limitUpCount,
      limitDownCount: s.limitDownCount,
      totalAmount: s.totalAmount,
      allMedianPct: s.allMedianPct,
      allAvgPct: s.allAvgPct,
    }));
  }, [snapshots]);

  const upColors = useMemo(() => {
    const m = new Map<string, string>();
    days.forEach((d, i) => m.set(d, UP_COLORS[i % UP_COLORS.length]));
    return m;
  }, [days]);

  const downColors = useMemo(() => {
    const m = new Map<string, string>();
    days.forEach((d, i) => m.set(d, DOWN_COLORS[i % DOWN_COLORS.length]));
    return m;
  }, [days]);

  if (loading) {
    return (
      <AppPage>
        <PageHeader title="市场情绪" description="全市场涨跌广度波动曲线" />
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      </AppPage>
    );
  }

  const isEmpty = snapshots.length === 0;

  const chartProps = { hiddenLegends, onLegendClick: handleLegendClick };

  return (
    <AppPage>
      <PageHeader title="市场情绪" description="全市场涨跌广度波动曲线" />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        <input
          type="date"
          value={startDate}
          max={endDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="input w-40"
        />
        <span className="text-muted-foreground">—</span>
        <input
          type="date"
          value={endDate}
          min={startDate}
          max={formatDate(today)}
          onChange={(e) => setEndDate(e.target.value)}
          className="input w-40"
        />
        {days.length > 0 && (
          <span className="text-sm text-muted-foreground ml-2">
            {days.length} 个交易日 · {snapshots.length} 条快照
          </span>
        )}
      </div>

      <div className="mb-6 flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab.key
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <ApiErrorAlert error={error} />}

      {!loading && !error && isEmpty && (
        <Card className="flex flex-col items-center gap-2 py-16">
          <Activity className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-muted-foreground">该日期范围暂无市场情绪数据</p>
        </Card>
      )}

      {!isEmpty && activeTab === 'intraday' && (
        <IntradayCharts chartData={intradayChartData} days={days} upColors={upColors} downColors={downColors} {...chartProps} />
      )}

      {!isEmpty && activeTab === 'daily' && (
        <DailyCharts dailyData={dailyData} {...chartProps} />
      )}
    </AppPage>
  );
};

// ─── Intraday (30分钟) charts ────────────────────────────────────────────────

interface ChartControlProps {
  hiddenLegends: Set<string>;
  onLegendClick: (data: LegendPayload, index?: number) => void;
}

const IntradayCharts: React.FC<{
  chartData: Record<string, number | string>[];
  days: string[];
  upColors: Map<string, string>;
  downColors: Map<string, string>;
} & ChartControlProps> = ({ chartData, days, upColors, downColors, hiddenLegends, onLegendClick }) => (
  <div className="grid gap-6">
    <ChartCard title="涨跌家数" subtitle="红涨绿跌 · 3000普涨 / 600普跌">
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend onClick={onLegendClick} />
          <ReferenceLine y={3000} stroke="#fbbf24" strokeWidth={1.5} strokeDasharray="4 4" label={{ value: '普涨线 3000', position: 'right', fontSize: 11, fill: '#fbbf24' }} />
          <ReferenceLine y={600} stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="4 4" label={{ value: '普跌线 600', position: 'right', fontSize: 11, fill: '#9ca3af' }} />
          {days.flatMap((day) => [
            <Line
              key={`${day}_up`}
              type="monotone"
              dataKey={`${day}_up`}
              name={`${day} 上涨`}
              stroke={upColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has(`${day}_up`)}
            />,
            <Line
              key={`${day}_down`}
              type="monotone"
              dataKey={`${day}_down`}
              name={`${day} 下跌`}
              stroke={downColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has(`${day}_down`)}
            />,
          ])}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>

    <ChartCard title="涨跌停家数" subtitle="红涨停 · 绿跌停">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend onClick={onLegendClick} />
          {days.flatMap((day) => [
            <Line
              key={`${day}_lu`}
              type="monotone"
              dataKey={`${day}_limitUp`}
              name={`${day} 涨停`}
              stroke={upColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has(`${day}_limitUp`)}
            />,
            <Line
              key={`${day}_ld`}
              type="monotone"
              dataKey={`${day}_limitDown`}
              name={`${day} 跌停`}
              stroke={downColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has(`${day}_limitDown`)}
            />,
          ])}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>

    <ChartCard title="成交额(亿)" subtitle="全市场成交额变化">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} maxBarSize={40}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend onClick={onLegendClick} />
          {days.map((day) => (
            <Bar
              key={`${day}_amt`}
              dataKey={`${day}_amount`}
              name={`${day}`}
              fill={upColors.get(day)}
              hide={hiddenLegends.has(`${day}_amount`)}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>

    <ChartCard title="全市场涨跌幅(%)" subtitle="全股票涨跌幅统计（中位数/均值 · 可正可负）">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend onClick={onLegendClick} />
          {days.flatMap((day) => [
            <Line
              key={`${day}_am`}
              type="monotone"
              dataKey={`${day}_allMedian`}
              name={`${day} 全市场中位数`}
              stroke={upColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has(`${day}_allMedian`)}
            />,
            <Line
              key={`${day}_aa`}
              type="monotone"
              dataKey={`${day}_allAvg`}
              name={`${day} 全市场均值`}
              stroke={downColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has(`${day}_allAvg`)}
            />,
          ])}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  </div>
);

// ─── Daily (每日收盘) charts ──────────────────────────────────────────────────

const DailyCharts: React.FC<{ dailyData: Record<string, number | string>[] } & ChartControlProps> = ({ dailyData, hiddenLegends, onLegendClick }) => {
  if (dailyData.length === 0) {
    return (
      <Card className="flex flex-col items-center gap-2 py-16">
        <Activity className="h-10 w-10 text-muted-foreground/40" />
        <p className="text-muted-foreground">该日期范围暂无收盘快照数据</p>
      </Card>
    );
  }

  return (
    <div className="grid gap-6">
      <ChartCard title="涨跌家数（收盘）" subtitle="红涨 · 绿跌">
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend onClick={onLegendClick} />
            <ReferenceLine y={3000} stroke="#fbbf24" strokeWidth={1.5} strokeDasharray="4 4" label={{ value: '普涨线 3000', position: 'right', fontSize: 11, fill: '#fbbf24' }} />
            <ReferenceLine y={600} stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="4 4" label={{ value: '普跌线 600', position: 'right', fontSize: 11, fill: '#9ca3af' }} />
            <Line
              type="monotone"
              dataKey="upCount"
              name="上涨"
              stroke="#ef4444"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has('upCount')}
            />
            <Line
              type="monotone"
              dataKey="downCount"
              name="下跌"
              stroke="#22c55e"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has('downCount')}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="涨跌停家数（收盘）" subtitle="红涨停 · 绿跌停">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend onClick={onLegendClick} />
            <Line
              type="monotone"
              dataKey="limitUpCount"
              name="涨停"
              stroke="#ef4444"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has('limitUpCount')}
            />
            <Line
              type="monotone"
              dataKey="limitDownCount"
              name="跌停"
              stroke="#22c55e"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has('limitDownCount')}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="成交额(亿)（收盘）" subtitle="每日15:00收盘快照">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={dailyData} maxBarSize={40}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend onClick={onLegendClick} />
            <Bar
              dataKey="totalAmount"
              name="成交额"
              fill="#60a5fa"
              hide={hiddenLegends.has('totalAmount')}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="全市场涨跌幅(%)（收盘）" subtitle="全股票涨跌幅统计（中位数/均值 · 可正可负）">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend onClick={onLegendClick} />
            <Line
              type="monotone"
              dataKey="allMedianPct"
              name="全市场中位数"
              stroke="#ef4444"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has('allMedianPct')}
            />
            <Line
              type="monotone"
              dataKey="allAvgPct"
              name="全市场均值"
              stroke="#22c55e"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
              hide={hiddenLegends.has('allAvgPct')}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
};

// ─── Shared ───────────────────────────────────────────────────────────────────

const ChartCard: React.FC<{ title: string; subtitle: string; children: React.ReactNode }> = ({
  title,
  subtitle,
  children,
}) => (
  <Card className="p-4">
    <h3 className="mb-1 text-sm font-semibold text-foreground">{title}</h3>
    <p className="mb-3 text-xs text-muted-foreground">{subtitle}</p>
    {children}
  </Card>
);

export default MarketSentimentPage;
