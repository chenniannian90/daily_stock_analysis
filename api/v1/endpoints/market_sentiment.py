# -*- coding: utf-8 -*-
"""市场情绪快照 API 端点。"""

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.market_sentiment import (
    DailySentimentResponse,
    RangeSentimentResponse,
    SentimentSnapshotItem,
)
from src.services.market_sentiment_service import (
    get_snapshots_by_date,
    get_snapshots_by_range,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_item(row: dict) -> SentimentSnapshotItem:
    return SentimentSnapshotItem(
        date=row.get('date', ''),
        time=row.get('snapshot_time', ''),
        up_count=row.get('up_count', 0),
        down_count=row.get('down_count', 0),
        flat_count=row.get('flat_count', 0),
        limit_up_count=row.get('limit_up_count', 0),
        limit_down_count=row.get('limit_down_count', 0),
        total_volume=row.get('total_volume', 0.0),
        total_amount=row.get('total_amount', 0.0),
        up_median_pct=row.get('up_median_pct', 0.0),
        down_median_pct=row.get('down_median_pct', 0.0),
        up_avg_pct=row.get('up_avg_pct', 0.0),
        down_avg_pct=row.get('down_avg_pct', 0.0),
    )


@router.get("", response_model=DailySentimentResponse)
def get_daily_sentiment(date_str: str = Query(..., alias="date", description="日期 YYYY-MM-DD")):
    """获取某日全部市场情绪快照。"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效日期格式: {date_str}，应为 YYYY-MM-DD")

    rows = get_snapshots_by_date(target_date)
    return DailySentimentResponse(
        date=date_str,
        snapshots=[_to_item(r) for r in rows],
    )


@router.get("/range", response_model=RangeSentimentResponse)
def get_range_sentiment(
    start: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end: str = Query(..., description="结束日期 YYYY-MM-DD"),
):
    """获取日期范围内的市场情绪快照。"""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start 不能晚于 end")

    rows = get_snapshots_by_range(start_date, end_date)
    return RangeSentimentResponse(
        snapshots=[_to_item(r) for r in rows],
    )
