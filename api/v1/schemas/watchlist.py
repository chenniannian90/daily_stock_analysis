# -*- coding: utf-8 -*-
"""自选股 API Schema 定义"""

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def validate_stock_code(code: str) -> str:
    """验证股票代码格式"""
    code = code.strip().upper()
    # A股: 6位数字
    # 港股: HK + 5位数字
    # 美股: 1-5位大写字母
    if not re.match(r'^(\d{6}|HK\d{5}|[A-Z]{1,5})$', code):
        raise ValueError('股票代码格式无效，支持: 6位数字(A股)、HK+5位数字(港股)、1-5位字母(美股)')
    return code


def validate_hex_color(color: str) -> str:
    """验证颜色格式"""
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError('颜色格式无效，应为 #RRGGBB 格式')
    return color


# ========== 标签 ==========

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32, description="标签名称")
    color: str = Field(default="#6b7280", description="颜色")

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        return validate_hex_color(v)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=32)
    color: Optional[str] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_hex_color(v)


class TagItem(BaseModel):
    id: int
    name: str
    color: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 分组 ==========

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32, description="分组名称")
    sort_order: int = Field(default=0, description="排序")


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=32)
    sort_order: Optional[int] = None


class GroupItem(BaseModel):
    id: int
    name: str
    sort_order: int
    stock_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 自选股 ==========

class StockAdd(BaseModel):
    code: str = Field(..., min_length=1, max_length=10, description="股票代码")
    name: Optional[str] = Field(None, max_length=50, description="股票名称")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        return validate_stock_code(v)


class StockTagUpdate(BaseModel):
    tag_ids: List[int] = Field(..., description="标签ID列表")


class StockGroupUpdate(BaseModel):
    group_id: Optional[int] = Field(None, description="分组ID，null表示移出分组")


class StockListItem(BaseModel):
    code: str
    name: Optional[str] = None
    tags: List[TagItem] = []
    group: Optional[GroupItem] = None
    last_analysis_at: Optional[datetime] = None
    last_prediction: Optional[str] = None
    last_advice: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockListResponse(BaseModel):
    items: List[StockListItem]
    total: int
    page: int
    limit: int


# ========== 历史分析 ==========

class AnalysisHistoryItem(BaseModel):
    id: int
    analysis_date: Optional[str] = None
    analysis_time: Optional[str] = None
    trend_prediction: Optional[str] = None
    operation_advice: Optional[str] = None
    sentiment_score: Optional[int] = None
    analysis_summary: Optional[str] = None
    backtest_outcome: Optional[str] = None
    direction_correct: Optional[bool] = None

    class Config:
        from_attributes = True


class AccuracyStats(BaseModel):
    direction_accuracy: Optional[float] = None
    win_count: int = 0
    loss_count: int = 0
    neutral_count: int = 0


class StockHistoryResponse(BaseModel):
    items: List[AnalysisHistoryItem]
    total: int
    page: int
    limit: int
    accuracy_stats: Optional[AccuracyStats] = None


# ========== 通用响应 ==========

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
