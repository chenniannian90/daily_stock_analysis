# -*- coding: utf-8 -*-
"""股票统计词云 API 端点。"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.stock_stat import DatesResponse, WordCloudResponse, WordCloudWord
from src.services.stock_stat_service import WINDOWS, get_available_dates, get_word_cloud_data

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/wordcloud", response_model=WordCloudResponse)
def get_wordcloud(
    date_str: str = Query("", alias="date", description="基准日期 YYYY-MM-DD，空则最新"),
    window: int = Query(5, description="时间窗口(交易日): 1|3|5|10|20"),
    stat_type: str = Query("gain", alias="type", description="统计类型: gain(涨幅>5%) | vol(波动率>5%)"),
):
    """获取词云数据（板块+概念）。"""
    if window not in WINDOWS:
        raise HTTPException(status_code=400, detail=f"无效 window: {window}，支持 {WINDOWS}")
    if stat_type not in ("gain", "vol"):
        raise HTTPException(status_code=400, detail="无效 type，支持 gain 或 vol")

    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效日期格式: {date_str}，应为 YYYY-MM-DD")

    data = get_word_cloud_data(
        target_date=target_date,
        window=window,
        stat_type=stat_type,
    )

    return WordCloudResponse(
        date=data["date"],
        window=data["window"],
        type=data["type"],
        qualifying_count=data["qualifying_count"],
        sector_words=[WordCloudWord(**w) for w in data["sector_words"]],
        concept_words=[WordCloudWord(**w) for w in data["concept_words"]],
    )


@router.get("/dates", response_model=DatesResponse)
def get_dates(days: int = Query(30, description="查询最近N天")):
    """获取有数据的交易日列表。"""
    dates = get_available_dates(days=min(days, 90))
    return DatesResponse(dates=dates)
