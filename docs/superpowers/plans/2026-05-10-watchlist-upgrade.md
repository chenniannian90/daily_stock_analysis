# 自选股功能升级实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 升级自选股功能，对齐 Go 版本实现，支持一股多分组、行情数据、搜索、移动、排序。

**Architecture:** 重构数据模型（5张新表），重写 Repository/Service/API 层，使用 DataFetcherManager 获取实时行情。

**Tech Stack:** Python 3.11, SQLAlchemy 2.0, FastAPI, Pydantic, pytest

---

## 文件结构

**新建文件：**
- `tests/test_watchlist_upgrade.py` - 升级后的测试

**修改文件：**
- `src/storage.py` - 替换现有 Watchlist 模型为新的 5 个模型
- `src/repositories/watchlist_repo.py` - 完全重写
- `src/services/watchlist_service.py` - 完全重写
- `api/v1/endpoints/watchlist.py` - 完全重写
- `api/v1/schemas/watchlist.py` - 完全重写

---

### Task 1: 定义新的 ORM 模型

**Files:**
- Modify: `src/storage.py:574-680` (替换现有 Watchlist 模型)

- [ ] **Step 1: 删除现有 Watchlist 模型**

删除 `src/storage.py` 中以下类定义：
- `WatchlistStock`
- `WatchlistTag`
- `WatchlistStockTag`
- `WatchlistGroup`
- `WatchlistStockGroup`

- [ ] **Step 2: 添加 WatchlistItem 模型**

```python
class WatchlistItem(Base):
    """自选股条目（一股可多分组）"""

    __tablename__ = 'watchlist_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, default='default', index=True)
    watch_type = Column(String(16), nullable=False, default='stock')
    group_id = Column(Integer, nullable=False, default=0, index=True)
    ts_code = Column(String(10), nullable=False, index=True)
    sort_num = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', 'ts_code', name='uix_user_group_tscode'),
        Index('ix_watchlist_user_type', 'user_id', 'watch_type'),
    )

    def __repr__(self):
        return f"<WatchlistItem(user={self.user_id}, code={self.ts_code}, group={self.group_id})>"
```

- [ ] **Step 3: 添加 WatchlistGroupNew 模型**

```python
class WatchlistGroupNew(Base):
    """自选股分组"""

    __tablename__ = 'watchlist_groups_new'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, default='default', index=True)
    name = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uix_user_group_name'),
    )

    def __repr__(self):
        return f"<WatchlistGroupNew(user={self.user_id}, name={self.name})>"
```

- [ ] **Step 4: 添加 WatchlistSort 模型**

```python
class WatchlistSort(Base):
    """排序存储"""

    __tablename__ = 'watchlist_sorts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    sort_type = Column(String(32), nullable=False)
    sort_content = Column(Text)  # JSON 数组

    __table_args__ = (
        UniqueConstraint('user_id', 'sort_type', name='uix_user_sort_type'),
    )

    def __repr__(self):
        return f"<WatchlistSort(user={self.user_id}, type={self.sort_type})>"
```

- [ ] **Step 5: 添加 UserTag 模型**

```python
class UserTag(Base):
    """用户标签"""

    __tablename__ = 'user_tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, default='default', index=True)
    name = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uix_user_tag_name'),
    )

    def __repr__(self):
        return f"<UserTag(user={self.user_id}, name={self.name})>"
```

- [ ] **Step 6: 添加 StockUserTag 模型**

```python
class StockUserTag(Base):
    """股票-标签关联"""

    __tablename__ = 'stock_user_tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    ts_code = Column(String(10), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey('user_tags.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'ts_code', 'tag_id', name='uix_user_code_tag'),
    )

    def __repr__(self):
        return f"<StockUserTag(user={self.user_id}, code={self.ts_code}, tag={self.tag_id})>"
```

- [ ] **Step 7: 运行语法检查**

```bash
python3 -m py_compile src/storage.py
```

Expected: 无输出表示成功

- [ ] **Step 8: Commit**

```bash
git add src/storage.py
git commit -m "feat(watchlist): replace ORM models with new structure for multi-group support"
```

---

### Task 2: 编写新模型的测试

**Files:**
- Modify: `tests/test_watchlist_repo.py`

- [ ] **Step 1: 更新测试文件 imports**

