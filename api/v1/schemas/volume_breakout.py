# -*- coding: utf-8 -*-
"""放量检测 API 响应模型"""

from typing import List
from pydantic import BaseModel


class BreakoutStock(BaseModel):
    code: str
    name: str
    volume: float
    yesterday_volume: float
    avg_3d_volume: float = 0
    ratio_vs_yesterday: float
    ratio_vs_3d_avg: float = 0
    sector_name: str = ""
    concept_names: str = ""


class BreakoutETF(BaseModel):
    code: str
    name: str
    volume: float
    yesterday_volume: float
    ratio_vs_yesterday: float


class BreakoutSector(BaseModel):
    name: str
    agg_volume: float
    yesterday_agg_volume: float
    ratio: float
    constituent_count: int


class BreakoutConcept(BaseModel):
    code: str = ""
    name: str
    agg_volume: float
    yesterday_agg_volume: float
    ratio: float
    constituent_count: int


class WordCloudWord(BaseModel):
    text: str
    value: int


class BreakoutResponse(BaseModel):
    date: str
    stock_count: int
    etf_count: int
    sector_count: int
    concept_count: int
    stocks: List[BreakoutStock]
    etfs: List[BreakoutETF]
    sectors: List[BreakoutSector]
    concepts: List[BreakoutConcept]
    sector_words: List[WordCloudWord]
    concept_words: List[WordCloudWord]


class BreakoutDatesResponse(BaseModel):
    dates: List[str]
