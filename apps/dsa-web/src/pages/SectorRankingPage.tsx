import React, { useCallback, useEffect, useState } from 'react';
import { CalendarDays, LayoutList, TrendingDown, TrendingUp, Zap } from 'lucide-react';
import { sectorRankingApi, type SectorRankingItem } from '../api/sectorRanking';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';

const formatDate = (d: Date) => d.toISOString().slice(0, 10);

const WINDOWS = [
  { value: 1, label: '1日' },
  { value: 3, label: '3日' },
  { value: 5, label: '5日' },
  { value: 10, label: '10日' },
  { value: 20, label: '20日' },
];

const SECTOR_TYPES = [
  { value: 'industry', label: '行业板块' },
  { value: 'concept', label: '概念板块' },
];

const SectorRankingPage: React.FC = () => {
  const today = new Date();
  const [date, setDate] = useState(() => formatDate(today));
  const [sectorType, setSectorType] = useState('industry');
  const [window, setWindow] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [gainItems, setGainItems] = useState<SectorRankingItem[]>([]);
  const [flowItems, setFlowItems] = useState<SectorRankingItem[]>([]);
  const [limitUpItems, setLimitUpItems] = useState<SectorRankingItem[]>([]);
  const [availableDates, setAvailableDates] = useState<string[]>([]);

  const fetchAll = useCallback(async (d: string) => {
    setLoading(true);
    setError(null);
    try {
      const [gain, flow, limitUp] = await Promise.all([
        sectorRankingApi.getRankings({ date: d, sectorType, window, sortBy: 'gain', limit: 20 }),
        sectorRankingApi.getRankings({ date: d, sectorType, window, sortBy: 'capital_flow', limit: 20 }),
        sectorRankingApi.getRankings({ date: d, sectorType, window, sortBy: 'limit_up', limit: 20 }),
      ]);
      setGainItems(gain.items);
      setFlowItems(flow.items);
      setLimitUpItems(limitUp.items);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败';
      setError({ title: '加载失败', message: msg, rawMessage: msg, category: 'unknown' });
      setGainItems([]);
      setFlowItems([]);
      setLimitUpItems([]);
    } finally {
      setLoading(false);
    }
  }, [sectorType, window]);

  useEffect(() => {
    fetchAll(date);
  }, [date, sectorType, window, fetchAll]);

  useEffect(() => {
    sectorRankingApi.getDates(sectorType, 30).then(setAvailableDates).catch(() => {});
  }, [sectorType]);

  const handleDateChange = useCallback((newDate: string) => {
    setDate(newDate);
  }, []);

  if (loading) {
    return (
      <AppPage>
        <PageHeader title="板块排名" description="行业/概念板块 涨幅·资金流·涨停 Top20" />
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      </AppPage>
    );
  }

  const isEmpty = gainItems.length === 0 && flowItems.length === 0 && limitUpItems.length === 0;

  return (
    <AppPage>
      <PageHeader title="板块排名" description="行业/概念板块 涨幅·资金流·涨停 Top20" />

      {/* Controls */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        <input
          type="date"
          value={date}
          max={formatDate(today)}
          onChange={(e) => handleDateChange(e.target.value)}
          className="input w-40"
        />
        {availableDates.length > 0 && (
          <select
            value={date}
            onChange={(e) => handleDateChange(e.target.value)}
            className="input w-40"
          >
            {availableDates.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        )}
      </div>

      {/* Sector type toggle */}
      <div className="mb-3 flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {SECTOR_TYPES.map((st) => (
          <button
            key={st.value}
            onClick={() => setSectorType(st.value)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              sectorType === st.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {st.label}
          </button>
        ))}
      </div>

      {/* Time window tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {WINDOWS.map((w) => (
          <button
            key={w.value}
            onClick={() => setWindow(w.value)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              window === w.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {w.label}
          </button>
        ))}
      </div>

      {error && <ApiErrorAlert error={error} />}

      {!loading && !error && isEmpty && (
        <Card className="flex flex-col items-center gap-2 py-16">
          <LayoutList className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-muted-foreground">该日期暂无板块排名数据</p>
        </Card>
      )}

      {/* Three ranking tables side by side */}
      {!isEmpty && (
        <div className="grid gap-6 lg:grid-cols-3">
          <RankingCard
            title="涨幅最大"
            icon={<TrendingUp className="h-4 w-4" />}
            items={gainItems}
            valueKey="changePct"
            valueColor={(v) => v > 0 ? 'text-red-500' : v < 0 ? 'text-green-500' : 'text-muted-foreground'}
          />
          <RankingCard
            title="资金净流入最大"
            icon={<Zap className="h-4 w-4" />}
            items={flowItems}
            valueKey="netCapitalFlow"
            valueColor={(v) => v > 0 ? 'text-red-500' : v < 0 ? 'text-green-500' : 'text-muted-foreground'}
          />
          <RankingCard
            title="涨停家数最多"
            icon={<TrendingDown className="h-4 w-4" />}
            items={limitUpItems}
            valueKey="limitUpCount"
            valueColor={() => 'text-red-500'}
          />
        </div>
      )}
    </AppPage>
  );
};

// ─── Ranking card ───────────────────────────────────────────────────────────

interface RankingCardProps {
  title: string;
  icon: React.ReactNode;
  items: SectorRankingItem[];
  valueKey: 'changePct' | 'netCapitalFlow' | 'limitUpCount';
  valueColor: (v: number) => string;
}

const RankingCard: React.FC<RankingCardProps> = ({ title, icon, items, valueKey, valueColor }) => (
  <Card className="p-4">
    <div className="mb-3 flex items-center gap-2">
      <span className="text-muted-foreground">{icon}</span>
      <h3 className="text-sm font-semibold text-foreground">{title} Top 20</h3>
    </div>
    {items.length === 0 ? (
      <p className="py-8 text-center text-xs text-muted-foreground">暂无数据</p>
    ) : (
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th className="pb-2 text-left font-medium w-8">#</th>
              <th className="pb-2 text-left font-medium">板块</th>
              <th className="pb-2 text-right font-medium">{title}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.sectorCode} className="border-b border-border/40 last:border-0 hover:bg-muted/30">
                <td className="py-1.5 font-mono text-muted-foreground">
                  {item.rank <= 3 ? (
                    <span className={`inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold text-white ${
                      item.rank === 1 ? 'bg-red-500' : item.rank === 2 ? 'bg-orange-500' : 'bg-amber-500'
                    }`}>
                      {item.rank}
                    </span>
                  ) : (
                    item.rank
                  )}
                </td>
                <td className="py-1.5 max-w-[120px] truncate" title={item.sectorName}>
                  {item.sectorName}
                </td>
                <td className={`py-1.5 text-right font-mono font-medium ${valueColor(getValue(item, valueKey))}`}>
                  {formatValue(item, valueKey)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </Card>
);

function getValue(item: SectorRankingItem, key: 'changePct' | 'netCapitalFlow' | 'limitUpCount'): number {
  return item[key];
}

function formatValue(item: SectorRankingItem, key: 'changePct' | 'netCapitalFlow' | 'limitUpCount'): string {
  if (key === 'changePct') return formatPct(item.changePct);
  if (key === 'netCapitalFlow') return formatFlow(item.netCapitalFlow);
  return String(item.limitUpCount);
}

function formatPct(v: number): string {
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

function formatFlow(v: number): string {
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}亿`;
}

export default SectorRankingPage;
