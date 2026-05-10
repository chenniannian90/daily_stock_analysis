# -*- coding: utf-8 -*-
"""自选股数据访问层 - 升级版"""

import json
import logging
import time
from typing import List, Optional, Dict, Any

from sqlalchemy import delete, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.storage import (
    WatchlistItem,
    WatchlistGroupNew,
    WatchlistSort,
    UserTag,
    StockUserTag,
)

logger = logging.getLogger(__name__)
DEFAULT_USER = 'default'


class WatchlistRepository:
    """自选股数据访问层"""

    def __init__(self, session: Session, user_id: str = DEFAULT_USER):
        self._session = session
        self._user_id = user_id

    # ========== 分组操作 ==========

    def create_group(self, name: str) -> WatchlistGroupNew:
        """创建分组"""
        try:
            group = WatchlistGroupNew(user_id=self._user_id, name=name)
            self._session.add(group)
            self._session.commit()
            logger.info(f"创建分组: {name}")
            return group
        except IntegrityError:
            self._session.rollback()
            raise ValueError(f"分组 '{name}' 已存在")

    def get_group_by_id(self, group_id: int) -> Optional[WatchlistGroupNew]:
        """按ID查询分组"""
        return self._session.execute(
            select(WatchlistGroupNew).where(
                WatchlistGroupNew.id == group_id,
                WatchlistGroupNew.user_id == self._user_id,
            )
        ).scalar_one_or_none()

    def list_groups(self) -> List[WatchlistGroupNew]:
        """获取所有分组"""
        return list(self._session.execute(
            select(WatchlistGroupNew).where(
                WatchlistGroupNew.user_id == self._user_id
            )
        ).scalars().all())

    def update_group(self, group_id: int, name: str) -> Optional[WatchlistGroupNew]:
        """更新分组名称"""
        group = self.get_group_by_id(group_id)
        if not group:
            return None
        try:
            group.name = name
            self._session.commit()
            return group
        except IntegrityError:
            self._session.rollback()
            raise ValueError(f"分组 '{name}' 已存在")

    def delete_group(self, group_id: int) -> bool:
        """删除分组（同时删除该分组下的条目）"""
        group = self.get_group_by_id(group_id)
        if not group:
            return False

        # 删除分组下的条目
        self._session.execute(
            delete(WatchlistItem).where(
                WatchlistItem.user_id == self._user_id,
                WatchlistItem.group_id == group_id,
            )
        )

        self._session.delete(group)
        self._session.commit()
        logger.info(f"删除分组: {group.name}")
        return True

    def get_group_order(self) -> List[int]:
        """获取分组排序"""
        sort = self._session.execute(
            select(WatchlistSort).where(
                WatchlistSort.user_id == self._user_id,
                WatchlistSort.sort_type == 'group_order',
            )
        ).scalar_one_or_none()

        if sort and sort.sort_content:
            return json.loads(sort.sort_content)
        return []

    def set_group_order(self, group_ids: List[int]) -> None:
        """设置分组排序"""
        sort = self._session.execute(
            select(WatchlistSort).where(
                WatchlistSort.user_id == self._user_id,
                WatchlistSort.sort_type == 'group_order',
            )
        ).scalar_one_or_none()

        content = json.dumps(group_ids)
        if sort:
            sort.sort_content = content
        else:
            sort = WatchlistSort(
                user_id=self._user_id,
                sort_type='group_order',
                sort_content=content,
            )
            self._session.add(sort)
        self._session.commit()

    def count_items_in_group(self, group_id: int) -> int:
        """统计分组内条目数量"""
        return self._session.execute(
            select(func.count(WatchlistItem.id)).where(
                WatchlistItem.user_id == self._user_id,
                WatchlistItem.group_id == group_id,
            )
        ).scalar() or 0

    # ========== 条目操作 ==========

    def add_item(self, ts_code: str, group_ids: List[int]) -> bool:
        """添加条目到多个分组"""
        if not group_ids:
            group_ids = [0]  # 默认未分组

        added = False
        for group_id in group_ids:
            try:
                item = WatchlistItem(
                    user_id=self._user_id,
                    watch_type='stock',
                    group_id=group_id,
                    ts_code=ts_code,
                    sort_num=0,
                )
                self._session.add(item)
                self._session.commit()
                added = True
                logger.info(f"添加条目: {ts_code} 到分组 {group_id}")
            except IntegrityError:
                self._session.rollback()

        return added

    def remove_item(self, ts_code: str, group_id: int) -> bool:
        """从指定分组删除条目"""
        result = self._session.execute(
            delete(WatchlistItem).where(
                WatchlistItem.user_id == self._user_id,
                WatchlistItem.ts_code == ts_code,
                WatchlistItem.group_id == group_id,
            )
        )
        self._session.commit()
        return result.rowcount > 0

    def list_items(self, group_id: int, size: int = 20, offset: int = 0) -> tuple:
        """获取条目列表"""
        if group_id == 0:
            # "全部"分组：聚合所有条目并去重
            all_items = self._session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.user_id == self._user_id,
                ).order_by(
                    WatchlistItem.sort_num.desc(),
                    WatchlistItem.id.asc(),
                )
            ).scalars().all()

            # 去重
            seen = set()
            unique_items = []
            for item in all_items:
                if item.ts_code not in seen:
                    seen.add(item.ts_code)
                    unique_items.append(item)

            total = len(unique_items)
            return unique_items[offset:offset + size], total
        else:
            # 指定分组
            items = self._session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.user_id == self._user_id,
                    WatchlistItem.group_id == group_id,
                ).order_by(
                    WatchlistItem.sort_num.desc(),
                    WatchlistItem.id.asc(),
                ).limit(size).offset(offset)
            ).scalars().all()

            total = self._session.execute(
                select(func.count(WatchlistItem.id)).where(
                    WatchlistItem.user_id == self._user_id,
                    WatchlistItem.group_id == group_id,
                )
            ).scalar() or 0

            return list(items), total

    def move_item(self, ts_code: str, from_group_id: int, to_group_id: int) -> bool:
        """移动条目到其他分组"""
        self.remove_item(ts_code, from_group_id)
        return self.add_item(ts_code, [to_group_id])

    def sort_items(self, group_id: int, items: List[Dict[str, Any]]) -> bool:
        """排序条目（置顶/置底）"""
        now = int(time.time())
        for entry in items:
            ts_code = entry.get('ts_code')
            action = entry.get('action')

            item = self._session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.user_id == self._user_id,
                    WatchlistItem.group_id == group_id,
                    WatchlistItem.ts_code == ts_code,
                )
            ).scalar_one_or_none()

            if item:
                if action == 'top':
                    item.sort_num = now
                elif action == 'bottom':
                    item.sort_num = -now

        self._session.commit()
        return True

    def get_all_ts_codes(self) -> List[str]:
        """获取所有条目的代码（去重）"""
        items = self._session.execute(
            select(WatchlistItem.ts_code).where(
                WatchlistItem.user_id == self._user_id,
            ).distinct()
        ).scalars().all()
        return list(items)

    # ========== 标签操作 ==========

    def create_tag(self, name: str) -> UserTag:
        """创建标签"""
        try:
            tag = UserTag(user_id=self._user_id, name=name)
            self._session.add(tag)
            self._session.commit()
            logger.info(f"创建标签: {name}")
            return tag
        except IntegrityError:
            self._session.rollback()
            raise ValueError(f"标签 '{name}' 已存在")

    def list_tags(self) -> List[UserTag]:
        """获取所有标签"""
        return list(self._session.execute(
            select(UserTag).where(UserTag.user_id == self._user_id)
        ).scalars().all())

    def delete_tag(self, tag_id: int) -> bool:
        """删除标签"""
        tag = self._session.execute(
            select(UserTag).where(
                UserTag.id == tag_id,
                UserTag.user_id == self._user_id,
            )
        ).scalar_one_or_none()

        if not tag:
            return False

        self._session.execute(
            delete(StockUserTag).where(StockUserTag.tag_id == tag_id)
        )

        self._session.delete(tag)
        self._session.commit()
        return True

    def add_tag_to_stock(self, ts_code: str, tag_id: int) -> bool:
        """给股票添加标签"""
        try:
            assoc = StockUserTag(
                user_id=self._user_id,
                ts_code=ts_code,
                tag_id=tag_id,
            )
            self._session.add(assoc)
            self._session.commit()
            return True
        except IntegrityError:
            self._session.rollback()
            return False

    def remove_tag_from_stock(self, ts_code: str, tag_id: int) -> bool:
        """移除股票标签"""
        result = self._session.execute(
            delete(StockUserTag).where(
                StockUserTag.user_id == self._user_id,
                StockUserTag.ts_code == ts_code,
                StockUserTag.tag_id == tag_id,
            )
        )
        self._session.commit()
        return result.rowcount > 0

    def get_stock_tags(self, ts_code: str) -> List[UserTag]:
        """获取股票的所有标签"""
        assocs = self._session.execute(
            select(StockUserTag).where(
                StockUserTag.user_id == self._user_id,
                StockUserTag.ts_code == ts_code,
            )
        ).scalars().all()

        tag_ids = [a.tag_id for a in assocs]
        if not tag_ids:
            return []

        return list(self._session.execute(
            select(UserTag).where(UserTag.id.in_(tag_ids))
        ).scalars().all())

    def get_all_stock_tags(self, ts_codes: List[str]) -> Dict[str, List[UserTag]]:
        """批量获取多只股票的标签"""
        if not ts_codes:
            return {}

        results = self._session.execute(
            select(StockUserTag.ts_code, UserTag)
            .join(UserTag, StockUserTag.tag_id == UserTag.id)
            .where(
                StockUserTag.user_id == self._user_id,
                StockUserTag.ts_code.in_(ts_codes),
            )
        ).all()

        result = {code: [] for code in ts_codes}
        for ts_code, tag in results:
            result[ts_code].append(tag)
        return result
