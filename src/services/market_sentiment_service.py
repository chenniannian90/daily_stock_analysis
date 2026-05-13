# -*- coding: utf-8 -*-
"""市场情绪快照服务 — 采集、存储、查询。"""

import logging
from datetime import date, datetime
from typing import List, Optional

from src.storage import DatabaseManager, MarketSentimentSnapshot

logger = logging.getLogger(__name__)


def take_market_snapshot(override_time: Optional[datetime] = None) -> Optional[dict]:
    """采集当前市场情绪快照并存入 DB。

    Args:
        override_time: 可选时间覆盖，用于盘后重试时标为收盘时间
    """
    from data_provider.akshare_fetcher import AkshareFetcher

    fetcher = AkshareFetcher()
    stats = fetcher.get_market_stats()
    if not stats:
        logger.warning("[市场情绪] 获取市场统计失败，跳过快照")
        return None

    now = override_time or datetime.now()
    today = date.today()
    db = DatabaseManager.get_instance()

    try:
        with db.session_scope() as session:
            snap = MarketSentimentSnapshot(
                snapshot_time=now,
                date=today,
                up_count=stats.get('up_count', 0),
                down_count=stats.get('down_count', 0),
                flat_count=stats.get('flat_count', 0),
                limit_up_count=stats.get('limit_up_count', 0),
                limit_down_count=stats.get('limit_down_count', 0),
                total_volume=stats.get('total_volume', 0.0),
                total_amount=stats.get('total_amount', 0.0),
                up_median_pct=stats.get('up_median_pct', 0.0),
                down_median_pct=stats.get('down_median_pct', 0.0),
                up_avg_pct=stats.get('up_avg_pct', 0.0),
                down_avg_pct=stats.get('down_avg_pct', 0.0),
                all_median_pct=stats.get('all_median_pct', 0.0),
                all_avg_pct=stats.get('all_avg_pct', 0.0),
            )
            session.add(snap)
            session.flush()
            snap_id = snap.id
    except Exception:
        logger.exception("[市场情绪] 快照入库失败")
        return None

    logger.info(
        "[市场情绪] 快照已保存 id=%s time=%s up=%s down=%s limit_up=%s limit_down=%s amount=%.0f亿",
        snap_id,
        now.strftime("%H:%M"),
        stats.get('up_count', 0),
        stats.get('down_count', 0),
        stats.get('limit_up_count', 0),
        stats.get('limit_down_count', 0),
        stats.get('total_amount', 0.0),
    )
    return stats


def get_snapshots_by_date(target_date: date) -> List[dict]:
    """查询某日所有快照，按时间升序。"""
    from sqlalchemy import select

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        rows = session.execute(
            select(MarketSentimentSnapshot)
            .where(MarketSentimentSnapshot.date == target_date)
            .order_by(MarketSentimentSnapshot.snapshot_time)
        ).scalars().all()
        return [r.to_dict() for r in rows]


def get_snapshots_by_range(start_date: date, end_date: date) -> List[dict]:
    """查询日期范围内的快照。"""
    from sqlalchemy import select

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        rows = session.execute(
            select(MarketSentimentSnapshot)
            .where(
                MarketSentimentSnapshot.date >= start_date,
                MarketSentimentSnapshot.date <= end_date,
            )
            .order_by(MarketSentimentSnapshot.date, MarketSentimentSnapshot.snapshot_time)
        ).scalars().all()
        return [r.to_dict() for r in rows]


def snapshot_exists_for_time(target_date: date, time_str: str) -> bool:
    """检查指定日期+时间是否已有快照（防重复采集）。"""
    snapshots = get_snapshots_by_date(target_date)
    return any(s['snapshot_time'] == time_str for s in snapshots)
