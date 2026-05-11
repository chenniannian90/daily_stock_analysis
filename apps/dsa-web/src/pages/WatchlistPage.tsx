import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Tag, Trash2, X, ChevronRight, TrendingUp, TrendingDown, FolderOpen } from 'lucide-react';
import { watchlistApi } from '../api/watchlist';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import {
  ApiErrorAlert,
  Badge,
  Card,
  ConfirmDialog,
  Drawer,
  EmptyState,
  InlineAlert,
  Input,
  Select,
  TagPickerDrawer,
} from '../components/common';
import type { GroupInfo, ItemInfo, TagItem } from '../types/watchlist';
import { StockAutocomplete } from '../components/StockAutocomplete';

const DEFAULT_PAGE_SIZE = 20;

// Format number with appropriate precision
const formatNumber = (num: number | undefined, decimals = 2): string => {
  if (num === undefined || num === null) return '--';
  return num.toFixed(decimals);
};

// Format market value (backend returns 元, convert to 亿 first)
const formatMarketValue = (mv: number | undefined): string => {
  if (mv === undefined || mv === null) return '--';
  const yi = mv / 100000000;
  if (yi >= 10000) {
    return `${(yi / 10000).toFixed(2)}万亿`;
  }
  return `${yi.toFixed(2)}亿`;
};

// Determine badge variant based on analysis prediction and score
const getAnalysisBadge = (
  prediction?: string,
  score?: number
): { variant: 'success' | 'danger' | 'warning' | 'info' | 'default'; label: string } | null => {
  if (!prediction && score === undefined) return null;
  const label = prediction && score !== undefined
    ? `${prediction} ${score}`
    : (prediction || `${score}`);
  const p = (prediction || '').toLowerCase();
  if (p.includes('强烈看多') || p.includes('看多') || p.includes('买入') || p.includes('强烈买入')) {
    return { variant: 'danger', label };
  }
  if (p.includes('看空') || p.includes('强烈看空') || p.includes('卖出') || p.includes('强烈卖出')) {
    return { variant: 'success', label };
  }
  if (p.includes('持有') || p.includes('观望') || p.includes('震荡')) {
    return { variant: 'info', label };
  }
  if (score !== undefined) {
    if (score >= 60) return { variant: 'danger', label };
    if (score >= 40) return { variant: 'info', label };
    return { variant: 'success', label };
  }
  return { variant: 'default', label };
};

