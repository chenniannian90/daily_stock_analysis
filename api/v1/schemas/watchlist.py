# -*- coding: utf-8 -*-
"""自选股 API Schema 定义"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ========== 通用响应 ==========

class MessageResp(BaseModel):
    """通用消息响应"""
    message: str


# ========== 分组 ==========

class GroupCreate(BaseModel):
    """创建分组"""
    name: str = Field(..., min_length=1, max_length=32, description="分组名称")


class GroupUpdate(BaseModel):
    """更新分组"""
    id: int = Field(..., description="分组ID")
    name: str = Field(..., min_length=1, max_length=32, description="分组名称")


class GroupSort(BaseModel):
    """分组排序"""
    items: List[int] = Field(..., description="分组ID列表，按顺序排列")


class GroupInfo(BaseModel):
    """分组信息"""
    id: int
    name: str
    sortOrder: int
    stockCount: int
    isDefault: bool

    class Config:
        from_attributes = True


class GroupListResp(BaseModel):
    """分组列表响应"""
    groups: List[GroupInfo]


# ========== 条目 ==========

class ItemAdd(BaseModel):
    """添加条目"""
    tsCode: str = Field(..., min_length=1, max_length=12, description="股票代码")
    groupIds: List[int] = Field(default=[0], description="分组ID列表，默认为默认分组")


class ItemRemove(BaseModel):
    """移除条目"""
    tsCode: str = Field(..., description="股票代码")
    groupId: int = Field(default=0, description="分组ID，默认为默认分组")


class ItemMove(BaseModel):
    """移动条目"""
    tsCode: str = Field(..., description="股票代码")
    fromGroupId: int = Field(..., description="源分组ID")
    toGroupId: int = Field(..., description="目标分组ID")


class ItemSortEntry(BaseModel):
    """条目排序项"""
    tsCode: str = Field(..., description="股票代码")
    action: Literal["top", "bottom"] = Field(..., description="排序动作：top-置顶，bottom-置底")


class ItemSort(BaseModel):
    """条目排序"""
    groupId: int = Field(..., description="分组ID")
    items: List[ItemSortEntry] = Field(..., description="排序项列表")


class ItemListParam(BaseModel):
    """条目列表查询参数"""
    groupId: int = Field(default=0, description="分组ID，默认为默认分组")
    size: int = Field(default=20, ge=1, le=100, description="每页数量，1-100")
    offset: int = Field(default=0, ge=0, description="偏移量")


class TagInfo(BaseModel):
    """标签信息"""
    id: int
    name: str
    color: str = "#00d4ff"

    class Config:
        from_attributes = True


class TagItem(BaseModel):
    """标签详情（含颜色和创建时间）"""
    id: int
    name: str
    color: str = "#00d4ff"
    createdAt: Optional[str] = None

    class Config:
        from_attributes = True


class ItemInfo(BaseModel):
    """条目信息"""
    tsCode: str
    name: str
    industry: Optional[str] = None
    tags: List[TagInfo] = []
    close: Optional[float] = None
    changePct: Optional[float] = None
    totalMv: Optional[float] = None
    turnoverRate: Optional[float] = None

    class Config:
        from_attributes = True


class ItemListResp(BaseModel):
    """条目列表响应"""
    items: List[ItemInfo]
    total: int


# ========== 搜索 ==========

class ItemSearchParam(BaseModel):
    """条目搜索参数"""
    keyword: str = Field(..., min_length=1, max_length=20, description="搜索关键词")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制，1-50")


class ItemSearchInfo(BaseModel):
    """条目搜索结果"""
    tsCode: str
    name: str
    industry: Optional[str] = None

    class Config:
        from_attributes = True


class ItemSearchResp(BaseModel):
    """条目搜索响应"""
    items: List[ItemSearchInfo]


# ========== 标签 ==========

class TagCreate(BaseModel):
    """创建标签"""
    name: str = Field(..., min_length=1, max_length=32, description="标签名称")
    color: Optional[str] = Field(default="#00d4ff", description="标签颜色")


class TagUpdate(BaseModel):
    """更新标签"""
    name: Optional[str] = Field(None, min_length=1, max_length=32, description="标签名称")
    color: Optional[str] = Field(None, description="标签颜色")


class StockTagSet(BaseModel):
    """设置股票标签"""
    tag_ids: List[int] = Field(..., description="标签ID列表")


# ========== 分析历史 ==========

class AnalysisHistoryItem(BaseModel):
    """分析历史条目"""
    id: int
    analysisDate: Optional[str] = None
    analysisTime: Optional[str] = None
    trendPrediction: Optional[str] = None
    operationAdvice: Optional[str] = None
    sentimentScore: Optional[int] = None
    analysisSummary: Optional[str] = None
    backtestOutcome: Optional[str] = None
    directionCorrect: Optional[bool] = None


class AccuracyStats(BaseModel):
    """预测准确率统计"""
    directionAccuracy: Optional[float] = None
    winCount: int = 0
    lossCount: int = 0
    neutralCount: int = 0


class StockHistoryResp(BaseModel):
    """股票分析历史响应"""
    items: List[AnalysisHistoryItem]
    total: int
    page: int
    limit: int
    accuracyStats: Optional[AccuracyStats] = None
