# -*- coding: utf-8 -*-
"""板块排名 Pydantic schemas。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SectorRankingItem(BaseModel):
    """单条板块排名"""

    rank: int = Field(..., description="排名")
    sector_code: str = Field(..., description="板块代码 BKXXXX")
    sector_name: str = Field(..., description="板块名称")
    change_pct: float = Field(0.0, description="累计涨跌幅(%)")
    net_capital_flow: float = Field(0.0, description="累计主力净流入(亿)")
    limit_up_count: int = Field(0, description="累计涨停家数")
    window: int = Field(1, description="时间窗口(交易日)")
    date: str = Field("", description="基准日期 YYYY-MM-DD")


class SectorRankingResponse(BaseModel):
    """板块排名响应"""

    date: str = Field(..., description="基准日期 YYYY-MM-DD")
    sector_type: str = Field(..., description="板块类型 industry|concept")
    window: int = Field(..., description="时间窗口 1|3|5|10|20")
    sort_by: str = Field(..., description="排序维度 gain|capital_flow|limit_up")
    items: List[SectorRankingItem] = Field(default_factory=list)


class SectorRankingDatesResponse(BaseModel):
    """可用日期列表"""

    dates: List[str] = Field(default_factory=list)