```python
# tests/test_watchlist_repo.py
"""自选股数据访问层测试 - 升级版"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.storage import (
    Base,
    WatchlistItem,
    WatchlistGroupNew,
    WatchlistSort,
    UserTag,
    StockUserTag,
)
```

- [ ] **Step 2: 添加 WatchlistItem 模型测试**

```python
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
        from sqlalchemy.exc import IntegrityError

        item1 = WatchlistItem(user_id='default', group_id=1, ts_code='600519.SH')
        item2 = WatchlistItem(user_id='default', group_id=1, ts_code='600519.SH')
        db_session.add_all([item1, item2])
        
        with pytest.raises(IntegrityError):
            db_session.commit()
```

- [ ] **Step 3: 添加 WatchlistGroupNew 模型测试**

```python
class TestWatchlistGroupModel:
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
        from sqlalchemy.exc import IntegrityError

        g1 = WatchlistGroupNew(user_id='default', name='核心持仓')
        g2 = WatchlistGroupNew(user_id='default', name='核心持仓')
        db_session.add_all([g1, g2])

        with pytest.raises(IntegrityError):
            db_session.commit()
```

- [ ] **Step 4: 添加 WatchlistSort 模型测试**

```python
class TestWatchlistSortModel:
    """测试排序模型"""

    def test_sort_create(self, db_session):
        """测试创建排序记录"""
        import json
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
```

- [ ] **Step 5: 添加 UserTag 和 StockUserTag 测试**

```python
class TestUserTagModels:
    """测试用户标签模型"""

    def test_user_tag_create(self, db_session):
        """测试创建标签"""
        tag = UserTag(user_id='default', name='龙头')
        db_session.add(tag)
        db_session.commit()

        result = db_session.query(UserTag).filter_by(name='龙头').first()
        assert result is not None

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
```

- [ ] **Step 6: 运行测试**

```bash
python3 -m pytest tests/test_watchlist_repo.py -v
```

Expected: 所有测试通过

- [ ] **Step 7: Commit**

```bash
git add tests/test_watchlist_repo.py
git commit -m "test(watchlist): add tests for new ORM models"
```

---

### Task 3: 重写 Repository 层

**Files:**
- Modify: `src/repositories/watchlist_repo.py`

- [ ] **Step 1: 重写 imports 和类定义**

```python
# -*- coding: utf-8 -*-
"""自选股数据访问层 - 升级版"""

import json
import logging
import time
from typing import List, Optional, Dict, Any

from sqlalchemy import delete, select, func, or_
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
```

- [ ] **Step 2: 实现 Group 相关方法**

```python
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
        group.name = name
        self._session.commit()
        return group

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
```

- [ ] **Step 3: 实现 Item 相关方法**

```python
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
                # 已存在，跳过
        
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

    def list_items(self, group_id: int, size: int = 20, offset: int = 0) -> tuple[List[WatchlistItem], int]:
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
            condition = (
                WatchlistItem.user_id == self._user_id,
                WatchlistItem.group_id == group_id,
            )
            items = self._session.execute(
                select(WatchlistItem).where(*condition).order_by(
                    WatchlistItem.sort_num.desc(),
                    WatchlistItem.id.asc(),
                ).limit(size).offset(offset)
            ).scalars().all()
            
            total = self._session.execute(
                select(func.count(WatchlistItem.id)).where(*condition)
            ).scalar() or 0
            
            return list(items), total

    def move_item(self, ts_code: str, from_group_id: int, to_group_id: int) -> bool:
        """移动条目到其他分组"""
        # 从原分组删除
        self.remove_item(ts_code, from_group_id)
        # 添加到新分组
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
```

- [ ] **Step 4: 实现 Tag 相关方法**

```python
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
        
        # 删除关联
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
        result = {}
        for code in ts_codes:
            result[code] = self.get_stock_tags(code)
        return result
```

- [ ] **Step 5: 运行语法检查**

```bash
python3 -m py_compile src/repositories/watchlist_repo.py
```

- [ ] **Step 6: Commit**

```bash
git add src/repositories/watchlist_repo.py
git commit -m "feat(watchlist): rewrite repository layer with multi-group support"
```

---

### Task 4: 重写 Schema 定义

**Files:**
- Modify: `api/v1/schemas/watchlist.py`

- [ ] **Step 1: 完全重写 Schema 文件**

