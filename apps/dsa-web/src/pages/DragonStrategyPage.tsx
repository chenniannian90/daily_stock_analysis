import React, { useCallback, useEffect, useState } from 'react';
import {
  CalendarDays, TrendingUp, TrendingDown, Minus,
  Zap, Crown, Flame, Target, BarChart3, Activity,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import { dragonStrategyApi, type DragonStock, type BoardSummary } from '../api/dragonStrategy';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';
import { cn } from '../utils/cn';

const SCORE_COLOR = (score?: number) => {
  // A股配色：高分红色（强势），低分绿色（弱势）
  if (score == null) return 'text-muted-foreground';
  if (score >= 70) return 'text-red-400';
  if (score >= 50) return 'text-amber-400';
  return 'text-emerald-400';
};

const PCT_COLOR = (pct: number) => {
  // A股配色：涨红跌绿
  if (pct > 0) return 'text-red-400';
  if (pct < 0) return 'text-emerald-400';
  return 'text-muted-foreground';
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const todayStr = () => formatDate(new Date().toISOString().slice(0, 10));

const SectionTitle: React.FC<{ icon: React.ReactNode; title: string; count?: number }> = ({ icon, title, count }) => (
  <div className="flex items-center gap-2 mb-3">
    {icon}
    <h3 className="text-sm font-semibold text-foreground">{title}</h3>
    {count != null && <span className="text-xs text-muted-foreground">({count})</span>}
  </div>
);

const DragonTable: React.FC<{ dragons: DragonStock[]; highlight?: boolean }> = ({ dragons, highlight }) => {
  if (!dragons.length) return <p className="text-sm text-muted-foreground py-4">暂无数据</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-xs text-muted-foreground">
            <th className="text-left py-2 pr-2 font-medium">股票</th>
            <th className="text-left py-2 pr-2 font-medium">板块</th>
            <th className="text-left py-2 pr-2 font-medium">概念</th>
            <th className="text-right py-2 pr-2 font-medium">板块%</th>
            <th className="text-right py-2 pr-2 font-medium">个股%</th>
            <th className="text-center py-2 pr-2 font-medium">连板</th>
            <th className="text-center py-2 pr-2 font-medium">评分</th>
            <th className="text-left py-2 font-medium">判定理由</th>
          </tr>
        </thead>
        <tbody>
          {dragons.map((d, i) => (
            <tr
              key={`${d.stockCode}-${i}`}
              className={cn(
                'border-b border-white/5 transition-colors',
                highlight ? 'bg-amber-500/5' : 'hover:bg-white/[0.02]',
              )}
            >
              <td className="py-2 pr-2">
                <span className="font-medium text-foreground">{d.stockName}</span>
                <span className="text-xs text-muted-foreground ml-1">{d.stockCode}</span>
              </td>
              <td className="py-2 pr-2 text-muted-foreground max-w-[120px] truncate">{d.boardName}</td>
              <td className="py-2 pr-2 text-xs text-muted-foreground max-w-[100px] truncate">{d.conceptName || '-'}</td>
              <td className={cn('py-2 pr-2 text-right', PCT_COLOR(d.boardPct))}>
                {d.boardPct > 0 ? '+' : ''}{d.boardPct?.toFixed(1)}%
              </td>
              <td className={cn('py-2 pr-2 text-right font-medium', PCT_COLOR(d.stockPct))}>
                {d.stockPct > 0 ? '+' : ''}{d.stockPct?.toFixed(1)}%
              </td>
              <td className="py-2 pr-2 text-center">
                {d.consecutiveBoard >= 2 ? (
                  <span className="inline-flex items-center gap-0.5 text-amber-400 font-bold">
                    <Zap className="h-3 w-3" />{d.consecutiveBoard}
                  </span>
                ) : d.consecutiveBoard === 1 ? (
                  <span className="text-muted-foreground">1</span>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </td>
              <td className="py-2 pr-2 text-center">
                <span className={cn('font-bold text-sm', SCORE_COLOR(d.dragonScore))}>
                  {d.dragonScore}
                </span>
              </td>
              <td className="py-2 text-xs text-muted-foreground max-w-[260px] truncate">
                {d.dragonReason}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const BoardSummaryCard: React.FC<{ summary: BoardSummary | null | undefined }> = ({ summary }) => {
  if (!summary) return null;
  const sentimentLabel = summary.marketSentiment === '强势' ? 'text-emerald-400'
    : summary.marketSentiment === '弱势' ? 'text-red-400' : 'text-muted-foreground';

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">板块数</span>
        <span className="text-sm font-medium">行业{summary.industryCount} 概念{summary.conceptCount}</span>
      </div>
      <div className="flex items-center gap-2">
        <Flame className="h-4 w-4 text-amber-400" />
        <span className="text-xs text-muted-foreground">领涨行业</span>
        <span className="text-sm font-medium">{summary.topIndustryName}</span>
        <span className={cn('text-xs', PCT_COLOR(summary.topIndustryPct))}>
          +{summary.topIndustryPct?.toFixed(1)}%
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Target className="h-4 w-4 text-cyan-400" />
        <span className="text-xs text-muted-foreground">领涨概念</span>
        <span className="text-sm font-medium">{summary.topConceptName}</span>
        <span className={cn('text-xs', PCT_COLOR(summary.topConceptPct))}>
          +{summary.topConceptPct?.toFixed(1)}%
        </span>
      </div>
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">市场情绪</span>
        <span className={cn('text-sm font-bold', sentimentLabel)}>{summary.marketSentiment}</span>
        <span className="text-xs text-muted-foreground">
          {summary.strongerThanIndexCount}板块强于指数
        </span>
      </div>
    </div>
  );
};

interface IndexBarProps {
  indices: Record<string, unknown> | null | undefined;
}

const IndexBar: React.FC<IndexBarProps> = ({ indices: idxData }) => {
  if (!idxData) return null;
  const items = Object.entries(idxData).filter(([k]) => k !== 'timestamp');
  if (!items.length) return null;
  return (
    <div className="flex flex-wrap gap-3 text-xs">
      {items.map(([code, info]: [string, unknown]) => {
        const d = info as { name?: string; pct?: number; changePct?: number; price?: number };
        const pct = d.pct ?? d.changePct ?? 0;
        return (
          <span key={code} className="inline-flex items-center gap-1">
            <span className="text-muted-foreground">{d.name || code}</span>
            <span className="text-foreground font-medium">{d.price?.toFixed(2) ?? '--'}</span>
            <span className={cn(PCT_COLOR(pct))}>
              {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
              {pct > 0 ? <TrendingUp className="inline h-3 w-3 ml-0.5" /> : pct < 0 ? <TrendingDown className="inline h-3 w-3 ml-0.5" /> : <Minus className="inline h-3 w-3 ml-0.5" />}
            </span>
          </span>
        );
      })}
    </div>
  );
};

const DragonStrategyPage: React.FC = () => {
  const [date, setDate] = useState<string>(todayStr());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [boardSummary, setBoardSummary] = useState<BoardSummary | null>(null);
  const [superDragons, setSuperDragons] = useState<DragonStock[]>([]);
  const [trueDragons, setTrueDragons] = useState<DragonStock[]>([]);
  const [crossDragons, setCrossDragons] = useState<DragonStock[]>([]);
  const [consecutiveLeaders, setConsecutiveLeaders] = useState<DragonStock[]>([]);
  const [allDragons, setAllDragons] = useState<DragonStock[]>([]);
  const [runTime, setRunTime] = useState<string>('');
  const [dates, setDates] = useState<string[]>([]);

  const fetchData = useCallback(async (queryDate: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await dragonStrategyApi.getByDate(queryDate);
      const dr = result.dragonResult;
      setBoardSummary(result.boardSummary || null);
      setRunTime(result.runTime || '');
      setSuperDragons(dr?.superDragons || []);
      setTrueDragons(dr?.trueDragons || []);
      setCrossDragons(dr?.crossBoardDragons || []);
      setConsecutiveLeaders(dr?.consecutiveLeaders || []);
      setAllDragons(dr?.dragonStocks || []);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败';
      setError({ title: '加载失败', message: msg, rawMessage: msg, category: 'unknown' });
      setSuperDragons([]);
      setTrueDragons([]);
      setCrossDragons([]);
      setConsecutiveLeaders([]);
      setAllDragons([]);
      setBoardSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDates = useCallback(async () => {
    try {
      const result = await dragonStrategyApi.getDates(30);
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

  return (
    <AppPage>
      <PageHeader
        title="龙头战法"
        description="基于指数→板块→个股→连板四层筛选，识别市场真龙头"
      />

      {/* Date Navigation */}
      <div className="flex items-center gap-3 mb-4">
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
        {runTime && (
          <span className="text-xs text-muted-foreground ml-2">
            数据时间: {runTime}
          </span>
        )}
        {dates.length > 0 && (
          <div className="ml-auto flex items-center gap-1.5 flex-wrap">
            <span className="text-xs text-muted-foreground">历史:</span>
            {dates.slice(0, 12).map(d => (
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
        )}
      </div>

      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">加载中...</div>
      ) : (
        <div className="space-y-4">
          {/* Index Bar */}
          {boardSummary?.indices && (
            <Card>
              <IndexBar indices={boardSummary.indices} />
            </Card>
          )}

          {/* Board Summary */}
          {boardSummary && (
            <Card>
              <SectionTitle icon={<Activity className="h-4 w-4 text-cyan-400" />} title="板块概况" />
              <BoardSummaryCard summary={boardSummary} />
            </Card>
          )}

          {/* Super Dragons + True Dragons side by side */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <SectionTitle
                icon={<Crown className="h-4 w-4 text-amber-400" />}
                title="超级龙头"
                count={superDragons.length}
              />
              <DragonTable dragons={superDragons} highlight />
            </Card>
            <Card>
              <SectionTitle
                icon={<Flame className="h-4 w-4 text-emerald-400" />}
                title="真龙头"
                count={trueDragons.length}
              />
              <DragonTable dragons={trueDragons.slice(0, 10)} />
            </Card>
          </div>

          {/* Consecutive Board Leaders */}
          {consecutiveLeaders.length > 0 && (
            <Card>
              <SectionTitle
                icon={<Zap className="h-4 w-4 text-yellow-400" />}
                title="连板龙头排行"
                count={consecutiveLeaders.length}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-xs text-muted-foreground">
                      <th className="text-left py-2 pr-2 font-medium">股票</th>
                      <th className="text-left py-2 pr-2 font-medium">板块</th>
                      <th className="text-center py-2 pr-2 font-medium">连板</th>
                      <th className="text-right py-2 pr-2 font-medium">涨幅</th>
                      <th className="text-right py-2 pr-2 font-medium">换手</th>
                      <th className="text-right py-2 pr-2 font-medium">封板资金(亿)</th>
                      <th className="text-right py-2 pr-2 font-medium">流通市值(亿)</th>
                      <th className="text-center py-2 font-medium">炸板次数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consecutiveLeaders.map((d, i) => (
                      <tr key={`cl-${d.stockCode}-${i}`} className="border-b border-white/5 hover:bg-white/[0.02]">
                        <td className="py-2 pr-2">
                          <span className="font-medium">{d.stockName}</span>
                          <span className="text-xs text-muted-foreground ml-1">{d.stockCode}</span>
                        </td>
                        <td className="py-2 pr-2 text-muted-foreground">{d.boardName || '-'}</td>
                        <td className="py-2 pr-2 text-center">
                          <span className="text-amber-400 font-bold">{d.consecutiveBoard}</span>
                        </td>
                        <td className={cn('py-2 pr-2 text-right', PCT_COLOR(d.stockPct))}>
                          {d.stockPct > 0 ? '+' : ''}{d.stockPct?.toFixed(1)}%
                        </td>
                        <td className="py-2 pr-2 text-right text-muted-foreground">
                          {d.turnover?.toFixed(1)}%
                        </td>
                        <td className="py-2 pr-2 text-right text-muted-foreground">
                          {(d.sealAmount / 1e8)?.toFixed(1)}
                        </td>
                        <td className="py-2 pr-2 text-right text-muted-foreground">
                          {d.floatMarketCap != null ? (d.floatMarketCap / 1e8).toFixed(1) : '-'}
                        </td>
                        <td className="py-2 text-center">
                          {d.breakCount > 0 ? (
                            <span className="text-amber-400">{d.breakCount}</span>
                          ) : (
                            <span className="text-muted-foreground">0</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Cross Board Dragons */}
          {crossDragons.length > 0 && (
            <Card>
              <SectionTitle
                icon={<Target className="h-4 w-4 text-purple-400" />}
                title="涨停板交叉龙头"
                count={crossDragons.length}
              />
              <DragonTable dragons={crossDragons} />
            </Card>
          )}

          {/* All Dragons */}
          {allDragons.length > 0 && (
            <Card>
              <SectionTitle
                icon={<BarChart3 className="h-4 w-4 text-muted-foreground" />}
                title="全部候选龙头"
                count={allDragons.length}
              />
              <DragonTable dragons={allDragons} />
            </Card>
          )}

          {!boardSummary && !allDragons.length && (
            <Card>
              <p className="text-sm text-muted-foreground text-center py-8">
                该日期暂无龙头战法数据
              </p>
            </Card>
          )}
        </div>
      )}
    </AppPage>
  );
};

export default DragonStrategyPage;