const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();

  // Page title
  useEffect(() => {
    document.title = '自选股 - DSA';
  }, []);

  // State
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [tags, setTags] = useState<TagItem[]>([]);
  const [items, setItems] = useState<ItemInfo[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedGroupId, setSelectedGroupId] = useState<number | 'all'>('all');
  const [selectedTagId, setSelectedTagId] = useState<number | 'all'>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);

  // Add stock drawer
  const [addStockDrawerOpen, setAddStockDrawerOpen] = useState(false);
  const [newStockCode, setNewStockCode] = useState('');
  const [addingStock, setAddingStock] = useState(false);
  const [addStockError, setAddStockError] = useState<string | null>(null);

  // Manage tags drawer
  const [tagsDrawerOpen, setTagsDrawerOpen] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState('#00d4ff');
  const [creatingTag, setCreatingTag] = useState(false);
  const [tagActionError, setTagActionError] = useState<string | null>(null);
  const [editingTag, setEditingTag] = useState<TagItem | null>(null);
  const [editTagName, setEditTagName] = useState('');
  const [editTagColor, setEditTagColor] = useState('');
  const [updatingTag, setUpdatingTag] = useState(false);
  const [deletingTagId, setDeletingTagId] = useState<number | null>(null);

  // Delete confirmation
  const [pendingDeleteItem, setPendingDeleteItem] = useState<ItemInfo | null>(null);
  const [deletingItem, setDeletingItem] = useState(false);

  // Edit item tags drawer
  const [editTagsDrawerOpen, setEditTagsDrawerOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<ItemInfo | null>(null);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [savingTags, setSavingTags] = useState(false);
  const [tagSaveError, setTagSaveError] = useState<string | null>(null);

  // Move item group drawer
  const [moveGroupDrawerOpen, setMoveGroupDrawerOpen] = useState(false);
  const [movingItem, setMovingItem] = useState<ItemInfo | null>(null);
  const [targetGroupId, setTargetGroupId] = useState<number>(0);
  const [movingToGroup, setMovingToGroup] = useState(false);

  // Create group modal
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);

  // Edit group
  const [editingGroupId, setEditingGroupId] = useState<number | null>(null);
  const [editGroupName, setEditGroupName] = useState('');
  const [updatingGroup, setUpdatingGroup] = useState(false);

  // Delete group
  const [deletingGroupId, setDeletingGroupId] = useState<number | null>(null);
  const [deletingGroup, setDeletingGroup] = useState(false);

  const totalPages = Math.max(1, Math.ceil(totalItems / DEFAULT_PAGE_SIZE));

  // Load groups
  const loadGroups = useCallback(async () => {
    try {
      const data = await watchlistApi.listGroups();
      setGroups(data || []);
    } catch (err) {
      console.error('Failed to load groups:', err);
    }
  }, []);

  // Load tags
  const loadTags = useCallback(async () => {
    try {
      const data = await watchlistApi.getTags();
      setTags(data || []);
    } catch (err) {
      console.error('Failed to load tags:', err);
    }
  }, []);

  // Load items
  const loadItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // groupId=0 means "all" (聚合所有条目并去重)
      const groupId = selectedGroupId === 'all' ? 0 : selectedGroupId;
      const data = await watchlistApi.listItems(groupId, DEFAULT_PAGE_SIZE, (currentPage - 1) * DEFAULT_PAGE_SIZE);
      setItems(data.items || []);
      setTotalItems(data.total || 0);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, selectedGroupId]);

  useEffect(() => {
    void loadGroups();
    void loadTags();
  }, [loadGroups, loadTags]);

  useEffect(() => {
    if (groups.length > 0) {
      void loadItems();
    }
  }, [loadItems, groups.length]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedGroupId, selectedTagId]);

  // Add stock (called by StockAutocomplete onSubmit)
  const handleAddStock = async (code: string, _name?: string) => {
    if (!code.trim()) {
      setAddStockError('请输入股票代码');
      return;
    }
    setAddingStock(true);
    setAddStockError(null);
    try {
      const groupId = selectedGroupId === 'all' ? 0 : selectedGroupId;
      await watchlistApi.addItem(code.trim(), [groupId]);
      setNewStockCode('');
      setAddStockDrawerOpen(false);
      await loadItems();
      await loadGroups();
    } catch (err) {
      setAddStockError(getParsedApiError(err).message || '添加失败');
    } finally {
      setAddingStock(false);
    }
  };

  // Delete item
  const handleDeleteItem = async () => {
    if (!pendingDeleteItem) return;
    setDeletingItem(true);
    try {
      // In "all" view, remove from all groups (groupId=0 removes from all)
      // In specific group view, remove from that group only
      const groupId = selectedGroupId === 'all' ? 0 : selectedGroupId;
      await watchlistApi.removeItem(pendingDeleteItem.tsCode, groupId);
      setPendingDeleteItem(null);
      if (items.length === 1 && currentPage > 1) {
        setCurrentPage(currentPage - 1);
      } else {
        await loadItems();
      }
      await loadGroups(); // Refresh to update stock count
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setDeletingItem(false);
    }
  };


  // Open edit tags drawer
  const handleOpenEditTags = (item: ItemInfo) => {
    setEditingItem(item);
    setSelectedTagIds(item.tags.map(t => t.id));
    setTagSaveError(null);
    setEditTagsDrawerOpen(true);
  };

  // Save item tags
  const handleSaveTags = async () => {
    if (!editingItem) return;
    setSavingTags(true);
    setTagSaveError(null);
    try {
      await watchlistApi.setStockTags(editingItem.tsCode, selectedTagIds);
      setEditTagsDrawerOpen(false);
      setEditingItem(null);
      await loadItems();
    } catch (err: any) {
      setTagSaveError(err?.message || '保存标签失败');
    } finally {
      setSavingTags(false);
    }
  };

  // Open move group drawer
  const handleOpenMoveGroup = (item: ItemInfo) => {
    setMovingItem(item);
    setTargetGroupId(selectedGroupId === 'all' ? 0 : selectedGroupId);
    setMoveGroupDrawerOpen(true);
  };

  // Move item to group
  const handleMoveToGroup = async () => {
    if (!movingItem) return;
    setMovingToGroup(true);
    try {
      const currentGroupId = selectedGroupId === 'all' ? 0 : selectedGroupId;
      await watchlistApi.moveItem(movingItem.tsCode, currentGroupId, targetGroupId);
      setMoveGroupDrawerOpen(false);
      setMovingItem(null);
      await loadItems();
      await loadGroups();
    } catch (err) {
      console.error('Move failed:', err);
    } finally {
      setMovingToGroup(false);
    }
  };

  // Create tag
  const handleCreateTag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTagName.trim()) {
      setTagActionError('请输入标签名称');
      return;
    }
    setCreatingTag(true);
    setTagActionError(null);
    try {
      await watchlistApi.createTag({
        name: newTagName.trim(),
        color: newTagColor,
      });
      setNewTagName('');
      setNewTagColor('#00d4ff');
      await loadTags();
    } catch (err) {
      setTagActionError(getParsedApiError(err).message || '创建失败');
    } finally {
      setCreatingTag(false);
    }
  };

  // Update tag
  const handleUpdateTag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTag || !editTagName.trim()) {
      setTagActionError('请输入标签名称');
      return;
    }
    setUpdatingTag(true);
    setTagActionError(null);
    try {
      await watchlistApi.updateTag(editingTag.id, {
        name: editTagName.trim(),
        color: editTagColor,
      });
      setEditingTag(null);
      await loadTags();
    } catch (err) {
      setTagActionError(getParsedApiError(err).message || '更新失败');
    } finally {
      setUpdatingTag(false);
    }
  };

  // Delete tag
  const handleDeleteTag = async (tagId: number) => {
    try {
      await watchlistApi.deleteTag(tagId);
      setDeletingTagId(null);
      await loadTags();
    } catch (err) {
      setTagActionError(getParsedApiError(err).message || '删除失败');
    }
  };

  // Create group
  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) {
      setGroupError('请输入分组名称');
      return;
    }
    setCreatingGroup(true);
    setGroupError(null);
    try {
      await watchlistApi.createGroup(newGroupName.trim());
      setNewGroupName('');
      setShowCreateGroup(false);
      await loadGroups();
    } catch (err) {
      setGroupError(getParsedApiError(err).message || '创建失败');
    } finally {
      setCreatingGroup(false);
    }
  };

  // Update group
  const handleUpdateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editGroupName.trim() || !editingGroupId) {
      setGroupError('请输入分组名称');
      return;
    }
    setUpdatingGroup(true);
    setGroupError(null);
    try {
      await watchlistApi.updateGroup(editingGroupId, editGroupName.trim());
      setEditingGroupId(null);
      setEditGroupName('');
      await loadGroups();
    } catch (err) {
      setGroupError(getParsedApiError(err).message || '更新失败');
    } finally {
      setUpdatingGroup(false);
    }
  };

  // Delete group
  const handleDeleteGroup = async () => {
    if (!deletingGroupId) return;
    setDeletingGroup(true);
    try {
      const deletedId = deletingGroupId;
      await watchlistApi.deleteGroup(deletedId);
      setDeletingGroupId(null);
      // Reset to "all" view if the deleted group was selected
      if (selectedGroupId === deletedId) {
        setSelectedGroupId('all');
      }
      await loadGroups();
      await loadItems();
    } catch (err) {
      setDeletingGroupId(null);
      setGroupError(getParsedApiError(err).message || '删除失败');
    } finally {
      setDeletingGroup(false);
    }
  };
  const goToDetail = (tsCode: string) => {
    navigate(`/watchlist/${tsCode}`);
  };

  return (
    <div className="min-h-screen space-y-4 p-4 md:p-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-xl md:text-2xl font-semibold text-foreground">自选股管理</h1>
        <p className="text-xs md:text-sm text-secondary">
          管理您的自选股列表，查看历史分析记录和预测准确率
        </p>
      </div>

      {/* Error alert */}
      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}

      {/* Filters */}
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3">
          {/* Group tabs */}
          <div className="flex flex-wrap gap-2 items-center">
            <button
              type="button"
              onClick={() => setSelectedGroupId('all')}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                selectedGroupId === 'all'
                  ? 'bg-cyan/20 text-cyan border border-cyan/30'
                  : 'bg-white/5 text-secondary-text border border-white/10 hover:bg-white/10'
              }`}
            >
              全部
            </button>
            {groups.filter(g => g.id !== 0).map((group) => (
              <div
                key={group.id}
                className={`flex items-center rounded-lg text-sm transition-all ${
                  selectedGroupId === group.id
                    ? 'bg-cyan/20 text-cyan border border-cyan/30'
                    : 'bg-white/5 text-secondary-text border border-white/10 hover:bg-white/10'
                }`}
              >
                <button
                  type="button"
                  onClick={() => setSelectedGroupId(group.id)}
                  className="px-3 py-1.5"
                >
                  {group.name} ({group.stockCount})
                </button>
                {selectedGroupId === group.id && (
                  <div className="flex items-center pr-1">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingGroupId(group.id);
                        setEditGroupName(group.name);
                      }}
                      className="p-0.5 text-secondary-text hover:text-cyan transition-colors"
                      title="重命名"
                    >
                      <Tag className="h-3 w-3 rotate-90" />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeletingGroupId(group.id);
                      }}
                      className="p-0.5 text-secondary-text hover:text-danger transition-colors"
                      title="删除"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={() => setShowCreateGroup(true)}
              className="px-3 py-1.5 rounded-lg text-sm border border-dashed border-white/20 text-secondary-text hover:border-white/40 hover:text-foreground transition-all"
            >
              <Plus className="h-4 w-4 inline-block mr-1" />
              新建分组
            </button>
          </div>

          {/* Rename group inline form */}
          {editingGroupId != null ? (
            <div className="flex items-center gap-2 mt-2">
              <form onSubmit={handleUpdateGroup} className="flex items-center gap-2">
                <input
                  type="text"
                  value={editGroupName}
                  onChange={(e) => setEditGroupName(e.target.value)}
                  placeholder="输入新名称"
                  className="input-surface h-8 w-40 rounded border bg-transparent px-3 text-sm"
                  autoFocus
                />
                <button
                  type="submit"
                  className="btn-secondary text-xs px-3 py-1.5"
                  disabled={updatingGroup}
                >
                  {updatingGroup ? '保存中...' : '保存'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditingGroupId(null);
                    setGroupError(null);
                  }}
                  className="text-xs text-secondary-text hover:text-foreground"
                >
                  取消
                </button>
              </form>
            </div>
          ) : null}

          {/* Group error */}
          {groupError ? (
            <InlineAlert
              variant="danger"
              className="mt-2 rounded-lg px-3 py-2 text-xs shadow-none"
              message={groupError}
            />
          ) : null}

          {/* Tag filter */}
          <Select
            value={selectedTagId === 'all' ? '' : String(selectedTagId)}
            onChange={(val) => setSelectedTagId(val === '' ? 'all' : Number(val))}
            options={[
              { value: '', label: '全部标签' },
              ...tags.map((tag) => ({ value: String(tag.id), label: tag.name })),
            ]}
            placeholder="筛选标签"
          />

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setTagsDrawerOpen(true)}
              className="btn-secondary text-sm flex items-center gap-1.5"
            >
              <Tag className="h-4 w-4" />
              管理标签
            </button>
            <button
              type="button"
              onClick={() => setAddStockDrawerOpen(true)}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              添加股票
            </button>
          </div>
        </div>
      </div>

      {/* Create group inline form */}
      {showCreateGroup ? (
        <Card padding="md">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-foreground">新建分组</h3>
            <button
              type="button"
              onClick={() => {
                setShowCreateGroup(false);
                setNewGroupName('');
                setGroupError(null);
              }}
              className="text-secondary-text hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          {groupError ? (
            <InlineAlert
              variant="danger"
              className="mb-3 rounded-lg px-3 py-2 text-xs shadow-none"
              message={groupError}
            />
          ) : null}
          <form onSubmit={handleCreateGroup} className="flex gap-2">
            <Input
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              placeholder="分组名称"
              className="flex-1"
            />
            <button
              type="submit"
              className="btn-secondary text-sm"
              disabled={creatingGroup}
            >
              {creatingGroup ? '创建中...' : '创建'}
            </button>
          </form>
        </Card>
      ) : null}

      {/* Stock list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="暂无自选股"
          description="点击右上角「添加股票」按钮，将感兴趣的股票加入自选列表"
          className="border-dashed"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map((item) => {
            const isPositive = (item.changePct ?? 0) >= 0;
            return (
              <div
                key={item.tsCode}
                className="group cursor-pointer"
                onClick={() => goToDetail(item.tsCode)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    goToDetail(item.tsCode);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <Card
                  padding="md"
                  hoverable
                  className="relative"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-foreground">{item.tsCode}</span>
                        {item.name ? (
                          <span className="text-sm text-secondary-text truncate">{item.name}</span>
                        ) : null}
                      </div>

                      {/* Quote data */}
                      <div className="mt-2 flex items-center gap-4 text-xs">
                        {item.close !== undefined ? (
                          <span className="text-foreground font-medium">
                            {formatNumber(item.close)}
                          </span>
                        ) : null}
                        {item.changePct !== undefined ? (
                          <span className={`flex items-center gap-0.5 ${isPositive ? 'text-red-400' : 'text-green-400'}`}>
                            {isPositive ? (
                              <TrendingUp className="h-3 w-3" />
                            ) : (
                              <TrendingDown className="h-3 w-3" />
                            )}
                            {isPositive ? '+' : ''}{formatNumber(item.changePct)}%
                          </span>
                        ) : null}
                      </div>

                      {/* Additional info */}
                      <div className="mt-1 flex items-center gap-3 text-xs text-secondary-text">
                        {item.totalMv !== undefined ? (
                          <span>市值: {formatMarketValue(item.totalMv)}</span>
                        ) : null}
                        {item.turnoverRate !== undefined ? (
                          <span>换手: {formatNumber(item.turnoverRate)}%</span>
                        ) : null}
                      </div>

                      {/* Analysis result badge */}
                      {(() => {
                        const badge = getAnalysisBadge(item.lastPrediction, item.lastScore);
                        return badge ? (
                          <div className="mt-1.5">
                            <Badge variant={badge.variant} size="sm">
                              {badge.label}
                            </Badge>
                          </div>
                        ) : null;
                      })()}

                      {/* Tags */}
                      <div className="mt-2 flex flex-wrap gap-1">
                        {item.tags.map((tag) => (
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
                        ))}
                        {item.industry ? (
                          <Badge variant="info" size="sm">
                            {item.industry}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <ChevronRight className="h-4 w-4 text-secondary-text group-hover:text-cyan transition-colors" />
                      <div className="flex items-center gap-0.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenEditTags(item);
                          }}
                          onKeyDown={(e) => e.stopPropagation()}
                          className="p-1 rounded text-secondary-text hover:text-cyan hover:bg-cyan/10 transition-all"
                          aria-label="打标签"
                          title="打标签"
                        >
                          <Tag className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenMoveGroup(item);
                          }}
                          onKeyDown={(e) => e.stopPropagation()}
                          className="p-1 rounded text-secondary-text hover:text-cyan hover:bg-cyan/10 transition-all"
                          aria-label="移动分组"
                          title="移动分组"
                        >
                          <FolderOpen className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingDeleteItem(item);
                          }}
                          onKeyDown={(e) => e.stopPropagation()}
                          className="p-1 rounded text-secondary-text hover:text-danger hover:bg-danger/10 transition-all"
                          aria-label="删除"
                          title="删除"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 ? (
        <div className="flex items-center justify-center gap-2">
          <button
            type="button"
            className="btn-secondary text-sm px-3 py-1.5"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          >
            上一页
          </button>
          <span className="text-sm text-secondary-text">
            第 {currentPage} / {totalPages} 页（共 {totalItems} 只）
          </span>
          <button
            type="button"
            className="btn-secondary text-sm px-3 py-1.5"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
          >
            下一页
          </button>
        </div>
      ) : null}

      {/* Add Stock Drawer */}
      <Drawer
        isOpen={addStockDrawerOpen}
        onClose={() => {
          setAddStockDrawerOpen(false);
          setNewStockCode('');
          setAddStockError(null);
        }}
        title="添加自选股"
      >
        {addStockError ? (
          <InlineAlert
            variant="danger"
            className="mb-4 rounded-lg px-3 py-2 text-sm shadow-none"
            message={addStockError}
          />
        ) : null}
        <div className="space-y-4">
          <StockAutocomplete
            value={newStockCode}
            onChange={setNewStockCode}
            onSubmit={handleAddStock}
            placeholder="输入代码/名称/拼音搜索"
            disabled={addingStock}
          />
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              className="btn-secondary flex-1"
              onClick={() => {
                setAddStockDrawerOpen(false);
                setNewStockCode('');
                setAddStockError(null);
              }}
            >
              取消
            </button>
          </div>
        </div>
      </Drawer>

      {/* Edit Tags Drawer */}
      <TagPickerDrawer
        isOpen={editTagsDrawerOpen}
        onClose={() => {
          setEditTagsDrawerOpen(false);
          setEditingItem(null);
          setSelectedTagIds([]);
          setTagSaveError(null);
        }}
        tags={tags}
        selectedTagIds={selectedTagIds}
        onToggleTag={(tagId: number) => {
          setSelectedTagIds((prev) =>
            prev.includes(tagId)
              ? prev.filter((id) => id !== tagId)
              : [...prev, tagId]
          );
        }}
        onSave={() => { handleSaveTags(); }}
        saving={savingTags}
        title={`编辑标签 - ${editingItem?.name || editingItem?.tsCode || ''}`}
        error={tagSaveError}
        onDismissError={() => setTagSaveError(null)}
      />

      {/* Move Group Drawer */}
      <Drawer
        isOpen={moveGroupDrawerOpen}
        onClose={() => {
          setMoveGroupDrawerOpen(false);
          setMovingItem(null);
        }}
        title={`移动分组 - ${movingItem?.name || movingItem?.tsCode || ''}`}
      >
        <div className="space-y-4">
          <div className="text-sm text-secondary-text mb-2">选择目标分组</div>
          <div className="space-y-2">
            {groups.map((group) => (
              <button
                key={group.id}
                type="button"
                className={`w-full px-4 py-3 text-left rounded-lg transition-all ${
                  targetGroupId === group.id
                    ? 'bg-cyan/20 border border-cyan'
                    : 'bg-surface border border-border hover:border-cyan/50'
                }`}
                onClick={() => setTargetGroupId(group.id)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">{group.name}</span>
                  <span className="text-xs text-secondary-text">{group.stockCount} 只</span>
                </div>
              </button>
            ))}
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              className="btn-secondary flex-1"
              onClick={() => {
                setMoveGroupDrawerOpen(false);
                setMovingItem(null);
              }}
            >
              取消
            </button>
            <button
              type="button"
              className="btn-primary flex-1"
              disabled={movingToGroup}
              onClick={handleMoveToGroup}
            >
              {movingToGroup ? '移动中...' : '确认移动'}
            </button>
          </div>
        </div>
      </Drawer>

      {/* Manage Tags Drawer */}
      <Drawer
        isOpen={tagsDrawerOpen}
        onClose={() => {
          setTagsDrawerOpen(false);
          setNewTagName('');
          setNewTagColor('#00d4ff');
          setEditingTag(null);
          setTagActionError(null);
        }}
        title="管理标签"
      >
        {tagActionError ? (
          <InlineAlert
            variant="danger"
            className="mb-4 rounded-lg px-3 py-2 text-sm shadow-none"
            message={tagActionError}
          />
        ) : null}

        {/* Create new tag */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-foreground mb-3">创建新标签</h4>
          <form onSubmit={handleCreateTag} className="space-y-3">
            <Input
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              placeholder="标签名称"
            />
            <div className="flex items-center gap-3">
              <label className="text-sm text-secondary-text">颜色</label>
              <input
                type="color"
                value={newTagColor}
                onChange={(e) => setNewTagColor(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer border border-white/20"
              />
            </div>
            <button
              type="submit"
              className="btn-secondary w-full text-sm"
              disabled={creatingTag}
            >
              {creatingTag ? '创建中...' : '创建标签'}
            </button>
          </form>
        </div>

        {/* Existing tags */}
        <div>
          <h4 className="text-sm font-medium text-foreground mb-3">现有标签</h4>
          {tags.length === 0 ? (
            <p className="text-sm text-secondary-text">暂无标签</p>
          ) : (
            <div className="space-y-2">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg border border-white/10 bg-white/[0.02]"
                >
                  {editingTag?.id === tag.id ? (
                    <form onSubmit={handleUpdateTag} className="flex-1 flex items-center gap-2">
                      <input
                        type="text"
                        value={editTagName}
                        onChange={(e) => setEditTagName(e.target.value)}
                        className="input-surface input-focus-glow h-9 flex-1 rounded-lg border bg-transparent px-3 text-sm"
                      />
                      <input
                        type="color"
                        value={editTagColor}
                        onChange={(e) => setEditTagColor(e.target.value)}
                        className="w-8 h-8 rounded cursor-pointer border border-white/20"
                      />
                      <button
                        type="submit"
                        className="btn-secondary text-xs px-2 py-1"
                        disabled={updatingTag}
                      >
                        保存
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingTag(null);
                          setTagActionError(null);
                        }}
                        className="text-xs text-secondary-text hover:text-foreground"
                      >
                        取消
                      </button>
                    </form>
                  ) : (
                    <>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: tag.color }}
                        />
                        <span className="text-sm text-foreground">{tag.name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingTag(tag);
                            setEditTagName(tag.name);
                            setEditTagColor(tag.color);
                          }}
                          className="text-xs text-secondary-text hover:text-cyan px-2 py-1"
                        >
                          编辑
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeletingTagId(tag.id)}
                          className="text-xs text-secondary-text hover:text-danger px-2 py-1"
                        >
                          删除
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Drawer>

      {/* Delete Item Confirmation */}
      <ConfirmDialog
        isOpen={!!pendingDeleteItem}
        title="删除自选股"
        message={`确认从自选列表中删除 ${pendingDeleteItem?.tsCode}${pendingDeleteItem?.name ? ` (${pendingDeleteItem.name})` : ''} 吗？`}
        confirmText={deletingItem ? '删除中...' : '确认删除'}
        cancelText="取消"
        isDanger
        onConfirm={handleDeleteItem}
        onCancel={() => setPendingDeleteItem(null)}
      />

      {/* Delete Tag Confirmation */}
      <ConfirmDialog
        isOpen={!!deletingTagId}
        title="删除标签"
        message="确认删除这个标签吗？删除后，股票上的标签关联也会被移除。"
        confirmText="确认删除"
        cancelText="取消"
        isDanger
        onConfirm={() => {
          if (deletingTagId) {
            void handleDeleteTag(deletingTagId);
          }
        }}
        onCancel={() => setDeletingTagId(null)}
      />

      {/* Delete Group Confirmation */}
      <ConfirmDialog
        isOpen={!!deletingGroupId}
        title="删除分组"
        message="确认删除这个分组吗？分组内的股票条目也会被移除。"
        confirmText={deletingGroup ? '删除中...' : '确认删除'}
        cancelText="取消"
        isDanger
        onConfirm={() => { handleDeleteGroup(); }}
        onCancel={() => setDeletingGroupId(null)}
      />
    </div>
  );
};

export default WatchlistPage;
