import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, TrendingUp, TrendingDown, Minus, Tag, ChevronDown, ChevronUp } from 'lucide-react';
import { watchlistApi } from '../api/watchlist';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import {
  ApiErrorAlert,
  Badge,
  Card,
  EmptyState,
  Pagination,
  StatCard,
  TagPickerDrawer,
} from '../components/common';
import type { StockHistoryResponse, AnalysisHistoryItem, TagItem, TagInfo } from '../types/watchlist';
import { cn } from '../utils/cn';

const SCORE_COLOR = (score?: number) => {
  if (score == null) return 'text-muted-foreground';
  if (score >= 70) return 'text-emerald-500';
  if (score >= 50) return 'text-amber-500';
  return 'text-red-500';
};

const DEFAULT_PAGE_SIZE = 10;

const WatchlistDetailPage: React.FC = () => {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();

  // Page title
  useEffect(() => {
    document.title = code ? `${code} - 自选股详情 - DSA` : '自选股详情 - DSA';
  }, [code]);

  // State
  const [historyData, setHistoryData] = useState<StockHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  // Tags state
  const [allTags, setAllTags] = useState<TagItem[]>([]);
  const [stockTags, setStockTags] = useState<TagInfo[]>([]);
  const [tagsDrawerOpen, setTagsDrawerOpen] = useState(false);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [savingTags, setSavingTags] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);

  const totalPages = historyData ? Math.max(1, Math.ceil(historyData.total / DEFAULT_PAGE_SIZE)) : 1;

  // Load history
  const loadHistory = useCallback(async (page: number) => {
    if (!code) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await watchlistApi.getStockHistory(code, {
        page,
        limit: DEFAULT_PAGE_SIZE,
      });
      setHistoryData(data);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, [code]);

  // Load tags
  const loadTags = useCallback(async () => {
    if (!code) return;
    try {
      const [all, stock] = await Promise.all([
        watchlistApi.getTags(),
        watchlistApi.getStockTags(code),
      ]);
      setAllTags(all || []);
      setStockTags(stock || []);
    } catch (err) {
      console.error('Failed to load tags:', err);
    }
  }, [code]);

  useEffect(() => {
    void loadHistory(currentPage);
    void loadTags();
  }, [loadHistory, loadTags, currentPage]);

  // Go back to list
  const goBack = () => {
    navigate('/watchlist');
  };

  // Open tags drawer
  const handleOpenTagsDrawer = () => {
    setSelectedTagIds(stockTags.map(t => t.id));
    setTagError(null);
    setTagsDrawerOpen(true);
  };

  // Save tags
  const handleSaveTags = async () => {
    if (!code) return;
    setSavingTags(true);
    setTagError(null);
    try {
      await watchlistApi.setStockTags(code, selectedTagIds);
      setTagsDrawerOpen(false);
      // Reload stock tags
      const updated = await watchlistApi.getStockTags(code);
      setStockTags(updated || []);
    } catch (err: any) {
      setTagError(err?.message || '保存失败');
    } finally {
      setSavingTags(false);
    }
  };

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

  // Render direction icon
  const renderDirectionIcon = (correct?: boolean) => {
    if (correct === undefined || correct === null) return null;
    return correct ? (
      <TrendingUp className="h-4 w-4 text-success" />
    ) : (
      <TrendingDown className="h-4 w-4 text-danger" />
    );
  };

  // Format accuracy
  const formatAccuracy = (accuracy?: number): string => {
    if (accuracy === undefined || accuracy === null) return '--';
    return `${(accuracy * 100).toFixed(1)}%`;
  };

  // Stats from API response
  const stats = historyData?.accuracyStats;
  const directionAccuracy = stats?.directionAccuracy;

  return (
    <div className="min-h-screen space-y-4 p-4 md:p-6">
      {/* Header with back button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={goBack}
          className="flex items-center gap-1.5 text-secondary-text hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">返回列表</span>
        </button>
      </div>

      {/* Title */}
      <div className="space-y-1">
        <h1 className="text-xl md:text-2xl font-semibold text-foreground">
          {code ? (
            <>
              <span className="font-mono">{code}</span>
            </>
          ) : (
            '自选股详情'
          )}
        </h1>
        <p className="text-xs md:text-sm text-secondary">
          查看该股票的历史分析记录和预测准确率统计
        </p>
      </div>

      {/* Error alert */}
      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}

      {/* Tags card */}
      <Card padding="md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-secondary-text" />
            <span className="text-sm font-medium text-foreground">标签</span>
          </div>
          <button
            type="button"
            onClick={handleOpenTagsDrawer}
            className="text-sm text-cyan hover:text-white transition-colors"
          >
            编辑标签
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5 min-h-[28px]">
          {stockTags.length === 0 ? (
            <span className="text-xs text-muted-text">暂无标签，点击"编辑标签"添加</span>
          ) : (
            stockTags.map(tag => (
              <Badge
                key={tag.id}
                variant="default"
                size="sm"
                style={{
                  borderColor: tag.color || '#00d4ff',
                  backgroundColor: `${tag.color || '#00d4ff'}18`,
                  color: tag.color || '#00d4ff',
                }}
              >
                {tag.name}
              </Badge>
            ))
          )}
        </div>
      </Card>

      {/* Accuracy Stats Cards */}
      {stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="方向准确率"
            value={formatAccuracy(directionAccuracy)}
            tone={directionAccuracy && directionAccuracy >= 0.5 ? 'success' : directionAccuracy ? 'warning' : 'default'}
            icon={
              directionAccuracy && directionAccuracy >= 0.5 ? (
                <TrendingUp className="h-5 w-5 text-success" />
              ) : directionAccuracy ? (
                <TrendingDown className="h-5 w-5 text-warning" />
              ) : (
                <Minus className="h-5 w-5 text-secondary-text" />
              )
            }
          />
          <StatCard
            label="预测正确"
            value={stats.winCount}
            tone="success"
          />
          <StatCard
            label="预测错误"
            value={stats.lossCount}
            tone="danger"
          />
          <StatCard
            label="持平/未验证"
            value={stats.neutralCount}
            tone="default"
          />
        </div>
      ) : null}

      {/* History Table */}
      <Card padding="md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-foreground">历史分析记录</h2>
          {historyData ? (
            <span className="text-xs text-secondary-text">共 {historyData.total} 条记录</span>
          ) : null}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
          </div>
        ) : !historyData || historyData.items.length === 0 ? (
          <EmptyState
            title="暂无分析记录"
            description="该股票尚未有历史分析记录，进行分析后会在此展示"
            className="border-dashed"
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-xs text-secondary-text">
                    <th className="text-left py-3 pr-4 font-medium">日期</th>
                    <th className="text-center py-3 pr-4 font-medium">评分</th>
                    <th className="text-left py-3 pr-4 font-medium">预测方向</th>
                    <th className="text-left py-3 pr-4 font-medium">操作建议</th>
                    <th className="text-center py-3 pr-4 font-medium">回测结果</th>
                    <th className="text-center py-3 font-medium">准确性</th>
                    <th className="text-center py-3 font-medium w-10">展开</th>
                  </tr>
                </thead>
                <tbody>
                  {historyData.items.map((item: AnalysisHistoryItem, idx: number) => {
                    const prediction = formatPrediction(item.trendPrediction);
                    const isExpanded = expandedIdx === idx;
                    return (
                      <>
                        <tr
                          key={item.id}
                          className={cn(
                            'border-b border-white/5 hover:bg-white/[0.02] transition-colors cursor-pointer',
                          )}
                          onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                        >
                          <td className="py-3 pr-4 text-secondary-text">
                            {item.analysisDate || item.analysisTime ? (
                              <span>
                                {item.analysisDate || ''}
                                {item.analysisTime ? (
                                  <span className="text-xs ml-1 text-muted-text">
                                    {item.analysisTime}
                                  </span>
                                ) : null}
                              </span>
                            ) : (
                              '--'
                            )}
                          </td>
                          <td className={cn('py-3 pr-4 text-center font-bold', SCORE_COLOR(item.sentimentScore))}>
                            {item.sentimentScore ?? '--'}
                          </td>
                          <td className="py-3 pr-4">
                            {item.trendPrediction ? (
                              <Badge
                                variant={prediction.variant}
                                size="sm"
                              >
                                {prediction.text}
                              </Badge>
                            ) : (
                              <span className="text-secondary-text">--</span>
                            )}
                          </td>
                          <td className="py-3 pr-4 text-secondary-text max-w-[200px] truncate">
                            {item.operationAdvice || '--'}
                          </td>
                          <td className="py-3 pr-4 text-center">
                            {item.backtestOutcome ? (
                              <span className="text-xs text-secondary-text">
                                {item.backtestOutcome}
                              </span>
                            ) : (
                              <span className="text-muted-text">--</span>
                            )}
                          </td>
                          <td className="py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {renderDirectionIcon(item.directionCorrect)}
                              <span className="text-xs">
                                {item.directionCorrect === true ? (
                                  <span className="text-success">正确</span>
                                ) : item.directionCorrect === false ? (
                                  <span className="text-danger">错误</span>
                                ) : (
                                  <span className="text-muted-text">--</span>
                                )}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 text-center">
                            {isExpanded
                              ? <ChevronUp className="mx-auto h-4 w-4 text-muted-foreground" />
                              : <ChevronDown className="mx-auto h-4 w-4 text-muted-foreground" />
                            }
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${item.id}-expanded`} className="border-b border-white/5 bg-white/[0.02]">
                            <td colSpan={7} className="px-6 py-4">
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
                                  <p className="mb-1 text-xs font-medium text-muted-foreground">趋势预测</p>
                                  <p>{item.trendPrediction || '—'}</p>
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
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="mt-4">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
              />
            </div>
          </>
        )}
      </Card>

      {/* Tags Drawer */}
      <TagPickerDrawer
        isOpen={tagsDrawerOpen}
        onClose={() => setTagsDrawerOpen(false)}
        tags={allTags}
        selectedTagIds={selectedTagIds}
        onToggleTag={(tagId) => {
          setSelectedTagIds((prev) =>
            prev.includes(tagId)
              ? prev.filter((id) => id !== tagId)
              : [...prev, tagId]
          );
        }}
        onSave={() => { handleSaveTags(); }}
        saving={savingTags}
        title={`编辑标签 - ${code || ''}`}
        error={tagError}
        onDismissError={() => setTagError(null)}
      />
    </div>
  );
};

export default WatchlistDetailPage;
