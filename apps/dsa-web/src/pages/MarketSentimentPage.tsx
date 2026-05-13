import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, CalendarDays } from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { marketSentimentApi, type SentimentSnapshot } from '../api/marketSentiment';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';

const formatDate = (d: Date) => d.toISOString().slice(0, 10);

const COLORS = ['#22d3ee', '#f97316', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#60a5fa', '#fb923c'];
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

  const days = useMemo(() => {
    const set = new Set<string>();
    for (const s of snapshots) {
      if (s.date) set.add(s.date);
    }
    return Array.from(set).sort();
  }, [snapshots]);

  // ── intraday data: group by time point ──
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
      entry[`${day}_upMedian`] = s.upMedianPct;
      entry[`${day}_downMedian`] = s.downMedianPct;
      entry[`${day}_upAvg`] = s.upAvgPct;
      entry[`${day}_downAvg`] = s.downAvgPct;
      entry[`${day}_limitUp`] = s.limitUpCount;
      entry[`${day}_limitDown`] = s.limitDownCount;
      entry[`${day}_amount`] = s.totalAmount;
    }
    return Array.from(map.values());
  }, [snapshots]);

  // ── daily data: only 15:00 closing snapshots, one point per day ──
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
      upMedianPct: s.upMedianPct,
      downMedianPct: s.downMedianPct,
      upAvgPct: s.upAvgPct,
      downAvgPct: s.downAvgPct,
    }));
  }, [snapshots]);

  const dayColors = useMemo(() => {
    const m = new Map<string, string>();
    days.forEach((d, i) => m.set(d, COLORS[i % COLORS.length]));
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

  return (
    <AppPage>
      <PageHeader title="市场情绪" description="全市场涨跌广度波动曲线" />

      {/* ── Date picker ── */}
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

      {/* ── Tabs ── */}
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
        <IntradayCharts chartData={intradayChartData} days={days} dayColors={dayColors} />
      )}

      {!isEmpty && activeTab === 'daily' && (
        <DailyCharts dailyData={dailyData} />
      )}
    </AppPage>
  );
};

// ─── Intraday (30分钟) charts ────────────────────────────────────────────────

const IntradayCharts: React.FC<{
  chartData: Record<string, number | string>[];
  days: string[];
  dayColors: Map<string, string>;
}> = ({ chartData, days, dayColors }) => (
  <div className="grid gap-6">
    <ChartCard title="涨跌家数" subtitle="上涨 vs 下跌">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {days.flatMap((day) => [
            <Line
              key={`${day}_up`}
              type="monotone"
              dataKey={`${day}_up`}
              name={`${day} 上涨`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />,
            <Line
              key={`${day}_down`}
              type="monotone"
              dataKey={`${day}_down`}
              name={`${day} 下跌`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
            />,
          ])}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>

    <ChartCard title="涨跌停家数" subtitle="涨停 vs 跌停">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {days.flatMap((day) => [
            <Line
              key={`${day}_lu`}
              type="monotone"
              dataKey={`${day}_limitUp`}
              name={`${day} 涨停`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />,
            <Line
              key={`${day}_ld`}
              type="monotone"
              dataKey={`${day}_limitDown`}
              name={`${day} 跌停`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
            />,
          ])}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>

    <ChartCard title="成交额(亿)" subtitle="全市场成交额变化">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {days.map((day) => (
            <Line
              key={`${day}_amt`}
              type="monotone"
              dataKey={`${day}_amount`}
              name={`${day} 成交额`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>

    <ChartCard title="涨跌幅统计(%)" subtitle="上涨中位数/均值">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {days.flatMap((day) => [
            <Line
              key={`${day}_um`}
              type="monotone"
              dataKey={`${day}_upMedian`}
              name={`${day} 上涨中位数`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />,
            <Line
              key={`${day}_ua`}
              type="monotone"
              dataKey={`${day}_upAvg`}
              name={`${day} 上涨均值`}
              stroke={dayColors.get(day)}
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
            />,
          ])}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  </div>
);

// ─── Daily (每日收盘) charts ──────────────────────────────────────────────────

const DailyCharts: React.FC<{ dailyData: Record<string, number | string>[] }> = ({ dailyData }) => {
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
      <ChartCard title="涨跌家数（收盘）" subtitle="每日15:00收盘快照">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="upCount"
              name="上涨"
              stroke="#22d3ee"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="downCount"
              name="下跌"
              stroke="#f97316"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="涨跌停家数（收盘）" subtitle="每日15:00收盘快照">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="limitUpCount"
              name="涨停"
              stroke="#f87171"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="limitDownCount"
              name="跌停"
              stroke="#34d399"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="成交额(亿)（收盘）" subtitle="每日15:00收盘快照">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="totalAmount"
              name="成交额"
              stroke="#60a5fa"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="涨跌幅统计(%)（收盘）" subtitle="每日15:00收盘快照">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="upMedianPct"
              name="上涨中位数"
              stroke="#22d3ee"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="upAvgPct"
              name="上涨均值"
              stroke="#22d3ee"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="downMedianPct"
              name="下跌中位数"
              stroke="#f97316"
              strokeWidth={STROKE_WIDTH}
              dot={{ r: DOT_R }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="downAvgPct"
              name="下跌均值"
              stroke="#f97316"
              strokeWidth={STROKE_WIDTH}
              strokeDasharray="5 5"
              dot={{ r: DOT_R }}
              connectNulls
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
