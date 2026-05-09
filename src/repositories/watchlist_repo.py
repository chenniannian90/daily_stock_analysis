# -*- coding: utf-8 -*-
"""自选股数据访问层"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import delete, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.storage import (
    DatabaseManager,
    WatchlistStock,
    WatchlistTag,
    WatchlistStockTag,
    WatchlistGroup,
    WatchlistStockGroup,
)

logger = logging.getLogger(__name__)


class WatchlistRepository:
    """自选股数据访问层"""

    def __init__(self, session: Optional[Session] = None, db_manager: Optional[DatabaseManager] = None):
        if session:
            self._session = session
            self._owns_session = False
        elif db_manager:
            self._session = db_manager.get_session()
            self._owns_session = True
        else:
            self._session = DatabaseManager.get_instance().get_session()
            self._owns_session = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self._session:
            self._session.close()

    def add_stock(self, code: str, name: Optional[str] = None) -> WatchlistStock:
        """添加自选股"""
        try:
            stock = WatchlistStock(code=code, name=name)
            self._session.add(stock)
            self._session.commit()
            logger.info(f"添加自选股: {code} {name}")
            return stock
        except IntegrityError:
            self._session.rollback()
            raise ValueError(f"股票 {code} 已存在")

    def get_stock_by_code(self, code: str) -> Optional[WatchlistStock]:
        """按代码查询自选股"""
        return self._session.execute(
            select(WatchlistStock).where(WatchlistStock.code == code)
        ).scalar_one_or_none()

    def delete_stock(self, code: str) -> bool:
        """删除自选股（级联删除关联）"""
        stock = self.get_stock_by_code(code)
        if not stock:
            return False

        # 级联删除标签关联
        self._session.execute(
            delete(WatchlistStockTag).where(WatchlistStockTag.stock_id == stock.id)
        )
        # 级联删除分组关联
        self._session.execute(
            delete(WatchlistStockGroup).where(WatchlistStockGroup.stock_id == stock.id)
        )
        # 删除股票
        self._session.delete(stock)
        self._session.commit()
        logger.info(f"删除自选股: {code}")
        return True

    def list_stocks(
        self,
        group_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WatchlistStock]:
        """获取自选股列表"""
        query = select(WatchlistStock).order_by(WatchlistStock.created_at.desc())

        if group_id:
            subquery = select(WatchlistStockGroup.stock_id).where(
                WatchlistStockGroup.group_id == group_id
            )
            query = query.where(WatchlistStock.id.in_(subquery))

        if tag_id:
            subquery = select(WatchlistStockTag.stock_id).where(
                WatchlistStockTag.tag_id == tag_id
            )
            query = query.where(WatchlistStock.id.in_(subquery))

        query = query.limit(limit).offset(offset)
        return list(self._session.execute(query).scalars().all())

    def count_stocks(
        self,
        group_id: Optional[int] = None,
        tag_id: Optional[int] = None,
    ) -> int:
        """统计自选股数量"""
        query = select(func.count(WatchlistStock.id))

        if group_id:
            subquery = select(WatchlistStockGroup.stock_id).where(
                WatchlistStockGroup.group_id == group_id
            )
            query = query.where(WatchlistStock.id.in_(subquery))

        if tag_id:
            subquery = select(WatchlistStockTag.stock_id).where(
                WatchlistStockTag.tag_id == tag_id
            )
            query = query.where(WatchlistStock.id.in_(subquery))

        return self._session.execute(query).scalar() or 0

    def update_stock_last_analysis(self, code: str) -> None:
        """更新最后分析时间"""
        stock = self.get_stock_by_code(code)
        if stock:
            stock.last_analysis_at = datetime.now()
            self._session.commit()

    # ========== 标签操作 ==========

    def create_tag(self, name: str, color: str = "#6b7280") -> WatchlistTag:
        """创建标签"""
        try:
            tag = WatchlistTag(name=name, color=color)
            self._session.add(tag)
            self._session.commit()
            logger.info(f"创建标签: {name}")
            return tag
        except IntegrityError:
            self._session.rollback()
            raise ValueError(f"标签 '{name}' 已存在")

    def get_tag_by_id(self, tag_id: int) -> Optional[WatchlistTag]:
        """按ID查询标签"""
        return self._session.execute(
            select(WatchlistTag).where(WatchlistTag.id == tag_id)
        ).scalar_one_or_none()

    def list_tags(self) -> List[WatchlistTag]:
        """获取所有标签"""
        return list(self._session.execute(
            select(WatchlistTag).order_by(WatchlistTag.created_at)
        ).scalars().all())

    def update_tag(self, tag_id: int, name: Optional[str] = None, color: Optional[str] = None) -> Optional[WatchlistTag]:
        """更新标签"""
        tag = self.get_tag_by_id(tag_id)
        if not tag:
            return None
        if name:
            tag.name = name
        if color:
            tag.color = color
        self._session.commit()
        return tag

    def delete_tag(self, tag_id: int) -> bool:
        """删除标签（级联删除关联）"""
        tag = self.get_tag_by_id(tag_id)
        if not tag:
            return False
        self._session.execute(
            delete(WatchlistStockTag).where(WatchlistStockTag.tag_id == tag_id)
        )
        self._session.delete(tag)
        self._session.commit()
        logger.info(f"删除标签: {tag.name}")
        return True

    def add_tag_to_stock(self, code: str, tag_id: int) -> bool:
        """给股票添加标签"""
        stock = self.get_stock_by_code(code)
        if not stock:
            raise ValueError(f"股票 {code} 不存在")

        try:
            assoc = WatchlistStockTag(stock_id=stock.id, tag_id=tag_id)
            self._session.add(assoc)
            self._session.commit()
            return True
        except IntegrityError:
            self._session.rollback()
            return False  # 已关联

    def remove_tag_from_stock(self, code: str, tag_id: int) -> bool:
        """移除股票标签"""
        stock = self.get_stock_by_code(code)
        if not stock:
            return False

        result = self._session.execute(
            delete(WatchlistStockTag).where(
                WatchlistStockTag.stock_id == stock.id,
                WatchlistStockTag.tag_id == tag_id,
            )
        )
        self._session.commit()
        return result.rowcount > 0

    def get_stock_tags(self, code: str) -> List[WatchlistTag]:
        """获取股票的所有标签"""
        stock = self.get_stock_by_code(code)
        if not stock:
            return []

        return list(self._session.execute(
            select(WatchlistTag)
            .join(WatchlistStockTag, WatchlistTag.id == WatchlistStockTag.tag_id)
            .where(WatchlistStockTag.stock_id == stock.id)
        ).scalars().all())

    # ========== 分组操作 ==========

    def create_group(self, name: str, sort_order: int = 0) -> WatchlistGroup:
        """创建分组"""
        try:
            group = WatchlistGroup(name=name, sort_order=sort_order)
            self._session.add(group)
            self._session.commit()
            logger.info(f"创建分组: {name}")
            return group
        except IntegrityError:
            self._session.rollback()
            raise ValueError(f"分组 '{name}' 已存在")

    def get_group_by_id(self, group_id: int) -> Optional[WatchlistGroup]:
        """按ID查询分组"""
        return self._session.execute(
            select(WatchlistGroup).where(WatchlistGroup.id == group_id)
        ).scalar_one_or_none()

    def list_groups(self) -> List[WatchlistGroup]:
        """获取所有分组（按sort_order排序）"""
        return list(self._session.execute(
            select(WatchlistGroup).order_by(WatchlistGroup.sort_order)
        ).scalars().all())

    def update_group(self, group_id: int, name: Optional[str] = None, sort_order: Optional[int] = None) -> Optional[WatchlistGroup]:
        """更新分组"""
        group = self.get_group_by_id(group_id)
        if not group:
            return None
        if name:
            group.name = name
        if sort_order is not None:
            group.sort_order = sort_order
        self._session.commit()
        return group

    def delete_group(self, group_id: int) -> bool:
        """删除分组（股票移出分组，不删除股票）"""
        group = self.get_group_by_id(group_id)
        if not group:
            return False
        self._session.execute(
            delete(WatchlistStockGroup).where(WatchlistStockGroup.group_id == group_id)
        )
        self._session.delete(group)
        self._session.commit()
        logger.info(f"删除分组: {group.name}")
        return True

    def set_stock_group(self, code: str, group_id: int) -> bool:
        """设置股票所属分组"""
        stock = self.get_stock_by_code(code)
        if not stock:
            raise ValueError(f"股票 {code} 不存在")

        # 先移除旧分组
        self._session.execute(
            delete(WatchlistStockGroup).where(WatchlistStockGroup.stock_id == stock.id)
        )

        # 添加新分组
        assoc = WatchlistStockGroup(stock_id=stock.id, group_id=group_id)
        self._session.add(assoc)
        self._session.commit()
        return True

    def remove_stock_from_group(self, code: str) -> bool:
        """移出分组"""
        stock = self.get_stock_by_code(code)
        if not stock:
            return False

        result = self._session.execute(
            delete(WatchlistStockGroup).where(WatchlistStockGroup.stock_id == stock.id)
        )
        self._session.commit()
        return result.rowcount > 0

    def get_stock_group(self, code: str) -> Optional[WatchlistGroup]:
        """获取股票所属分组"""
        stock = self.get_stock_by_code(code)
        if not stock:
            return None

        return self._session.execute(
            select(WatchlistGroup)
            .join(WatchlistStockGroup, WatchlistGroup.id == WatchlistStockGroup.group_id)
            .where(WatchlistStockGroup.stock_id == stock.id)
        ).scalar_one_or_none()
