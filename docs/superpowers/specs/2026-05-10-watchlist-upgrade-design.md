# 自选股功能升级设计文档

> 创建日期: 2026-05-10

## 概述

对齐 Go 版本 chan-go 的自选股功能实现，支持一股多分组、行情数据、搜索、排序等功能。

## 与 Go 版本对齐

| 功能 | 说明 |
|------|------|
| 一股多分组 | 同一只股票可加入多个分组 |
| 行情数据 | 返回 close/changePct/totalMv/turnoverRate |
| 搜索 | 搜索股票代码/名称 |
| 移动 | 股票移到其他分组 |
| 排序 | 分组排序 + 股票置顶/置底 |
| 标签 | 用户自定义标签 |

## 数据模型

### 表结构

#### watchlist_item（自选条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | VARCHAR(64) | 用户ID，默认 'default' |
| watch_type | VARCHAR(16) | 类型，默认 'stock' |
| group_id | INTEGER | 分组ID，0 表示未分组 |
| ts_code | VARCHAR(10) | 股票代码（如 600519.SH） |
| sort_num | INTEGER | 排序值，默认 0 |
| created_at | DATETIME | 创建时间 |

唯一约束：(user_id, group_id, ts_code)

**关键变化：** 同一只股票可在多个分组中存在多条记录。

#### watchlist_group（分组）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | VARCHAR(64) | 用户ID，默认 'default' |
| name | VARCHAR(32) | 分组名称 |
| created_at | DATETIME | 创建时间 |

唯一约束：(user_id, name)

#### watchlist_sort（排序存储）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | VARCHAR(64) | 用户ID |
| sort_type | VARCHAR(32) | 排序类型 |
| sort_content | TEXT | JSON 数组 |

唯一约束：(user_id, sort_type)

**sort_type 取值：**
- `group_order` - 分组排序
- `stock_tags:{ts_code}` - 股票标签

#### user_tag（用户标签）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | VARCHAR(64) | 用户ID |
| name | VARCHAR(32) | 标签名称 |
| created_at | DATETIME | 创建时间 |

唯一约束：(user_id, name)

#### stock_user_tag（股票-标签关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | VARCHAR(64) | 用户ID |
| ts_code | VARCHAR(10) | 股票代码 |
| tag_id | INTEGER | 标签ID |

唯一约束：(user_id, ts_code, tag_id)

### ER 图

```
┌─────────────────────┐
│   watchlist_item    │
│  - id               │
│  - user_id          │
│  - watch_type       │
│  - group_id ────────┼──────┐
│  - ts_code          │      │
│  - sort_num         │      │
└─────────────────────┘      │
                             ▼
                   ┌─────────────────────┐
                   │   watchlist_group   │
                   │  - id               │
                   │  - user_id          │
                   │  - name             │
                   └─────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│    stock_user_tag   │     │      user_tag       │
│  - user_id          │     │  - id               │
│  - ts_code          │     │  - user_id          │
│  - tag_id ──────────┼─────│  - name             │
└─────────────────────┘     └─────────────────────┘

┌─────────────────────┐
│   watchlist_sort    │
│  - user_id          │
│  - sort_type        │
│  - sort_content     │ (JSON)
└─────────────────────┘
```

## API 设计

### 分组接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/watchlist/group/list` | 获取分组列表 |
| POST | `/api/v1/watchlist/group/create` | 创建分组 |
| PUT | `/api/v1/watchlist/group/update` | 更新分组 |
| DELETE | `/api/v1/watchlist/group/delete?id=` | 删除分组 |
| PUT | `/api/v1/watchlist/group/sort` | 分组排序 |

### 条目接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/watchlist/item/list` | 获取条目列表 |
| POST | `/api/v1/watchlist/item/add` | 添加条目 |
| DELETE | `/api/v1/watchlist/item/remove` | 删除条目 |
| PUT | `/api/v1/watchlist/item/move` | 移动条目 |
| PUT | `/api/v1/watchlist/item/sort` | 条目排序 |
| GET | `/api/v1/watchlist/item/search` | 搜索股票 |

### 请求/响应示例

#### 获取分组列表

```http
GET /api/v1/watchlist/group/list
```

```json
{
  "groups": [
    {"id": 0, "name": "全部", "sortOrder": 0, "stockCount": 20, "isDefault": true},
    {"id": 1, "name": "核心持仓", "sortOrder": 1, "stockCount": 5},
    {"id": 2, "name": "观察股", "sortOrder": 2, "stockCount": 8}
  ]
}
```

