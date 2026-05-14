# -*- coding: utf-8 -*-
"""股票统计词云 API schemas。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WordCloudWord(BaseModel):
    """词云词汇"""

    text: str = Field(..., description="词汇文本")
    value: int = Field(..., description="权重")


class WordCloudResponse(BaseModel):
    """词云数据响应"""

    date: str = Field(..., description="基准日期 YYYY-MM-DD")
    window: int = Field(..., description="时间窗口（交易日）")
    type: str = Field(..., description="统计类型: gain | vol")
    qualifying_count: int = Field(0, description="达标股票数")
    sector_words: List[WordCloudWord] = Field(default_factory=list, description="板块词云")
    concept_words: List[WordCloudWord] = Field(default_factory=list, description="概念词云")


class DatesResponse(BaseModel):
    """有数据的日期列表"""

    dates: List[str] = Field(default_factory=list)
