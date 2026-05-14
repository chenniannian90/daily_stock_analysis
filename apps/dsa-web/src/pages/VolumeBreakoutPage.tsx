import React, { useCallback, useEffect, useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Cloud, TrendingUp, Zap } from 'lucide-react';
import { volumeBreakoutApi, type BreakoutResponse, type BreakoutStock, type BreakoutETF, type BreakoutSector, type BreakoutConcept } from '../api/volumeBreakout';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';
import WordCloud from '../components/charts/WordCloud';
import { cn } from '../utils/cn';

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const todayStr = () => formatDate(new Date().toISOString().slice(0, 10));

const fmtVol = (v: number) => {
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`;
  return v.toFixed(0);
};

const VolumeBreakoutPage: React.FC = () => {
  const [date, setDate] = useState<string>(todayStr());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [data, setData] = useState<BreakoutResponse | null>(null);
  const [dates, setDates] = useState<string[]>([]);

  const fetchData = useCallback(async (queryDate: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await volumeBreakoutApi.getResults(queryDate);
      setData(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败';
      setError({ title: '加载失败', message: msg, rawMessage: msg, category: 'unknown' });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDates = useCallback(async () => {
    try {
      const result = await volumeBreakoutApi.getDates(30);
      setDates(result.dates || []);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    fetchData(date);
    fetchDates();
  }, [date, fetchData, fetchDates]);

  const goDay = (offset: number) => {
    const d = new Date(date);
    d.setDate(d.getDate() + offset);
    setDate(formatDate(d.toISOString().slice(0, 10)));
  };

  const getStockTable = (stocks: BreakoutStock[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted-foreground text-xs border-b border-white/10">
            <th className="py-1.5 pr-2">代码</th>
            <th className="py-1.5 pr-2">名称</th>
            <th className="py-1.5 pr-2 text-right">成交量</th>
            <th className="py-1.5 pr-2 text-right">昨日量</th>
            <th className="py-1.5 pr-2 text-right">近3日均</th>
            <th className="py-1.5 pr-2 text-right">vs昨日</th>
            <th className="py-1.5 pr-2 text-right">vs3日均</th>
            <th className="py-1.5 pr-2">行业</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((s) => (
            <tr key={s.code} className="border-b border-white/5 hover:bg-white/5 text-xs">
              <td className="py-1.5 pr-2 font-mono">{s.code}</td>
              <td className="py-1.5 pr-2 text-foreground">{s.name}</td>
              <td className="py-1.5 pr-2 text-right">{fmtVol(s.volume)}</td>
              <td className="py-1.5 pr-2 text-right text-muted-foreground">{fmtVol(s.yesterdayVolume)}</td>
              <td className="py-1.5 pr-2 text-right text-muted-foreground">{fmtVol(s.avg3dVolume || 0)}</td>
              <td className={cn('py-1.5 pr-2 text-right font-medium', s.ratioVsYesterday >= 3 ? 'text-red-400' : 'text-amber-400')}>{s.ratioVsYesterday}x</td>
              <td className={cn('py-1.5 pr-2 text-right', (s.ratioVs3dAvg || 0) >= 3 ? 'text-red-400' : 'text-muted-foreground')}>{s.ratioVs3dAvg ? `${s.ratioVs3dAvg}x` : '-'}</td>
              <td className="py-1.5 pr-2 text-muted-foreground max-w-[100px] truncate">{s.sectorName}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const getETFTable = (etfs: BreakoutETF[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted-foreground text-xs border-b border-white/10">
            <th className="py-1.5 pr-2">代码</th>
            <th className="py-1.5 pr-2">名称</th>
            <th className="py-1.5 pr-2 text-right">成交量</th>
            <th className="py-1.5 pr-2 text-right">昨日量</th>
            <th className="py-1.5 pr-2 text-right">vs昨日</th>
          </tr>
        </thead>
        <tbody>
          {etfs.map((e) => (
            <tr key={e.code} className="border-b border-white/5 hover:bg-white/5 text-xs">
              <td className="py-1.5 pr-2 font-mono">{e.code}</td>
              <td className="py-1.5 pr-2 text-foreground">{e.name}</td>
              <td className="py-1.5 pr-2 text-right">{fmtVol(e.volume)}</td>
              <td className="py-1.5 pr-2 text-right text-muted-foreground">{fmtVol(e.yesterdayVolume)}</td>
              <td className={cn('py-1.5 pr-2 text-right font-medium', e.ratioVsYesterday >= 2 ? 'text-red-400' : 'text-amber-400')}>{e.ratioVsYesterday}x</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const getAggTable = (items: (BreakoutSector | BreakoutConcept)[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted-foreground text-xs border-b border-white/10">
            <th className="py-1.5 pr-2">名称</th>
            <th className="py-1.5 pr-2 text-right">成分股数</th>
            <th className="py-1.5 pr-2 text-right">今日合计</th>
            <th className="py-1.5 pr-2 text-right">昨日合计</th>
            <th className="py-1.5 pr-2 text-right">vs昨日</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.name} className="border-b border-white/5 hover:bg-white/5 text-xs">
              <td className="py-1.5 pr-2 text-foreground">{item.name}</td>
              <td className="py-1.5 pr-2 text-right text-muted-foreground">{item.constituentCount}</td>
              <td className="py-1.5 pr-2 text-right">{fmtVol(item.aggVolume)}</td>
              <td className="py-1.5 pr-2 text-right text-muted-foreground">{fmtVol(item.yesterdayAggVolume)}</td>
              <td className={cn('py-1.5 pr-2 text-right font-medium', item.ratio >= 2 ? 'text-red-400' : 'text-amber-400')}>{item.ratio}x</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <AppPage>
      <PageHeader
        title="放量检测"
        description="每日18:00自动检测全市场放量标的：个股(2×)、ETF(1.5×)、板块(1.5×)、概念(1.5×)"
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <button
          type="button"
          className="p-1.5 rounded hover:bg-white/10 transition-colors"
          onClick={() => goDay(-1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        <input
          type="date"
          className="bg-transparent border border-white/10 rounded px-3 py-1.5 text-sm text-foreground focus:border-cyan/50 outline-none"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <button
          type="button"
          className="p-1.5 rounded hover:bg-white/10 transition-colors disabled:opacity-30"
          onClick={() => goDay(1)}
          disabled={date >= todayStr()}
        >
          <ChevronRight className="h-4 w-4" />
        </button>

        {dates.length > 0 && (
          <>
            <div className="h-5 w-px bg-white/10" />
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-muted-foreground">历史:</span>
              {dates.slice(0, 12).map((d) => (
                <button
                  key={d}
                  type="button"
                  className={cn(
                    'text-xs px-1.5 py-0.5 rounded transition-colors',
                    d === date ? 'bg-cyan/20 text-cyan' : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
                  )}
                  onClick={() => setDate(d)}
                >
                  {d.slice(5)}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">加载中...</div>
      ) : (
        <>
          {/* Summary */}
          {data && (
            <div className="flex flex-wrap gap-4 mb-4 text-sm text-muted-foreground">
              <span>
                <TrendingUp className="inline h-3.5 w-3.5 mr-1 text-red-400" />
                放量个股: <span className="text-foreground font-bold">{data.stockCount}</span>
              </span>
              <span>
                <Zap className="inline h-3.5 w-3.5 mr-1 text-amber-400" />
                放量ETF: <span className="text-foreground font-bold">{data.etfCount}</span>
              </span>
              <span>
                放量板块: <span className="text-foreground font-bold">{data.sectorCount}</span>
              </span>
              <span>
                放量概念: <span className="text-foreground font-bold">{data.conceptCount}</span>
              </span>
            </div>
          )}

          <div className="space-y-4">
            {/* Stock breakout table */}
            {data?.stocks && data.stocks.length > 0 && (
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-red-400" />
                  <h3 className="text-sm font-semibold text-foreground">
                    放量个股 ({data.stockCount}只)
                  </h3>
                </div>
                {getStockTable(data.stocks)}
              </Card>
            )}

            {/* ETF breakout table */}
            {data?.etfs && data.etfs.length > 0 && (
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-amber-400" />
                  <h3 className="text-sm font-semibold text-foreground">
                    放量ETF ({data.etfCount}只)
                  </h3>
                </div>
                {getETFTable(data.etfs)}
              </Card>
            )}

            {/* Sector breakout table */}
            {data?.sectors && data.sectors.length > 0 && (
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-green-400" />
                  <h3 className="text-sm font-semibold text-foreground">
                    放量板块 ({data.sectorCount}个)
                  </h3>
                </div>
                {getAggTable(data.sectors)}
              </Card>
            )}

            {/* Concept breakout table */}
            {data?.concepts && data.concepts.length > 0 && (
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-foreground">
                    放量概念 ({data.conceptCount}个)
                  </h3>
                </div>
                {getAggTable(data.concepts)}
              </Card>
            )}

            {/* Word clouds */}
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <Cloud className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-sm font-semibold text-foreground">放量个股板块词云</h3>
                  {data?.sectorWords.length ? (
                    <span className="text-xs text-muted-foreground">({data.sectorWords.length})</span>
                  ) : null}
                </div>
                {data?.sectorWords.length ? (
                  <WordCloud words={data.sectorWords} className="h-[380px]" />
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-16">暂无数据</p>
                )}
              </Card>

              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <Cloud className="h-4 w-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-foreground">放量个股概念词云</h3>
                  {data?.conceptWords.length ? (
                    <span className="text-xs text-muted-foreground">({data.conceptWords.length})</span>
                  ) : null}
                </div>
                {data?.conceptWords.length ? (
                  <WordCloud words={data.conceptWords} className="h-[380px]" />
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-16">暂无数据</p>
                )}
              </Card>
            </div>

            {/* No data state */}
            {data && data.stockCount === 0 && data.etfCount === 0 && data.sectorCount === 0 && data.conceptCount === 0 && (
              <p className="text-center text-muted-foreground py-8">
                {data.date} 无放量标的
              </p>
            )}
          </div>
        </>
      )}
    </AppPage>
  );
};

export default VolumeBreakoutPage;