#### 获取条目列表

```http
GET /api/v1/watchlist/item/list?groupId=0&size=20&offset=0
```

```json
{
  "items": [
    {
      "tsCode": "600519.SH",
      "name": "贵州茅台",
      "industry": "白酒",
      "tags": [{"id": 1, "name": "龙头"}],
      "close": 1850.0,
      "changePct": 2.5,
      "totalMv": 2320000000000,
      "turnoverRate": 0.35
    }
  ],
  "total": 20
}
```

#### 添加条目

```http
POST /api/v1/watchlist/item/add
Content-Type: application/json

{
  "tsCode": "600519.SH",
  "groupIds": [1, 2]
}
```

```json
{"message": "success"}
```

#### 删除条目

```http
DELETE /api/v1/watchlist/item/remove?tsCode=600519.SH&groupId=1
```

```json
{"message": "success"}
```

#### 移动条目

```http
PUT /api/v1/watchlist/item/move
Content-Type: application/json

{
  "tsCode": "600519.SH",
  "fromGroupId": 1,
  "toGroupId": 2
}
```

```json
{"message": "success"}
```

#### 条目排序

```http
PUT /api/v1/watchlist/item/sort
Content-Type: application/json

{
  "groupId": 1,
  "items": [
    {"tsCode": "600519.SH", "action": "top"},
    {"tsCode": "000001.SZ", "action": "bottom"}
  ]
}
```

**action 取值：**
- `top` - 置顶，sort_num 设为当前时间戳
- `bottom` - 置底，sort_num 设为负时间戳

#### 搜索股票

```http
GET /api/v1/watchlist/item/search?keyword=茅台&limit=10
```

```json
{
  "items": [
    {"tsCode": "600519.SH", "name": "贵州茅台", "industry": "白酒"}
  ]
}
```

## 行情数据获取

使用现有 `DataFetcherManager` 获取实时行情：

```python
from data_provider.base import DataFetcherManager

def fetch_quotes(ts_codes: List[str]) -> Dict[str, dict]:
    """批量获取行情数据"""
    fetcher = DataFetcherManager()
    result = {}
    for code in ts_codes:
        try:
            quote = fetcher.get_realtime_quote(code)
            if quote:
                result[code] = {
                    "close": quote.close,
                    "changePct": (quote.close - quote.pre_close) / quote.pre_close * 100 if quote.pre_close else 0,
                    "totalMv": getattr(quote, 'total_mv', None),
                    "turnoverRate": getattr(quote, 'turnover_rate', None),
                }
        except Exception:
            pass
    return result
```

## 排序逻辑

### 分组排序

1. 从 `watchlist_sort` 表读取 `sort_type='group_order'` 的 `sort_content`（JSON 数组）
2. 解析为 `[group_id1, group_id2, ...]`
3. 按此顺序排列分组，未在列表中的分组追加到末尾

### 条目排序

1. 列表查询时按 `sort_num DESC, id ASC` 排序
2. 置顶：`sort_num = int(time.time())`（正数，越大越靠前）
3. 置底：`sort_num = -int(time.time())`（负数，越小越靠后）
4. 普通条目：`sort_num = 0`

## 文件结构

### 后端新增/修改文件

```
src/
├── storage.py                      # 新增 5 个 Model
├── repositories/
│   └── watchlist_repo.py           # 重写：适配新模型
├── services/
│   └── watchlist_service.py        # 重写：新增搜索/移动/排序逻辑
api/v1/
├── endpoints/
│   └── watchlist.py                # 重写：新 API 结构
├── schemas/
│   └── watchlist.py                # 重写：新 Schema
```

### 前端修改文件

```
apps/dsa-web/src/
├── pages/
│   └── WatchlistPage.tsx           # 修改：适配新 API
├── api/
│   └── watchlist.ts                # 修改：适配新 API
├── types/
│   └── watchlist.ts                # 修改：适配新类型
```

## 数据迁移

现有数据需要迁移：

1. `WatchlistStock` -> `watchlist_item` (group_id=0)
2. `WatchlistGroup` -> `watchlist_group`
3. `WatchlistTag` -> `user_tag`
4. `WatchlistStockTag` -> `stock_user_tag`

## 实现优先级

1. **P0 - 核心改造**
   - 数据模型重建
   - 条目 CRUD API（含行情数据）
   - 分组 CRUD API

2. **P1 - 增强功能**
   - 搜索 API
   - 移动 API
   - 排序 API

3. **P2 - 前端适配**
   - 前端 API 调用更新
   - UI 交互优化
