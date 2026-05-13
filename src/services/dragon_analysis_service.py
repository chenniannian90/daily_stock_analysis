# -*- coding: utf-8 -*-
"""龙头战法分析持久化服务 — 定时运行 + 存储 + 查询。"""

import json
import logging
from datetime import date, datetime
from typing import List, Optional

from src.storage import DatabaseManager, DragonAnalysisResult

logger = logging.getLogger(__name__)


def run_and_save_dragon_analysis(run_time: str) -> Optional[dict]:
    """运行龙头识别并入库。

    Args:
        run_time: "14:30" 或 "17:00"
    """
    from src.services.dragon_strategy_service import identify_dragon_stocks, get_board_summary

    today = date.today()

    try:
        board_summary = get_board_summary()
    except Exception:
        logger.exception("[龙头战法] 板块概况获取失败")
        board_summary = None

    try:
        dragon_result = identify_dragon_stocks(sector_count=5)
    except Exception:
        logger.exception("[龙头战法] 龙头识别失败")
        return None

    result = {
        "run_time": run_time,
        "date": today.isoformat(),
        "board_summary": board_summary,
        "dragon_result": dragon_result,
        "generated_at": datetime.now().isoformat(),
    }

    db = DatabaseManager.get_instance()
    try:
        with db.session_scope() as session:
            from sqlalchemy import select
            existing = session.execute(
                select(DragonAnalysisResult).where(
                    DragonAnalysisResult.date == today,
                    DragonAnalysisResult.run_time == run_time,
                )
            ).scalars().first()
            if existing:
                existing.result_json = json.dumps(result, ensure_ascii=False, default=str)
                existing.created_at = datetime.now()
                snap_id = existing.id
                logger.info("[龙头战法] 覆盖已有记录 id=%s", snap_id)
            else:
                snap = DragonAnalysisResult(
                    date=today,
                    run_time=run_time,
                    result_json=json.dumps(result, ensure_ascii=False, default=str),
                )
                session.add(snap)
                session.flush()
                snap_id = snap.id
    except Exception:
        logger.exception("[龙头战法] 结果入库失败")
        return None

    logger.info(
        "[龙头战法] 分析结果已保存 id=%s date=%s time=%s 真龙头=%s 超级龙头=%s",
        snap_id,
        today,
        run_time,
        len(dragon_result.get("true_dragons", [])),
        len(dragon_result.get("super_dragons", [])),
    )
    return result


def get_dragon_analysis_by_date(target_date: date) -> Optional[dict]:
    """获取某日最新的龙头分析结果（优先17:00，其次14:30）。"""
    from sqlalchemy import select

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        rows = session.execute(
            select(DragonAnalysisResult)
            .where(DragonAnalysisResult.date == target_date)
            .order_by(DragonAnalysisResult.run_time.desc())
        ).scalars().all()
        return rows[0].to_dict() if rows else None


def get_dragon_analysis_by_date_and_time(target_date: date, run_time: str) -> Optional[dict]:
    """获取某日特定时间的龙头分析结果。"""
    from sqlalchemy import select

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        row = session.execute(
            select(DragonAnalysisResult)
            .where(
                DragonAnalysisResult.date == target_date,
                DragonAnalysisResult.run_time == run_time,
            )
        ).scalars().first()
        return row.to_dict() if row else None


def get_dragon_analysis_dates(days: int = 30) -> List[str]:
    """获取最近N天有龙头分析数据的日期列表。"""
    from datetime import timedelta
    from sqlalchemy import select

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        rows = session.execute(
            select(DragonAnalysisResult.date)
            .where(DragonAnalysisResult.date >= date.today() - timedelta(days=days))
            .group_by(DragonAnalysisResult.date)
            .order_by(DragonAnalysisResult.date.desc())
        ).scalars().all()
        return [r.isoformat() for r in rows]


def dragon_analysis_exists_for_time(target_date: date, run_time: str) -> bool:
    """检查某日某时是否已有分析结果。"""
    from sqlalchemy import select, exists

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        return session.execute(
            select(exists().where(
                DragonAnalysisResult.date == target_date,
                DragonAnalysisResult.run_time == run_time,
            ))
        ).scalar()
