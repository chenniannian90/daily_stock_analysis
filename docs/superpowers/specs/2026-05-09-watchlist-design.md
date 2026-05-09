# 自选股功能设计文档

> 创建日期: 2026-05-09

## 概述

自选股功能允许用户手动添加关注的股票，支持标签和分组两种分类维度，并在交易日每天自动分析两次（11:30、19:00），用户可查看单股历史分析记录。

## 需求确认

| 需求项 | 确认结果 |
|--------|----------|
| 股票来源 | 手动添加 |
| 标签 vs 分组 | 两个独立维度，一只股票可有多个标签 |
| 定时分析 | 全量分析，每天两次（11:30、19:00） |
| 历史查询 | 单股详情页，查看历史分析曲线和记录 |

## 数据模型

### 表结构

#### WatchlistStock（自选股）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| code | String(10) | 股票代码，唯一约束 |
| name | String(50) | 股票名称 |
| last_analysis_at | DateTime | 最后分析时间 |
| created_at | DateTime | 创建时间 |

#### WatchlistTag（标签）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(32) | 标签名称，唯一约束 |
| color | String(16) | 颜色值（如 #00ff88） |
| created_at | DateTime | 创建时间 |

#### WatchlistStockTag（股票-标签关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| stock_id | Integer | 外键，关联 WatchlistStock |
| tag_id | Integer | 外键，关联 WatchlistTag |

唯一约束：(stock_id, tag_id)

#### WatchlistGroup（分组）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String(32) | 分组名称，唯一约束 |
| sort_order | Integer | 排序序号 |
| created_at | DateTime | 创建时间 |

#### WatchlistStockGroup（股票-分组关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| stock_id | Integer | 外键，关联 WatchlistStock |
| group_id | Integer | 外键，关联 WatchlistGroup |

唯一约束：stock_id（一只股票只能属于一个分组）

### ER 图

```
┌─────────────────────┐     ┌─────────────────────────┐
│   WatchlistStock    │────<│   WatchlistStockTag     │
│  (自选股)            │     │  (股票-标签关联)         │
│  - id               │     │  - stock_id             │
│  - code             │     │  - tag_id               │
│  - name             │     └─────────────────────────┘
│  - last_analysis_at │               │
│  - created_at       │               │
└─────────────────────┘               ▼
          │               ┌─────────────────────────┐
          │               │   WatchlistTag          │
          │               │  (标签)                  │
          │               │  - id                   │
          │               │  - name                 │
          │               │  - color                │
          │               │  - created_at           │
          │               └─────────────────────────┘
          │
          ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   WatchlistStockGroup   │     │   WatchlistGroup        │
│  (股票-分组关联)         │>────│  (分组)                  │
│  - stock_id             │     │  - id                   │
│  - group_id             │     │  - name                 │
└─────────────────────────┘     │  - sort_order           │
                                │  - created_at           │
                                └─────────────────────────┘
```

### 特殊规则

1. 「全部」分组是虚拟分组，不存数据库，由前端生成
2. 删除股票时，级联删除 WatchlistStockTag 和 WatchlistStockGroup 记录
3. 删除标签时，级联删除 WatchlistStockTag 记录
4. 删除分组时，将该分组下的股票移出分组（不删除股票）

## API 设计

### 自选股接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/watchlist/stocks` | 获取自选股列表 |
| POST | `/api/v1/watchlist/stocks` | 添加自选股 |
| DELETE | `/api/v1/watchlist/stocks/{code}` | 删除自选股 |
| GET | `/api/v1/watchlist/stocks/{code}/history` | 获取单股历史分析记录 |

### 标签接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/watchlist/tags` | 获取所有标签 |
| POST | `/api/v1/watchlist/tags` | 创建标签 |
| PUT | `/api/v1/watchlist/tags/{id}` | 更新标签 |
| DELETE | `/api/v1/watchlist/tags/{id}` | 删除标签 |
| POST | `/api/v1/watchlist/stocks/{code}/tags` | 给股票设置标签 |
| DELETE | `/api/v1/watchlist/stocks/{code}/tags/{tagId}` | 移除股票标签 |

### 分组接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/watchlist/groups` | 获取所有分组（含「全部」虚拟分组） |
| POST | `/api/v1/watchlist/groups` | 创建分组 |
| PUT | `/api/v1/watchlist/groups/{id}` | 更新分组 |
| DELETE | `/api/v1/watchlist/groups/{id}` | 删除分组 |
| PUT | `/api/v1/watchlist/stocks/{code}/group` | 设置股票所属分组 |

### 请求/响应示例

#### 添加自选股

```http
POST /api/v1/watchlist/stocks
Content-Type: application/json

{
  "code": "600519",
  "name": "贵州茅台"
}
```

```json
// Response 200
{
  "code": "600519",
  "name": "贵州茅台",
  "createdAt": "2026-05-09T22:30:00"
}
```

#### 获取自选股列表

```http
GET /api/v1/watchlist/stocks?groupId=1&tagId=2
```

