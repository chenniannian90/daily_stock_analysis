# -*- coding: utf-8 -*-
"""龙头战法 API 端点。"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.dragon_strategy import DragonAnalysisResponse, DragonDatesResponse
from src.services.dragon_analysis_service import (
    get_dragon_analysis_by_date,
    get_dragon_analysis_dates,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=DragonAnalysisResponse)
def get_dragon_analysis(date_str: str = Query(..., alias="date", description="日期 YYYY-MM-DD")):
    """获取某日龙头战法分析结果（优先返回17:00收盘结果，其次14:30）。"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效日期格式: {date_str}，应为 YYYY-MM-DD")

    row = get_dragon_analysis_by_date(target_date)
    if not row:
        raise HTTPException(status_code=404, detail=f"未找到 {date_str} 的龙头战法分析结果")

    result = row.get("result", {})
    return DragonAnalysisResponse(
        date=row.get("date", date_str),
        run_time=row.get("run_time"),
        board_summary=result.get("board_summary"),
        dragon_result=result.get("dragon_result"),
    )


@router.get("/dates", response_model=DragonDatesResponse)
def get_dragon_dates(days: int = Query(30, description="查询最近N天")):
    """获取最近N天有龙头战法分析数据的日期列表。"""
    dates = get_dragon_analysis_dates(days=min(days, 90))
    return DragonDatesResponse(dates=dates)