```python
# -*- coding: utf-8 -*-
"""自选股 API Schema 定义 - 升级版"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ========== 通用响应 ==========

class MessageResp(BaseModel):
    """通用消息响应"""
    message: str


# ========== 分组 ==========

class GroupCreate(BaseModel):
    """创建分组"""
    name: str = Field(..., min_length=1, max_length=32)


class GroupUpdate(BaseModel):
    """更新分组"""
    id: int
    name: str = Field(..., min_length=1, max_length=32)


class GroupSort(BaseModel):
    """分组排序"""
    items: List[int]  # group_id 列表，顺序即排序


class GroupInfo(BaseModel):
    """分组信息"""
    id: int
    name: str
    sortOrder: int = 0
    stockCount: int = 0
    isDefault: bool = False


class GroupListResp(BaseModel):
    """分组列表响应"""
    groups: List[GroupInfo]


# ========== 条目 ==========

class ItemAdd(BaseModel):
    """添加条目"""
    tsCode: str = Field(..., min_length=1, max_length=12)
    groupIds: List[int] = Field(default=[0])


class ItemRemove(BaseModel):
    """删除条目参数"""
    tsCode: str
    groupId: int = 0


class ItemMove(BaseModel):
    """移动条目"""
    tsCode: str
    fromGroupId: int
    toGroupId: int


class ItemSortEntry(BaseModel):
    """排序项"""
    tsCode: str
    action: str  # 'top' or 'bottom'


class ItemSort(BaseModel):
    """条目排序"""
    groupId: int
    items: List[ItemSortEntry]


class ItemListParam(BaseModel):
    """列表参数"""
    groupId: int = 0
    size: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class TagInfo(BaseModel):
    """标签信息"""
    id: int
    name: str


class ItemInfo(BaseModel):
    """条目信息"""
    tsCode: str
    name: str = ""
    industry: Optional[str] = None
    tags: List[TagInfo] = []
    close: Optional[float] = None
    changePct: Optional[float] = None
    totalMv: Optional[float] = None
    turnoverRate: Optional[float] = None


class ItemListResp(BaseModel):
    """条目列表响应"""
    items: List[ItemInfo]
    total: int


# ========== 搜索 ==========

class ItemSearchParam(BaseModel):
    """搜索参数"""
    keyword: str = Field(..., min_length=1, max_length=20)
    limit: int = Field(default=10, ge=1, le=50)


class ItemSearchInfo(BaseModel):
    """搜索结果项"""
    tsCode: str
    name: str
    industry: Optional[str] = None


class ItemSearchResp(BaseModel):
    """搜索响应"""
    items: List[ItemSearchInfo]


# ========== 标签 ==========

class TagCreate(BaseModel):
    """创建标签"""
    name: str = Field(..., min_length=1, max_length=32)


class StockTagSet(BaseModel):
    """设置股票标签"""
    tsCode: str
    tagIds: List[int]
```

- [ ] **Step 2: 运行语法检查**

```bash
python3 -m py_compile api/v1/schemas/watchlist.py
```

- [ ] **Step 3: Commit**

```bash
git add api/v1/schemas/watchlist.py
git commit -m "feat(watchlist): rewrite schemas for new API structure"
```

---

### Task 5: 重写 Service 层

**Files:**
- Modify: `src/services/watchlist_service.py`

- [ ] **Step 1: 重写 Service 文件**

