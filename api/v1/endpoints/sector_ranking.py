# -*- coding: utf-8 -*-
"""板块排名 API 端点。"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.sector_ranking import (
    SectorRankingDatesResponse,
    SectorRankingItem,
    SectorRankingResponse,
)
from src.services.sector_ranking_service import (
    WINDOWS,
    SORT_FIELDS,
    get_available_dates,
    get_rankings,
)

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_SECTOR_TYPES = {"industry", "concept"}


def _to_item(row: dict) -> SectorRankingItem:
    return SectorRankingItem(
        rank=row.get("rank", 0),
        sector_code=row.get("sector_code", ""),
        sector_name=row.get("sector_name", ""),
        change_pct=row.get("change_pct", 0.0),
        net_capital_flow=row.get("net_capital_flow", 0.0),
        limit_up_count=row.get("limit_up_count", 0),
        window=row.get("window", 1),
        date=row.get("date", ""),
    )


@router.get("", response_model=SectorRankingResponse)
def get_sector_rankings(
    date_str: str = Query("", alias="date", description="基准日期 YYYY-MM-DD，空则最新"),
    sector_type: str = Query("industry", description="板块类型: industry | concept"),
    window: int = Query(1, description="时间窗口(交易日): 1|3|5|10|20"),
    sort_by: str = Query("gain", description="排序维度: gain|capital_flow|limit_up"),
    limit: int = Query(20, description="返回条数，最大50"),
):
    """查询板块排名 Top N。"""
    if sector_type not in VALID_SECTOR_TYPES:
        raise HTTPException(status_code=400, detail=f"无效 sector_type: {sector_type}，应为 industry 或 concept")
    if window not in WINDOWS:
        raise HTTPException(status_code=400, detail=f"无效 window: {window}，支持 {WINDOWS}")
    if sort_by not in SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"无效 sort_by: {sort_by}，支持 {list(SORT_FIELDS)}")
    limit = min(max(1, limit), 50)

    target_date = None
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效日期格式: {date_str}，应为 YYYY-MM-DD")

    items = get_rankings(
        target_date=target_date,
        sector_type=sector_type,
        window=window,
        sort_by=sort_by,
        limit=limit,
    )

    real_date = items[0]["date"] if items else (date_str or "")
    return SectorRankingResponse(
        date=real_date,
        sector_type=sector_type,
        window=window,
        sort_by=sort_by,
        items=[_to_item(r) for r in items],
    )


@router.get("/dates", response_model=SectorRankingDatesResponse)
def get_dates(
    sector_type: str = Query("industry", description="板块类型: industry | concept"),
    days: int = Query(30, description="查询最近N天"),
):
    """获取有数据的交易日列表。"""
    if sector_type not in VALID_SECTOR_TYPES:
        raise HTTPException(status_code=400, detail=f"无效 sector_type: {sector_type}")
    dates = get_available_dates(sector_type, days=min(days, 90))
    return SectorRankingDatesResponse(dates=dates)
