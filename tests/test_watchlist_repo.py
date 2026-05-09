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
from src.repositories.watchlist_repo import WatchlistRepository


@pytest.fixture
def db_session():
    """共享的数据库 session fixture"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestWatchlistModels:
    """测试自选股相关模型"""

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


class TestWatchlistRepository:
    """测试自选股数据访问层"""

    @pytest.fixture
    def repo(self, db_session):
        return WatchlistRepository(db_session)

    def test_add_stock(self, repo, db_session):
        """测试添加自选股"""
        stock = repo.add_stock(code="600519", name="贵州茅台")

        assert stock.code == "600519"
        assert stock.name == "贵州茅台"
        assert stock.id is not None

    def test_add_stock_duplicate_raises(self, repo):
        """测试重复添加同一股票"""
        repo.add_stock(code="600519", name="贵州茅台")

        with pytest.raises(ValueError, match="已存在"):
            repo.add_stock(code="600519", name="贵州茅台")

    def test_get_stock_by_code(self, repo):
        """测试按代码查询"""
        repo.add_stock(code="600519", name="贵州茅台")

        result = repo.get_stock_by_code("600519")
        assert result is not None
        assert result.name == "贵州茅台"

    def test_get_stock_by_code_not_found(self, repo):
        """测试查询不存在的股票"""
        result = repo.get_stock_by_code("999999")
        assert result is None

    def test_delete_stock(self, repo):
        """测试删除自选股"""
        repo.add_stock(code="600519", name="贵州茅台")

        repo.delete_stock("600519")

        result = repo.get_stock_by_code("600519")
        assert result is None

    def test_list_stocks(self, repo):
        """测试获取自选股列表"""
        repo.add_stock(code="600519", name="贵州茅台")
        repo.add_stock(code="000858", name="五粮液")

        result = repo.list_stocks()
        assert len(result) == 2
        codes = [s.code for s in result]
        assert "600519" in codes
        assert "000858" in codes
