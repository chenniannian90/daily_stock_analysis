# -*- coding: utf-8 -*-
"""放量检测 API 端点。"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.volume_breakout import (
    BreakoutConcept,
    BreakoutDatesResponse,
    BreakoutETF,
    BreakoutResponse,
    BreakoutSector,
    BreakoutStock,
    WordCloudWord,
)
from src.services.volume_breakout_service import get_available_dates, get_breakout_results

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/results", response_model=BreakoutResponse)
def get_results(
    date_str: str = Query("", alias="date", description="基准日期 YYYY-MM-DD，空则最新"),
):
    """获取放量检测结果。"""
    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效日期格式: {date_str}，应为 YYYY-MM-DD")

    data = get_breakout_results(target_date=target_date)

    return BreakoutResponse(
        date=data["date"],
        stock_count=data["stock_count"],
        etf_count=data["etf_count"],
        sector_count=data["sector_count"],
        concept_count=data["concept_count"],
        stocks=[BreakoutStock(**s) for s in data["stocks"]],
        etfs=[BreakoutETF(**e) for e in data["etfs"]],
        sectors=[BreakoutSector(**s) for s in data["sectors"]],
        concepts=[BreakoutConcept(**c) for c in data["concepts"]],
        sector_words=[WordCloudWord(**w) for w in data["sector_words"]],
        concept_words=[WordCloudWord(**w) for w in data["concept_words"]],
    )


@router.get("/dates", response_model=BreakoutDatesResponse)
def get_dates(days: int = Query(30, description="查询最近N天")):
    """获取有数据的交易日列表。"""
    dates = get_available_dates(days=min(days, 90))
    return BreakoutDatesResponse(dates=dates)
