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