```json
// Response 200
{
  "items": [
    {
      "code": "600519",
      "name": "贵州茅台",
      "tags": [
        {"id": 1, "name": "龙头", "color": "#00ff88"}
      ],
      "group": {"id": 1, "name": "核心持仓"},
      "lastAnalysisAt": "2026-05-09T19:00:00",
      "lastPrediction": "震荡上行",
      "lastAdvice": "持有",
      "createdAt": "2026-05-01T10:00:00"
    }
  ],
  "total": 10
}
```

#### 获取单股历史分析记录

```http
GET /api/v1/watchlist/stocks/600519/history?page=1&limit=20
```

```json
// Response 200
{
  "items": [
    {
      "id": 123,
      "analysisDate": "2026-05-09",
      "analysisTime": "19:00",
      "trendPrediction": "震荡上行",
      "operationAdvice": "持有",
      "sentimentScore": 65,
      "analysisSummary": "技术面震荡上行，建议持有...",
      "backtestOutcome": "win",
      "directionCorrect": true
    }
  ],
  "total": 50,
  "accuracyStats": {
    "directionAccuracy": 72.5,
    "winCount": 29,
    "lossCount": 11,
    "neutralCount": 10
  }
}
```

## 前端设计

### 路由

| 路径 | 页面 |
|------|------|
| `/watchlist` | 自选股列表页 |
| `/watchlist/:code` | 单股详情页 |

### 自选股列表页

#### 布局

```
┌─────────────────────────────────────────────────────────┐
│  自选股                              [+ 添加] [管理标签]  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 全部(20) │ │ 核心持仓 │ │ 观察股   │ │ + 新建   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
├─────────────────────────────────────────────────────────┤
│  筛选: [全部标签 ▼] [搜索股票代码/名称...]              │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐ │
│  │ 600519 贵州茅台                    上次分析: 今天  │ │
│  │ [龙头] [消费]                          19:00      │ │
│  │ 预测: 震荡上行  建议: 持有               → 详情   │ │
│  └───────────────────────────────────────────────────┘ │
│  ...                                                  │
└─────────────────────────────────────────────────────────┘
```

#### 交互

1. **添加股票**：弹窗输入代码，自动查询名称
2. **设置标签**：点击卡片标签区域，弹出标签选择器
3. **设置分组**：右键菜单移动到其他分组
4. **删除股票**：右键菜单或删除按钮
5. **进入详情**：点击卡片或「详情」按钮

### 单股详情页

#### 布局

```
┌─────────────────────────────────────────────────────────┐
│  ← 返回    600519 贵州茅台                              │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐ │
│  │                [分析准确率趋势图]                   │ │
│  └───────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  历史分析记录                                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 日期        预测      建议      结果     准确性   │ │
│  │ 05-09 19:00 震荡上行  持有      上涨      ✓      │ │
│  │ 05-09 11:30 震荡      观望      持平      -      │ │
│  │ 05-08 19:00 下跌      减仓      下跌      ✓      │ │
│  └───────────────────────────────────────────────────┘ │
│  [加载更多]                                            │
└─────────────────────────────────────────────────────────┘
```

#### 交互

1. **返回列表**：点击返回按钮
2. **加载更多**：滚动加载或分页按钮

## 定时任务设计

### 调度配置

| 时间 | 任务 | 说明 |
|------|------|------|
| 11:30 | 午盘分析 | 分析所有自选股 |
| 19:00 | 晚盘分析 | 分析所有自选股 |

### 配置项

```env
# 自选股定时分析
WATCHLIST_SCHEDULE_ENABLED=true
WATCHLIST_MORNING_TIME=11:30
WATCHLIST_EVENING_TIME=19:00
```

### 分析流程

```
定时触发
    ↓
检查是否交易日（跳过周末节假日）
    ↓
获取所有自选股
    ↓
遍历执行分析（顺序执行）
    ↓
写入 AnalysisHistory
    ↓
更新 WatchlistStock.last_analysis_at
```

### 注意事项

1. **交易日判断**：仅交易日执行
2. **并发控制**：顺序执行，避免 API 限流
3. **错误处理**：单只股票失败不影响其他股票
4. **日志记录**：记录开始/结束时间和统计

## 文件结构

### 后端新增文件

```
src/
├── storage.py                      # 新增 5 个 Model
├── repositories/
│   └── watchlist_repo.py           # 新增：自选股数据访问层
├── services/
│   └── watchlist_service.py        # 新增：自选股业务逻辑
api/v1/
├── endpoints/
│   └── watchlist.py                # 新增：自选股 API 端点
├── schemas/
│   └── watchlist.py                # 新增：请求/响应 Schema
```

### 前端新增文件

```
apps/dsa-web/src/
├── pages/
│   ├── WatchlistPage.tsx           # 新增：自选股列表页
│   └── WatchlistDetailPage.tsx     # 新增：单股详情页
├── api/
│   └── watchlist.ts                # 新增：自选股 API 调用
├── types/
│   └── watchlist.ts                # 新增：类型定义
```

## 实现优先级

1. **P0 - 核心功能**
   - 数据模型创建
   - 自选股 CRUD API
   - 自选股列表页
   - 单股详情页

2. **P1 - 分类功能**
   - 标签 CRUD API
   - 分组 CRUD API
   - 标签/分组关联操作

3. **P2 - 定时任务**
   - 调度配置
   - 批量分析逻辑
   - 交易日判断
