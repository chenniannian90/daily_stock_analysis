import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarDays, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react';
import { historyApi, type DailySummaryItem } from '../api/history';
import type { ParsedApiError } from '../api/error';
import { AppPage } from '../components/common/AppPage';
import { ApiErrorAlert } from '../components/common/ApiErrorAlert';
import { Card } from '../components/common/Card';
import { PageHeader } from '../components/common/PageHeader';
import { cn } from '../utils/cn';

const SCORE_COLOR = (score?: number) => {
  if (score == null) return 'text-muted-foreground';
  if (score >= 70) return 'text-emerald-500';
  if (score >= 50) return 'text-amber-500';
  return 'text-red-500';
};

const SCORE_BG = (score?: number) => {
  if (score == null) return 'bg-muted';
  if (score >= 70) return 'bg-emerald-500/10';
  if (score >= 50) return 'bg-amber-500/10';
  return 'bg-red-500/10';
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const todayStr = () => formatDate(new Date().toISOString().slice(0, 10));

const DailySummaryPage: React.FC = () => {
  const navigate = useNavigate();
  const [date, setDate] = useState<string>(todayStr());
  const [items, setItems] = useState<DailySummaryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const fetchSummary = useCallback(async (queryDate: string) => {
    setLoading(true);
    setError(null);
    setExpandedIdx(null);
    try {
      const result = await historyApi.getDailySummary(queryDate);
      setItems(result.items);
      setTotal(result.total);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败';
      setError({ title: '加载失败', message: msg, rawMessage: msg, category: 'unknown' });
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary(date);
  }, [date, fetchSummary]);

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDate(e.target.value);
  };

  const goPrevDay = () => {
    const d = new Date(date);
    d.setDate(d.getDate() - 1);
    setDate(formatDate(d.toISOString().slice(0, 10)));
  };

  const goNextDay = () => {
    const d = new Date(date);
    d.setDate(d.getDate() + 1);
    setDate(formatDate(d.toISOString().slice(0, 10)));
  };

  const buyCount = items.filter(i => i.operationAdvice?.includes('买入')).length;
  const holdCount = items.filter(i => i.operationAdvice?.includes('持有')).length;
  const watchCount = items.filter(i => i.operationAdvice?.includes('观望')).length;
  const avgScore = items.length > 0
    ? Math.round(items.reduce((s, i) => s + (i.sentimentScore ?? 0), 0) / items.length)
    : 0;

  return (
    <AppPage>
      <PageHeader
        title="每日总结"
        description="按日期查看所有自选股分析结果"
      />

      {/* 日期选择 */}
      <div className="mb-6 flex items-center gap-2">
        <button
          type="button"
          onClick={goPrevDay}
          className="btn-icon"
          aria-label="前一天"
        >
          <ChevronDown className="h-4 w-4 rotate-90" />
        </button>
        <div className="relative">
          <CalendarDays className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="date"
            value={date}
            onChange={handleDateChange}
            className="input pl-10"
            max={todayStr()}
          />
        </div>
        <button
          type="button"
          onClick={goNextDay}
          disabled={date >= todayStr()}
          className="btn-icon disabled:opacity-30"
          aria-label="后一天"
        >
          <ChevronUp className="h-4 w-4 rotate-90" />
        </button>
      </div>

      {/* 统计卡片 */}
      {!loading && !error && total > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">总数</p>
            <p className="text-2xl font-bold">{total}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">平均分</p>
            <p className={cn('text-2xl font-bold', SCORE_COLOR(avgScore))}>{avgScore}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">买入/持有</p>
            <p className="text-2xl font-bold text-emerald-500">{buyCount + holdCount}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-muted-foreground">观望</p>
            <p className="text-2xl font-bold text-amber-500">{watchCount}</p>
          </Card>
        </div>
      )}

      {/* 加载 & 错误 */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      )}

      {error && <ApiErrorAlert error={error} />}

      {/* 空状态 */}
      {!loading && !error && total === 0 && (
        <Card className="flex flex-col items-center gap-2 py-12">
          <CalendarDays className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-muted-foreground">{date} 暂无分析记录</p>
        </Card>
      )}

      {/* 列表 */}
      {!loading && !error && items.length > 0 && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left font-medium">代码</th>
                  <th className="px-4 py-3 text-left font-medium">名称</th>
                  <th className="px-4 py-3 text-center font-medium">评分</th>
                  <th className="px-4 py-3 text-center font-medium">建议</th>
                  <th className="hidden px-4 py-3 text-left font-medium md:table-cell">摘要</th>
                  <th className="px-4 py-3 text-center font-medium">展开</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <React.Fragment key={item.stockCode}>
                    <tr
                      className={cn(
                        'cursor-pointer border-b border-border hover:bg-muted/30 transition-colors',
                        SCORE_BG(item.sentimentScore)
                      )}
                      onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                    >
                      <td className="px-4 py-3 font-mono text-xs">{item.stockCode}</td>
                      <td className="px-4 py-3 font-medium">{item.stockName || '—'}</td>
                      <td className={cn('px-4 py-3 text-center font-bold', SCORE_COLOR(item.sentimentScore))}>
                        {item.sentimentScore ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={cn(
                          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                          item.operationAdvice?.includes('买入') ? 'bg-emerald-500/10 text-emerald-600' :
                          item.operationAdvice?.includes('持有') ? 'bg-blue-500/10 text-blue-600' :
                          item.operationAdvice?.includes('减仓') ? 'bg-orange-500/10 text-orange-600' :
                          'bg-muted text-muted-foreground'
                        )}>
                          {item.operationAdvice?.includes('买入') ? <TrendingUp className="h-3 w-3" /> :
                           item.operationAdvice?.includes('减仓') ? <TrendingDown className="h-3 w-3" /> :
                           <Minus className="h-3 w-3" />}
                          {item.operationAdvice || '—'}
                        </span>
                      </td>
                      <td className="hidden max-w-xs truncate px-4 py-3 text-muted-foreground md:table-cell">
                        {item.analysisSummary || '—'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {expandedIdx === idx
                          ? <ChevronUp className="mx-auto h-4 w-4 text-muted-foreground" />
                          : <ChevronDown className="mx-auto h-4 w-4 text-muted-foreground" />
                        }
                      </td>
                    </tr>
                    {expandedIdx === idx && (
                      <tr className="border-b border-border bg-muted/20">
                        <td colSpan={6} className="px-6 py-4">
                          <div className="grid gap-3 sm:grid-cols-3">
                            <div>
                              <p className="mb-1 text-xs font-medium text-muted-foreground">操作建议</p>
                              <p>{item.operationAdvice || '—'}</p>
                            </div>
                            <div>
                              <p className="mb-1 text-xs font-medium text-muted-foreground">情绪评分</p>
                              <p className={cn('font-bold', SCORE_COLOR(item.sentimentScore))}>
                                {item.sentimentScore ?? '—'}
                              </p>
                            </div>
                            <div>
                              <p className="mb-1 text-xs font-medium text-muted-foreground">分析时间</p>
                              <p className="text-xs">{item.createdAt ? new Date(item.createdAt).toLocaleString('zh-CN') : '—'}</p>
                            </div>
                          </div>
                          <div className="mt-3">
                            <p className="mb-1 text-xs font-medium text-muted-foreground">分析摘要</p>
                            <p className="text-sm leading-relaxed text-foreground/80">
                              {item.analysisSummary || '暂无摘要'}
                            </p>
                          </div>
                          <div className="mt-3">
                            <button
                              type="button"
                              className="text-xs text-cyan hover:text-white transition-colors"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/history/${item.id}`);
                              }}
                            >
                              查看完整分析报告 →
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </AppPage>
  );
};

export default DailySummaryPage;
