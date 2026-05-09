# tests/test_watchlist_repo.py
"""自选股数据访问层测试"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.storage import (
    Base,
    WatchlistStock,
    WatchlistTag,
    WatchlistStockTag,
    WatchlistGroup,
    WatchlistStockGroup,
)


class TestWatchlistModels:
    """测试自选股相关模型"""

    @pytest.fixture
    def db_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    def test_watchlist_stock_model_exists(self, db_session):
        """测试 WatchlistStock 模型可正常创建"""
        stock = WatchlistStock(
            code="600519",
            name="贵州茅台",
        )
        db_session.add(stock)
        db_session.commit()

        result = db_session.query(WatchlistStock).filter_by(code="600519").first()
        assert result is not None
        assert result.code == "600519"
        assert result.name == "贵州茅台"
        assert result.id is not None

    def test_watchlist_tag_model_exists(self, db_session):
        """测试 WatchlistTag 模型可正常创建"""
        tag = WatchlistTag(name="龙头", color="#00ff88")
        db_session.add(tag)
        db_session.commit()

        result = db_session.query(WatchlistTag).filter_by(name="龙头").first()
        assert result is not None
        assert result.color == "#00ff88"

    def test_watchlist_group_model_exists(self, db_session):
        """测试 WatchlistGroup 模型可正常创建"""
        group = WatchlistGroup(name="核心持仓", sort_order=1)
        db_session.add(group)
        db_session.commit()

        result = db_session.query(WatchlistGroup).filter_by(name="核心持仓").first()
        assert result is not None
        assert result.sort_order == 1

    def test_watchlist_stock_tag_model_exists(self, db_session):
        """测试 WatchlistStockTag 模型可正常创建"""
        # 先创建股票和标签
        stock = WatchlistStock(code="600519", name="贵州茅台")
        tag = WatchlistTag(name="龙头", color="#00ff88")
        db_session.add_all([stock, tag])
        db_session.commit()

        # 创建关联
        assoc = WatchlistStockTag(stock_id=stock.id, tag_id=tag.id)
        db_session.add(assoc)
        db_session.commit()

        result = db_session.query(WatchlistStockTag).first()
        assert result is not None
        assert result.stock_id == stock.id
        assert result.tag_id == tag.id

    def test_watchlist_stock_group_model_exists(self, db_session):
        """测试 WatchlistStockGroup 模型可正常创建"""
        # 先创建股票和分组
        stock = WatchlistStock(code="000858", name="五粮液")
        group = WatchlistGroup(name="核心持仓", sort_order=1)
        db_session.add_all([stock, group])
        db_session.commit()

        # 创建关联
        assoc = WatchlistStockGroup(stock_id=stock.id, group_id=group.id)
        db_session.add(assoc)
        db_session.commit()

        result = db_session.query(WatchlistStockGroup).first()
        assert result is not None
        assert result.stock_id == stock.id
        assert result.group_id == group.id