```python
# -*- coding: utf-8 -*-
"""自选股业务逻辑 - 升级版"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from data_provider.base import DataFetcherManager
from src.repositories.watchlist_repo import WatchlistRepository
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)


class WatchlistService:
    """自选股业务逻辑"""

    def __init__(self, session: Session, user_id: str = 'default'):
        self.repo = WatchlistRepository(session, user_id)

    def list_groups(self) -> Dict[str, Any]:
        """获取分组列表"""
        groups = self.repo.list_groups()
        order = self.repo.get_group_order()
        order_map = {gid: i for i, gid in enumerate(order)}
        
        # 构建"全部"虚拟分组
        all_codes = self.repo.get_all_ts_codes()
        total_count = len(all_codes)
        
        infos = [{
            'id': 0,
            'name': '全部',
            'sortOrder': 0,
            'stockCount': total_count,
            'isDefault': True,
        }]
        
        for g in groups:
            count = self.repo.count_items_in_group(g.id)
            infos.append({
                'id': g.id,
                'name': g.name,
                'sortOrder': order_map.get(g.id, 999),
                'stockCount': count,
            })
        
        # 按 sortOrder 排序（"全部"始终第一）
        infos[1:] = sorted(infos[1:], key=lambda x: x['sortOrder'])
        
        return {'groups': infos}

    def create_group(self, name: str) -> Dict[str, Any]:
        """创建分组"""
        group = self.repo.create_group(name)
        return {'id': group.id, 'name': group.name}

    def update_group(self, group_id: int, name: str) -> Optional[Dict[str, Any]]:
        """更新分组"""
        group = self.repo.update_group(group_id, name)
        if group:
            return {'id': group.id, 'name': group.name}
        return None

    def delete_group(self, group_id: int) -> bool:
        """删除分组"""
        return self.repo.delete_group(group_id)

    def sort_groups(self, group_ids: List[int]) -> bool:
        """分组排序"""
        self.repo.set_group_order(group_ids)
        return True

    def list_items(self, group_id: int, size: int = 20, offset: int = 0) -> Dict[str, Any]:
        """获取条目列表（含行情数据）"""
        items, total = self.repo.list_items(group_id, size, offset)
        
        if not items:
            return {'items': [], 'total': 0}
        
        # 获取所有代码
        ts_codes = [item.ts_code for item in items]
        
        # 批量获取名称和行情
        name_map = self._fetch_stock_names(ts_codes)
        quote_map = self._fetch_quotes(ts_codes)
        tag_map = self.repo.get_all_stock_tags(ts_codes)
        
        # 构建返回数据
        result_items = []
        for item in items:
            info = {
                'tsCode': item.ts_code,
                'name': name_map.get(item.ts_code, item.ts_code),
                'tags': [{'id': t.id, 'name': t.name} for t in tag_map.get(item.ts_code, [])],
            }
            
            # 添加行情数据
            if item.ts_code in quote_map:
                quote = quote_map[item.ts_code]
                info['close'] = quote.get('close')
                info['changePct'] = quote.get('changePct')
                info['totalMv'] = quote.get('totalMv')
                info['turnoverRate'] = quote.get('turnoverRate')
            
            result_items.append(info)
        
        return {'items': result_items, 'total': total}

    def add_item(self, ts_code: str, group_ids: List[int]) -> bool:
        """添加条目"""
        return self.repo.add_item(ts_code, group_ids)

    def remove_item(self, ts_code: str, group_id: int) -> bool:
        """删除条目"""
        return self.repo.remove_item(ts_code, group_id)

    def move_item(self, ts_code: str, from_group_id: int, to_group_id: int) -> bool:
        """移动条目"""
        return self.repo.move_item(ts_code, from_group_id, to_group_id)

    def sort_items(self, group_id: int, items: List[Dict[str, Any]]) -> bool:
        """条目排序"""
        return self.repo.sort_items(group_id, items)

    def search_stocks(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索股票"""
        try:
            fetcher = DataFetcherManager()
            # 使用现有搜索功能
            results = fetcher.search_stock(keyword, limit)
            return results
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []

    def _fetch_stock_names(self, ts_codes: List[str]) -> Dict[str, str]:
        """批量获取股票名称"""
        result = {}
        try:
            fetcher = DataFetcherManager()
            for code in ts_codes:
                try:
                    name = fetcher.get_stock_name(code, allow_realtime=False)
                    if name:
                        result[code] = name
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"获取股票名称失败: {e}")
        return result

    def _fetch_quotes(self, ts_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取行情数据"""
        result = {}
        try:
            fetcher = DataFetcherManager()
            for code in ts_codes:
                try:
                    quote = fetcher.get_realtime_quote(code)
                    if quote:
                        result[code] = {
                            'close': quote.close,
                            'changePct': (quote.close - quote.pre_close) / quote.pre_close * 100 if quote.pre_close else 0,
                            'totalMv': getattr(quote, 'total_mv', None),
                            'turnoverRate': getattr(quote, 'turnover_rate', None),
                        }
                except Exception as e:
                    logger.debug(f"获取 {code} 行情失败: {e}")
        except Exception as e:
            logger.warning(f"获取行情数据失败: {e}")
        return result
```

- [ ] **Step 2: 运行语法检查**

```bash
python3 -m py_compile src/services/watchlist_service.py
```

- [ ] **Step 3: Commit**

```bash
git add src/services/watchlist_service.py
git commit -m "feat(watchlist): rewrite service layer with quote data support"
```

