# tests/test_watchlist_repo.py
"""自选股数据访问层测试 - 新模型"""

import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.storage import (
    Base,
    WatchlistItem,
    WatchlistGroupNew,
    WatchlistSort,
    UserTag,
    StockUserTag,
)


@pytest.fixture
def db_session():
    """共享的数据库 session fixture"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestWatchlistItemModel:
    """测试 WatchlistItem 模型"""

    def test_watchlist_item_create(self, db_session):
        """测试创建条目"""
        item = WatchlistItem(
            user_id='default',
            watch_type='stock',
            group_id=1,
            ts_code='600519.SH',
            sort_num=0,
        )
        db_session.add(item)
        db_session.commit()

        result = db_session.query(WatchlistItem).filter_by(ts_code='600519.SH').first()
        assert result is not None
        assert result.ts_code == '600519.SH'
        assert result.group_id == 1

    def test_same_stock_multiple_groups(self, db_session):
        """测试同一股票可在多个分组"""
        item1 = WatchlistItem(user_id='default', group_id=1, ts_code='600519.SH')
        item2 = WatchlistItem(user_id='default', group_id=2, ts_code='600519.SH')
        db_session.add_all([item1, item2])
        db_session.commit()

        results = db_session.query(WatchlistItem).filter_by(ts_code='600519.SH').all()
        assert len(results) == 2

    def test_unique_constraint_same_group(self, db_session):
        """测试同一分组不能重复添加"""
        item1 = WatchlistItem(user_id='default', group_id=1, ts_code='600519.SH')
        item2 = WatchlistItem(user_id='default', group_id=1, ts_code='600519.SH')
        db_session.add_all([item1, item2])

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_watchlist_item_to_dict(self, db_session):
        """测试 to_dict 方法"""
        item = WatchlistItem(
            user_id='default',
            watch_type='stock',
            group_id=1,
            ts_code='600519.SH',
            sort_num=5,
        )
        db_session.add(item)
        db_session.commit()

        result = db_session.query(WatchlistItem).first()
        d = result.to_dict()
        assert d['user_id'] == 'default'
        assert d['ts_code'] == '600519.SH'
        assert d['group_id'] == 1
        assert d['sort_num'] == 5
        assert 'created_at' in d


class TestWatchlistGroupNewModel:
    """测试分组模型"""

    def test_group_create(self, db_session):
        """测试创建分组"""
        group = WatchlistGroupNew(user_id='default', name='核心持仓')
        db_session.add(group)
        db_session.commit()

        result = db_session.query(WatchlistGroupNew).filter_by(name='核心持仓').first()
        assert result is not None
        assert result.name == '核心持仓'

    def test_unique_group_name(self, db_session):
        """测试分组名唯一"""
        g1 = WatchlistGroupNew(user_id='default', name='核心持仓')
        g2 = WatchlistGroupNew(user_id='default', name='核心持仓')
        db_session.add_all([g1, g2])

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_different_user_same_group_name(self, db_session):
        """测试不同用户可以有同名分组"""
        g1 = WatchlistGroupNew(user_id='user1', name='核心持仓')
        g2 = WatchlistGroupNew(user_id='user2', name='核心持仓')
        db_session.add_all([g1, g2])
        db_session.commit()

        results = db_session.query(WatchlistGroupNew).filter_by(name='核心持仓').all()
        assert len(results) == 2

    def test_group_to_dict(self, db_session):
        """测试 to_dict 方法"""
        group = WatchlistGroupNew(user_id='default', name='核心持仓')
        db_session.add(group)
        db_session.commit()

        result = db_session.query(WatchlistGroupNew).first()
        d = result.to_dict()
        assert d['user_id'] == 'default'
        assert d['name'] == '核心持仓'
        assert 'created_at' in d


class TestWatchlistSortModel:
    """测试排序模型"""

    def test_sort_create(self, db_session):
        """测试创建排序记录"""
        sort = WatchlistSort(
            user_id='default',
            sort_type='group_order',
            sort_content=json.dumps([1, 2, 3]),
        )
        db_session.add(sort)
        db_session.commit()

        result = db_session.query(WatchlistSort).filter_by(
            user_id='default', sort_type='group_order'
        ).first()
        assert result is not None
        data = json.loads(result.sort_content)
        assert data == [1, 2, 3]

    def test_unique_sort_type_per_user(self, db_session):
        """测试每个用户的每种排序类型只能有一条记录"""
        sort1 = WatchlistSort(user_id='default', sort_type='group_order', sort_content='[]')
        sort2 = WatchlistSort(user_id='default', sort_type='group_order', sort_content='[1]')
        db_session.add_all([sort1, sort2])

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_different_sort_types(self, db_session):
        """测试同一用户可以有不同类型的排序记录"""
        sort1 = WatchlistSort(user_id='default', sort_type='group_order', sort_content='[1, 2]')
        sort2 = WatchlistSort(user_id='default', sort_type='item_order', sort_content='[3, 4]')
        db_session.add_all([sort1, sort2])
        db_session.commit()

        results = db_session.query(WatchlistSort).filter_by(user_id='default').all()
        assert len(results) == 2

    def test_sort_to_dict(self, db_session):
        """测试 to_dict 方法"""
        sort = WatchlistSort(
            user_id='default',
            sort_type='group_order',
            sort_content='[1, 2, 3]',
        )
        db_session.add(sort)
        db_session.commit()

        result = db_session.query(WatchlistSort).first()
        d = result.to_dict()
        assert d['user_id'] == 'default'
        assert d['sort_type'] == 'group_order'
        assert d['sort_content'] == '[1, 2, 3]'


class TestUserTagModels:
    """测试用户标签模型"""

    def test_user_tag_create(self, db_session):
        """测试创建标签"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        result = db_session.query(UserTag).filter_by(name='龙头').first()
        assert result is not None

    def test_unique_tag_name_per_user(self, db_session):
        """测试同一用户的标签名唯一"""
        tag1 = UserTag(user_id='default', name='龙头')
        tag2 = UserTag(user_id='default', name='龙头')
        db_session.add_all([tag1, tag2])

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_different_user_same_tag_name(self, db_session):
        """测试不同用户可以有同名标签"""
        tag1 = UserTag(user_id='user1', name='龙头')
        tag2 = UserTag(user_id='user2', name='龙头')
        db_session.add_all([tag1, tag2])
        db_session.commit()

        results = db_session.query(UserTag).filter_by(name='龙头').all()
        assert len(results) == 2

    def test_user_tag_to_dict(self, db_session):
        """测试 to_dict 方法"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        result = db_session.query(UserTag).first()
        d = result.to_dict()
        assert d['user_id'] == 'default'
        assert d['name'] == '龙头'
        assert 'created_at' in d


class TestStockUserTagModel:
    """测试股票标签关联模型"""

    def test_stock_user_tag_association(self, db_session):
        """测试股票标签关联"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        assoc = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag.id)
        db_session.add(assoc)
        db_session.commit()

        result = db_session.query(StockUserTag).filter_by(ts_code='600519.SH').first()
        assert result is not None
        assert result.tag_id == tag.id

    def test_stock_multiple_tags(self, db_session):
        """测试一只股票可以有多个标签"""
        tag1 = UserTag(user_id='default', name='龙头')
        tag2 = UserTag(user_id='default', name='白马')
        db_session.add_all([tag1, tag2])
        db_session.commit()

        assoc1 = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag1.id)
        assoc2 = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag2.id)
        db_session.add_all([assoc1, assoc2])
        db_session.commit()

        results = db_session.query(StockUserTag).filter_by(ts_code='600519.SH').all()
        assert len(results) == 2

    def test_tag_multiple_stocks(self, db_session):
        """测试一个标签可以关联多只股票"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        assoc1 = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag.id)
        assoc2 = StockUserTag(user_id='default', ts_code='000858.SZ', tag_id=tag.id)
        db_session.add_all([assoc1, assoc2])
        db_session.commit()

        results = db_session.query(StockUserTag).filter_by(tag_id=tag.id).all()
        assert len(results) == 2

    def test_unique_stock_tag_association(self, db_session):
        """测试同一股票不能重复关联同一标签"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        assoc1 = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag.id)
        assoc2 = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag.id)
        db_session.add_all([assoc1, assoc2])

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_stock_user_tag_to_dict(self, db_session):
        """测试 to_dict 方法"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        assoc = StockUserTag(user_id='default', ts_code='600519.SH', tag_id=tag.id)
        db_session.add(assoc)
        db_session.commit()

        result = db_session.query(StockUserTag).first()
        d = result.to_dict()
        assert d['user_id'] == 'default'
        assert d['ts_code'] == '600519.SH'
        assert d['tag_id'] == tag.id
