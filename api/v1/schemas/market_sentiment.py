# -*- coding: utf-8 -*-
"""市场情绪快照 Pydantic schemas。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SentimentSnapshotItem(BaseModel):
    """单条快照"""

    date: str = Field(..., description="日期 YYYY-MM-DD")
    time: str = Field(..., description="采集时间 HH:MM")
    up_count: int = Field(0, description="上涨家数")
    down_count: int = Field(0, description="下跌家数")
    flat_count: int = Field(0, description="平盘家数")
    limit_up_count: int = Field(0, description="涨停家数")
    limit_down_count: int = Field(0, description="跌停家数")
    total_volume: float = Field(0.0, description="总成交量(亿股)")
    total_amount: float = Field(0.0, description="总成交额(亿元)")
    up_median_pct: float = Field(0.0, description="上涨中位数(%)")
    down_median_pct: float = Field(0.0, description="下跌中位数(%)")
    up_avg_pct: float = Field(0.0, description="上涨均值(%)")
    down_avg_pct: float = Field(0.0, description="下跌均值(%)")


class DailySentimentResponse(BaseModel):
    """单日情绪响应"""

    date: str = Field(..., description="日期 YYYY-MM-DD")
    snapshots: List[SentimentSnapshotItem] = Field(default_factory=list)


class RangeSentimentResponse(BaseModel):
    """多日情绪响应"""

    snapshots: List[SentimentSnapshotItem] = Field(default_factory=list)
