import React, { useCallback, useEffect, useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Cloud, TrendingUp, Activity } from 'lucide-react';
import { stockStatApi, type WordCloudResponse } from '../api/stockStat';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';
import WordCloud from '../components/charts/WordCloud';
import { cn } from '../utils/cn';

const WINDOWS = [1, 3, 5, 10, 20] as const;

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const todayStr = () => formatDate(new Date().toISOString().slice(0, 10));

const StockStatPage: React.FC = () => {
  const [date, setDate] = useState<string>(todayStr());
  const [window, setWindow] = useState<number>(5);
  const [statType, setStatType] = useState<'gain' | 'vol'>('gain');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [data, setData] = useState<WordCloudResponse | null>(null);
  const [dates, setDates] = useState<string[]>([]);

  const fetchData = useCallback(async (queryDate: string, w: number, t: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await stockStatApi.getWordCloud(queryDate, w, t);
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
      const result = await stockStatApi.getDates(30);
      setDates(result.dates || []);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    fetchData(date, window, statType);
    fetchDates();
  }, [date, window, statType, fetchData, fetchDates]);

  const goDay = (offset: number) => {
    const d = new Date(date);
    d.setDate(d.getDate() + offset);
    setDate(formatDate(d.toISOString().slice(0, 10)));
  };

  const qualifierLabel = statType === 'gain' ? '涨幅>5%' : '波动率>5%';

  return (
    <AppPage>
      <PageHeader
        title="股票统计"
        description={`全A股（剔除ST）统计各时间窗口内${qualifierLabel}的股票，按板块/概念聚合为词云`}
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {/* Date nav */}
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

        <div className="h-5 w-px bg-white/10" />

        {/* Window selector */}
        <span className="text-xs text-muted-foreground">窗口:</span>
        {WINDOWS.map((w) => (
          <button
            key={w}
            type="button"
            className={cn(
              'px-2.5 py-1 rounded text-sm transition-colors',
              w === window
                ? 'bg-cyan/20 text-cyan font-medium'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
            )}
            onClick={() => setWindow(w)}
          >
            {w}日
          </button>
        ))}

        <div className="h-5 w-px bg-white/10" />

        {/* Type toggle */}
        <button
          type="button"
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded text-sm transition-colors',
            statType === 'gain'
              ? 'bg-red-500/15 text-red-400 font-medium'
              : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
          )}
          onClick={() => setStatType('gain')}
        >
          <TrendingUp className="h-3.5 w-3.5" />
          涨幅&gt;5%
        </button>
        <button
          type="button"
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded text-sm transition-colors',
            statType === 'vol'
              ? 'bg-amber-500/15 text-amber-400 font-medium'
              : 'text-muted-foreground hover:text-foreground hover:bg-white/5',
          )}
          onClick={() => setStatType('vol')}
        >
          <Activity className="h-3.5 w-3.5" />
          波动率&gt;5%
        </button>

        {/* Historical dates */}
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
          {/* Qualifying count */}
          {data && (
            <p className="text-sm text-muted-foreground mb-3">
              近 <span className="text-foreground font-medium">{data.window}</span> 个交易日，
              出现过<span className="text-cyan font-medium"> {qualifierLabel} </span>
              的股票共 <span className="text-foreground font-bold">{data.qualifyingCount}</span> 只
            </p>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {/* Sector word cloud */}
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <Cloud className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-foreground">
                  板块词云
                </h3>
                {data?.sectorWords.length ? (
                  <span className="text-xs text-muted-foreground">({data.sectorWords.length})</span>
                ) : null}
              </div>
              {data?.sectorWords.length ? (
                <WordCloud words={data.sectorWords} className="h-[380px]" />
              ) : (
                <p className="text-sm text-muted-foreground text-center py-16">
                  {data ? '暂无板块数据' : '暂无数据'}
                </p>
              )}
            </Card>

            {/* Concept word cloud */}
            <Card>
              <div className="flex items-center gap-2 mb-2">
                <Cloud className="h-4 w-4 text-purple-400" />
                <h3 className="text-sm font-semibold text-foreground">
                  概念词云
                </h3>
                {data?.conceptWords.length ? (
                  <span className="text-xs text-muted-foreground">({data.conceptWords.length})</span>
                ) : null}
              </div>
              {data?.conceptWords.length ? (
                <WordCloud words={data.conceptWords} className="h-[380px]" />
              ) : (
                <p className="text-sm text-muted-foreground text-center py-16">
                  {data ? '暂无概念数据（可能需要先更新概念库）' : '暂无数据'}
                </p>
              )}
            </Card>
          </div>
        </>
      )}
    </AppPage>
  );
};

export default StockStatPage;