---

### Task 6: 重写 API 端点

**Files:**
- Modify: `api/v1/endpoints/watchlist.py`

- [ ] **Step 1: 重写 API 端点文件**

```python
# -*- coding: utf-8 -*-
"""自选股 API 端点 - 升级版"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.v1.schemas.watchlist import (
    GroupCreate,
    GroupUpdate,
    GroupSort,
    GroupListResp,
    GroupInfo,
    ItemAdd,
    ItemRemove,
    ItemMove,
    ItemSort,
    ItemListParam,
    ItemListResp,
    ItemSearchParam,
    ItemSearchResp,
    ItemSearchInfo,
    MessageResp,
    TagCreate,
    StockTagSet,
)
from src.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])


# ========== 分组接口 ==========

@router.get("/group/list", response_model=GroupListResp, summary="获取分组列表")
def list_groups(db: Session = Depends(get_db)):
    """获取分组列表（含"全部"虚拟分组）"""
    service = WatchlistService(db)
    result = service.list_groups()
    return GroupListResp(groups=[GroupInfo(**g) for g in result['groups']])


@router.post("/group/create", response_model=GroupInfo, summary="创建分组")
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    """创建分组"""
    service = WatchlistService(db)
    try:
        result = service.create_group(data.name)
        return GroupInfo(id=result['id'], name=result['name'])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/group/update", response_model=GroupInfo, summary="更新分组")
def update_group(data: GroupUpdate, db: Session = Depends(get_db)):
    """更新分组名称"""
    service = WatchlistService(db)
    result = service.update_group(data.id, data.name)
    if not result:
        raise HTTPException(status_code=404, detail="分组不存在")
    return GroupInfo(id=result['id'], name=result['name'])


@router.delete("/group/delete", response_model=MessageResp, summary="删除分组")
def delete_group(id: int = Query(..., description="分组ID"), db: Session = Depends(get_db)):
    """删除分组"""
    service = WatchlistService(db)
    if not service.delete_group(id):
        raise HTTPException(status_code=404, detail="分组不存在")
    return MessageResp(message="success")


@router.put("/group/sort", response_model=MessageResp, summary="分组排序")
def sort_groups(data: GroupSort, db: Session = Depends(get_db)):
    """设置分组排序顺序"""
    service = WatchlistService(db)
    service.sort_groups(data.items)
    return MessageResp(message="success")


# ========== 条目接口 ==========

@router.get("/item/list", response_model=ItemListResp, summary="获取条目列表")
def list_items(
    groupId: int = Query(0, description="分组ID，0表示全部"),
    size: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """获取条目列表（含行情数据）"""
    service = WatchlistService(db)
    result = service.list_items(groupId, size, offset)
    from api.v1.schemas.watchlist import ItemInfo, TagInfo
    items = [ItemInfo(**item) for item in result['items']]
    return ItemListResp(items=items, total=result['total'])


@router.post("/item/add", response_model=MessageResp, summary="添加条目")
def add_item(data: ItemAdd, db: Session = Depends(get_db)):
    """添加条目到分组"""
    service = WatchlistService(db)
    service.add_item(data.tsCode, data.groupIds)
    return MessageResp(message="success")


@router.delete("/item/remove", response_model=MessageResp, summary="删除条目")
def remove_item(
    tsCode: str = Query(..., description="股票代码"),
    groupId: int = Query(0, description="分组ID"),
    db: Session = Depends(get_db),
):
    """从指定分组删除条目"""
    service = WatchlistService(db)
    if not service.remove_item(tsCode, groupId):
        raise HTTPException(status_code=404, detail="条目不存在")
    return MessageResp(message="success")


@router.put("/item/move", response_model=MessageResp, summary="移动条目")
def move_item(data: ItemMove, db: Session = Depends(get_db)):
    """移动条目到其他分组"""
    service = WatchlistService(db)
    service.move_item(data.tsCode, data.fromGroupId, data.toGroupId)
    return MessageResp(message="success")


@router.put("/item/sort", response_model=MessageResp, summary="条目排序")
def sort_items(data: ItemSort, db: Session = Depends(get_db)):
    """条目排序（置顶/置底）"""
    service = WatchlistService(db)
    items = [{'tsCode': item.tsCode, 'action': item.action} for item in data.items]
    service.sort_items(data.groupId, items)
    return MessageResp(message="success")


@router.get("/item/search", response_model=ItemSearchResp, summary="搜索股票")
def search_stocks(
    keyword: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """搜索股票代码/名称"""
    service = WatchlistService(db)
    results = service.search_stocks(keyword, limit)
    items = [ItemSearchInfo(**r) for r in results]
    return ItemSearchResp(items=items)
```

