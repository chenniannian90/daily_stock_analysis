import type React from 'react';
import { Drawer } from './Drawer';
import { InlineAlert } from './InlineAlert';
import type { TagItem } from '../../types/watchlist';

interface TagPickerDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  tags: TagItem[];
  selectedTagIds: number[];
  onToggleTag: (tagId: number) => void;
  onSave: () => void;
  saving: boolean;
  title: string;
  error?: string | null;
  onDismissError?: () => void;
}

export const TagPickerDrawer: React.FC<TagPickerDrawerProps> = ({
  isOpen,
  onClose,
  tags,
  selectedTagIds,
  onToggleTag,
  onSave,
  saving,
  title,
  error,
  onDismissError,
}) => {
  return (
    <Drawer isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-4">
        {error ? (
          <InlineAlert
            variant="danger"
            className="rounded-lg px-3 py-2 text-xs shadow-none"
            message={error}
            action={
              onDismissError ? (
                <button
                  type="button"
                  onClick={onDismissError}
                  className="text-xs underline hover:no-underline"
                >
                  关闭
                </button>
              ) : undefined
            }
          />
        ) : null}

        <div className="text-sm text-secondary-text mb-2">选择标签</div>
        {tags.length === 0 ? (
          <div className="text-sm text-secondary-text">暂无标签，请先在自选股页面创建标签</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => {
              const isSelected = selectedTagIds.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  className={`px-3 py-1.5 rounded-full text-sm transition-all ${
                    isSelected
                      ? 'bg-cyan text-base'
                      : 'bg-surface text-secondary-text hover:bg-cyan/20'
                  }`}
                  onClick={() => onToggleTag(tag.id)}
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        )}

        <div className="flex gap-3 pt-4">
          <button
            type="button"
            className="btn-secondary flex-1"
            onClick={onClose}
            disabled={saving}
          >
            取消
          </button>
          <button
            type="button"
            className="btn-primary flex-1"
            disabled={saving}
            onClick={onSave}
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </Drawer>
  );
};
