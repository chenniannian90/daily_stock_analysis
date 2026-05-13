import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Target,
  Shield,
  Crosshair,
  Flag,
} from 'lucide-react';
import { historyApi } from '../api/history';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import type { AnalysisReport } from '../types/analysis';
import {
  ApiErrorAlert,
  Badge,
  EmptyState,
  SectionCard,
} from '../components/common';
import { cn } from '../utils/cn';

const SCORE_COLOR = (score?: number) => {
  if (score == null) return 'text-muted-foreground';
  if (score >= 70) return 'text-emerald-500';
  if (score >= 50) return 'text-amber-500';
  return 'text-red-500';
};

const HistoryDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const recordId = id ? Number(id) : null;

  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);

  // Page title
  useEffect(() => {
    const code = report?.meta.stockCode;
    document.title = code
      ? `${code}${report.meta.stockName ? ` ${report.meta.stockName}` : ''} - 分析详情 - DSA`
      : '分析详情 - DSA';
  }, [report]);

  const loadDetail = useCallback(async () => {
    if (!recordId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await historyApi.getDetail(recordId);
      setReport(data);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, [recordId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const goBack = () => navigate(-1);

  // Format prediction display
  const formatPrediction = (prediction?: string): { text: string; variant: 'success' | 'danger' | 'default' } => {
    if (!prediction) return { text: '--', variant: 'default' };
    const lower = prediction.toLowerCase();
    if (lower.includes('上涨') || lower.includes('看涨') || lower.includes('bullish')) {
      return { text: prediction, variant: 'success' };
    }
    if (lower.includes('下跌') || lower.includes('看跌') || lower.includes('bearish')) {
      return { text: prediction, variant: 'danger' };
    }
    return { text: prediction, variant: 'default' };
  };

  const strategy = report?.strategy;
  const hasStrategy = strategy && (strategy.idealBuy || strategy.secondaryBuy || strategy.stopLoss || strategy.takeProfit);
  const details = report?.details;
  const dashboard = details?.rawResult as Record<string, unknown> | undefined;

  const dashStr = (val: unknown) => (val != null ? String(val) : null);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen space-y-4 p-4 md:p-6">
        <button
          type="button"
          onClick={goBack}
          className="flex items-center gap-1.5 text-secondary-text hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">返回</span>
        </button>
        <ApiErrorAlert error={error} onDismiss={() => setError(null)} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen space-y-4 p-4 md:p-6">
        <button
          type="button"
          onClick={goBack}
          className="flex items-center gap-1.5 text-secondary-text hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">返回</span>
        </button>
        <EmptyState
          title="未找到分析报告"
          description="该分析记录不存在或已被删除"
        />
      </div>
    );
  }

  const { meta, summary } = report;
  const prediction = formatPrediction(summary.trendPrediction);

  return (
    <div className="min-h-screen space-y-4 p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={goBack}
          className="flex items-center gap-1.5 text-secondary-text hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">返回</span>
        </button>
      </div>

      {/* Title */}
      <div className="space-y-1">
        <h1 className="text-xl md:text-2xl font-semibold text-foreground">
          <span className="font-mono">{meta.stockCode}</span>
          {meta.stockName ? <span className="ml-2">{meta.stockName}</span> : null}
        </h1>
        <p className="text-xs md:text-sm text-secondary">
          {meta.createdAt ? new Date(meta.createdAt).toLocaleString('zh-CN') : ''}
          {meta.modelUsed ? <span className="ml-3">模型：{meta.modelUsed}</span> : null}
        </p>
      </div>

      {/* Price info */}
      {meta.currentPrice != null && (
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-foreground">
            ¥{meta.currentPrice}
          </span>
          {meta.changePct != null && (
            <span
              className={cn(
                'text-sm font-medium',
                meta.changePct > 0 ? 'text-emerald-500' : meta.changePct < 0 ? 'text-red-500' : 'text-muted-foreground',
              )}
            >
              {meta.changePct > 0 ? '+' : ''}{meta.changePct.toFixed(2)}%
            </span>
          )}
        </div>
      )}

      {/* Summary Card */}
      <SectionCard title="分析总结">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">情绪评分</span>
            <span className={cn('text-2xl font-bold', SCORE_COLOR(summary.sentimentScore))}>
              {summary.sentimentScore ?? '--'}
            </span>
            {summary.sentimentLabel && (
              <span className="text-xs text-muted-foreground">{summary.sentimentLabel}</span>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">操作建议</span>
            <span className="text-lg font-semibold text-foreground">{summary.operationAdvice || '--'}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">趋势预测</span>
            <Badge variant={prediction.variant} size="sm">
              {prediction.text}
            </Badge>
          </div>
        </div>
      </SectionCard>

      {/* Sniper Points */}
      {hasStrategy && (
        <SectionCard title="狙击点位">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {strategy.idealBuy && (
              <div className="flex items-start gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <Crosshair className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                <div>
                  <p className="text-xs text-muted-foreground">理想买入价</p>
                  <p className="text-lg font-bold text-emerald-500">{strategy.idealBuy}</p>
                </div>
              </div>
            )}
            {strategy.secondaryBuy && (
              <div className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                <Target className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                <div>
                  <p className="text-xs text-muted-foreground">次选买入价</p>
                  <p className="text-lg font-bold text-amber-500">{strategy.secondaryBuy}</p>
                </div>
              </div>
            )}
            {strategy.stopLoss && (
              <div className="flex items-start gap-3 rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                <Shield className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                <div>
                  <p className="text-xs text-muted-foreground">止损价</p>
                  <p className="text-lg font-bold text-red-500">{strategy.stopLoss}</p>
                </div>
              </div>
            )}
            {strategy.takeProfit && (
              <div className="flex items-start gap-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
                <Flag className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                <div>
                  <p className="text-xs text-muted-foreground">止盈价</p>
                  <p className="text-lg font-bold text-blue-500">{strategy.takeProfit}</p>
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {/* Analysis Summary */}
      <SectionCard title="分析摘要">
        <p className="text-sm leading-relaxed text-foreground/85 whitespace-pre-wrap">
          {summary.analysisSummary || '暂无摘要'}
        </p>
      </SectionCard>

      {/* Dashboard Detail from raw_result */}
      {dashboard && (
        <SectionCard title="决策仪表盘">
          <div className="space-y-6">
            {/* Core Conclusion */}
            {dashboard.core_conclusion != null && (
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">核心结论</h3>
                <p className="text-sm leading-relaxed text-foreground/80">
                  {dashStr(dashboard.core_conclusion)}
                </p>
              </div>
            )}

            {/* Data Perspective */}
            {dashboard.data_perspective != null && (
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">数据视角</h3>
                <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
                  <pre className="text-xs leading-relaxed text-foreground/70 whitespace-pre-wrap font-mono">
                    {dashStr(dashboard.data_perspective)}
                  </pre>
                </div>
              </div>
            )}

            {/* Intelligence */}
            {dashboard.intelligence != null && (
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">情报面</h3>
                <p className="text-sm leading-relaxed text-foreground/80">
                  {dashStr(dashboard.intelligence)}
                </p>
              </div>
            )}

            {/* Battle Plan */}
            {dashboard.battle_plan != null && (
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">作战计划</h3>
                <p className="text-sm leading-relaxed text-foreground/80">
                  {dashStr(dashboard.battle_plan)}
                </p>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {/* Related Boards */}
      {details?.belongBoards && details.belongBoards.length > 0 && (
        <SectionCard title="所属板块">
          <div className="flex flex-wrap gap-2">
            {details.belongBoards.map((board, idx) => (
              <Badge key={idx} variant="default" size="sm">
                {board.name}
              </Badge>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Sector Rankings */}
      {details?.sectorRankings && (details.sectorRankings.top?.length || details.sectorRankings.bottom?.length) && (
        <SectionCard title="板块排名">
          <div className="grid gap-4 sm:grid-cols-2">
            {details.sectorRankings.top && details.sectorRankings.top.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-1 text-xs font-medium text-emerald-500">
                  <TrendingUp className="h-3 w-3" />
                  涨幅领先
                </h3>
                <div className="space-y-1">
                  {details.sectorRankings.top.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="text-foreground/80">{item.name}</span>
                      {item.changePct != null && (
                        <span className="font-medium text-emerald-500">+{item.changePct.toFixed(2)}%</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {details.sectorRankings.bottom && details.sectorRankings.bottom.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-1 text-xs font-medium text-red-500">
                  <TrendingDown className="h-3 w-3" />
                  跌幅领先
                </h3>
                <div className="space-y-1">
                  {details.sectorRankings.bottom.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="text-foreground/80">{item.name}</span>
                      {item.changePct != null && (
                        <span className="font-medium text-red-500">{item.changePct.toFixed(2)}%</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      )}
    </div>
  );
};

export default HistoryDetailPage;