- [ ] **Step 2: 运行语法检查**

```bash
python3 -m py_compile api/v1/endpoints/watchlist.py
```

- [ ] **Step 3: Commit**

```bash
git add api/v1/endpoints/watchlist.py
git commit -m "feat(watchlist): rewrite API endpoints with new structure"
```

---

### Task 7: 运行完整测试

- [ ] **Step 1: 运行所有 watchlist 测试**

```bash
python3 -m pytest tests/test_watchlist_repo.py -v
```

Expected: 所有测试通过

- [ ] **Step 2: 运行语法检查所有修改文件**

```bash
python3 -m py_compile src/storage.py src/repositories/watchlist_repo.py src/services/watchlist_service.py api/v1/endpoints/watchlist.py api/v1/schemas/watchlist.py
```

- [ ] **Step 3: 运行 CI 门禁检查**

```bash
./scripts/ci_gate.sh
```

- [ ] **Step 4: 最终 Commit（如有遗漏）**

```bash
git add -A
git commit -m "feat(watchlist): complete upgrade with multi-group support"
```

---

### Task 8: 更新前端 API 调用

**Files:**
- Modify: `apps/dsa-web/src/api/watchlist.ts`
- Modify: `apps/dsa-web/src/types/watchlist.ts`
- Modify: `apps/dsa-web/src/pages/WatchlistPage.tsx`

- [ ] **Step 1: 更新类型定义**

```typescript
// apps/dsa-web/src/types/watchlist.ts

export interface GroupInfo {
  id: number;
  name: string;
  sortOrder: number;
  stockCount: number;
  isDefault?: boolean;
}

export interface ItemInfo {
  tsCode: string;
  name: string;
  industry?: string;
  tags: TagInfo[];
  close?: number;
  changePct?: number;
  totalMv?: number;
  turnoverRate?: number;
}

export interface TagInfo {
  id: number;
  name: string;
}
```

- [ ] **Step 2: 更新 API 调用**

```typescript
// apps/dsa-web/src/api/watchlist.ts

export const watchlistApi = {
  // 分组
  listGroups: () => request.get<GroupListResp>('/watchlist/group/list'),
  createGroup: (name: string) => request.post('/watchlist/group/create', { name }),
  updateGroup: (id: number, name: string) => request.put('/watchlist/group/update', { id, name }),
  deleteGroup: (id: number) => request.delete(`/watchlist/group/delete?id=${id}`),
  sortGroups: (items: number[]) => request.put('/watchlist/group/sort', { items }),

  // 条目
  listItems: (groupId: number, size = 20, offset = 0) =>
    request.get<ItemListResp>(`/watchlist/item/list?groupId=${groupId}&size=${size}&offset=${offset}`),
  addItem: (tsCode: string, groupIds: number[]) =>
    request.post('/watchlist/item/add', { tsCode, groupIds }),
  removeItem: (tsCode: string, groupId: number) =>
    request.delete(`/watchlist/item/remove?tsCode=${tsCode}&groupId=${groupId}`),
  moveItem: (tsCode: string, fromGroupId: number, toGroupId: number) =>
    request.put('/watchlist/item/move', { tsCode, fromGroupId, toGroupId }),
  sortItems: (groupId: number, items: { tsCode: string; action: string }[]) =>
    request.put('/watchlist/item/sort', { groupId, items }),
  searchStocks: (keyword: string, limit = 10) =>
    request.get<ItemSearchResp>(`/watchlist/item/search?keyword=${keyword}&limit=${limit}`),
};
```

- [ ] **Step 3: Commit**

```bash
git add apps/dsa-web/src/
git commit -m "feat(watchlist): update frontend API calls for new structure"
```

---

## 实现完成检查清单

- [ ] 新 ORM 模型定义完成
- [ ] 测试通过
- [ ] Repository 层重写完成
- [ ] Schema 定义重写完成
- [ ] Service 层重写完成
- [ ] API 端点重写完成
- [ ] 前端 API 更新完成
- [ ] CI 门禁通过
- [ ] 部署测试通过
