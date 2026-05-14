# -*- coding: utf-8 -*-
"""放量检测服务 — 每交易日18:00自动检测全市场放量标的。

四类检测:
- 个股（剔除ST）：成交量 > 2× 昨日 & > 2× 近3日均量
- ETF：成交量 > 1.5× 昨日
- 板块（申万行业）：成分股合计成交量 > 1.5× 昨日
- 同花顺概念：成分股合计成交量 > 1.5× 昨日
"""

import logging
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import desc, select

from src.storage import ConceptStockMapping, DatabaseManager, StockDailyStat

logger = logging.getLogger(__name__)


def _get_trading_dates_before(db, ref_date: date, count: int) -> List[date]:
    S = StockDailyStat
    try:
        with db.get_session() as session:
            rows = session.execute(
                select(S.date)
                .where(S.date <= ref_date)
                .distinct()
                .order_by(desc(S.date))
                .limit(count)
            ).scalars().all()
            return list(rows)
    except Exception:
        return []


def _detect_stock_breakout(db, today, yesterday, dates_3d) -> List[Dict]:
    S = StockDailyStat
    try:
        with db.get_session() as session:
            today_rows = session.execute(
                select(S.stock_code, S.stock_name, S.volume, S.sector_name)
                .where(S.date == today, S.security_type == "stock")
            ).all()

            yest_vols = {}
            if yesterday:
                yest_rows = session.execute(
                    select(S.stock_code, S.volume)
                    .where(S.date == yesterday, S.security_type == "stock")
                ).all()
                yest_vols = {r.stock_code: (r.volume or 0) for r in yest_rows}

            avg_vols = {}
            if dates_3d:
                d3_rows = session.execute(
                    select(S.stock_code, S.volume)
                    .where(S.date.in_(dates_3d), S.security_type == "stock")
                ).all()
                d3_groups: Dict[str, List[float]] = defaultdict(list)
                for r in d3_rows:
                    if r.volume:
                        d3_groups[r.stock_code].append(r.volume)
                avg_vols = {
                    code: sum(vols) / len(vols)
                    for code, vols in d3_groups.items()
                }
    except Exception:
        logger.exception("[放量检测] 个股查询失败")
        return []

    results = []
    for r in today_rows:
        code = r.stock_code
        today_vol = r.volume or 0
        if today_vol <= 0:
            continue
        yest_vol = yest_vols.get(code, 0)
        avg_3d = avg_vols.get(code, 0)

        if yest_vol > 0 and avg_3d > 0:
            if today_vol > 2 * yest_vol and today_vol > 2 * avg_3d:
                results.append({
                    "code": code,
                    "name": r.stock_name or "",
                    "volume": today_vol,
                    "yesterday_volume": yest_vol,
                    "avg_3d_volume": round(avg_3d, 2),
                    "ratio_vs_yesterday": round(today_vol / yest_vol, 2),
                    "ratio_vs_3d_avg": round(today_vol / avg_3d, 2),
                    "sector_name": r.sector_name or "",
                })
        elif yest_vol > 0 and today_vol > 2 * yest_vol:
            results.append({
                "code": code,
                "name": r.stock_name or "",
                "volume": today_vol,
                "yesterday_volume": yest_vol,
                "avg_3d_volume": 0,
                "ratio_vs_yesterday": round(today_vol / yest_vol, 2),
                "ratio_vs_3d_avg": 0,
                "sector_name": r.sector_name or "",
            })

    results.sort(key=lambda x: -x["ratio_vs_yesterday"])
    return results


def _detect_etf_breakout(db, today, yesterday) -> List[Dict]:
    if not yesterday:
        return []

    S = StockDailyStat
    try:
        with db.get_session() as session:
            today_rows = session.execute(
                select(S.stock_code, S.stock_name, S.volume)
                .where(S.date == today, S.security_type == "etf")
            ).all()

            yest_rows = session.execute(
                select(S.stock_code, S.volume)
                .where(S.date == yesterday, S.security_type == "etf")
            ).all()
            yest_vols = {r.stock_code: (r.volume or 0) for r in yest_rows}
    except Exception:
        logger.exception("[放量检测] ETF查询失败")
        return []

    results = []
    for r in today_rows:
        code = r.stock_code
        today_vol = r.volume or 0
        if today_vol <= 0:
            continue
        yest_vol = yest_vols.get(code, 0)
        if yest_vol > 0 and today_vol > 1.5 * yest_vol:
            results.append({
                "code": code,
                "name": r.stock_name or "",
                "volume": today_vol,
                "yesterday_volume": yest_vol,
                "ratio_vs_yesterday": round(today_vol / yest_vol, 2),
            })

    results.sort(key=lambda x: -x["ratio_vs_yesterday"])
    return results


def _detect_sector_breakout(db, today, yesterday) -> List[Dict]:
    if not yesterday:
        return []

    S = StockDailyStat
    try:
        with db.get_session() as session:
            today_rows = session.execute(
                select(S.stock_code, S.volume, S.sector_name)
                .where(S.date == today, S.security_type == "stock")
            ).all()
            yest_rows = session.execute(
                select(S.stock_code, S.volume, S.sector_name)
                .where(S.date == yesterday, S.security_type == "stock")
            ).all()
    except Exception:
        logger.exception("[放量检测] 板块查询失败")
        return []

    today_agg: Dict[str, Dict] = {}
    for r in today_rows:
        sn = (r.sector_name or "").strip()
        if not sn:
            continue
        if sn not in today_agg:
            today_agg[sn] = {"volume": 0, "codes": set()}
        today_agg[sn]["volume"] += (r.volume or 0)
        today_agg[sn]["codes"].add(r.stock_code)

    yest_agg: Dict[str, float] = defaultdict(float)
    for r in yest_rows:
        sn = (r.sector_name or "").strip()
        if sn:
            yest_agg[sn] += (r.volume or 0)

    results = []
    for sector_name, data in today_agg.items():
        today_vol = data["volume"]
        yest_vol = yest_agg.get(sector_name, 0)
        if today_vol <= 0 or yest_vol <= 0:
            continue
        if today_vol > 1.5 * yest_vol:
            results.append({
                "name": sector_name,
                "agg_volume": today_vol,
                "yesterday_agg_volume": yest_vol,
                "ratio": round(today_vol / yest_vol, 2),
                "constituent_count": len(data["codes"]),
            })

    results.sort(key=lambda x: -x["ratio"])
    return results


def _detect_concept_breakout(db, today, yesterday) -> List[Dict]:
    if not yesterday:
        return []

    S = StockDailyStat
    try:
        with db.get_session() as session:
            today_rows = session.execute(
                select(S.stock_code, S.volume)
                .where(S.date == today, S.security_type == "stock")
            ).all()
            yest_rows = session.execute(
                select(S.stock_code, S.volume)
                .where(S.date == yesterday, S.security_type == "stock")
            ).all()
            mapping_rows = session.execute(
                select(
                    ConceptStockMapping.concept_code,
                    ConceptStockMapping.concept_name,
                    ConceptStockMapping.stock_code,
                )
            ).all()
    except Exception:
        logger.exception("[放量检测] 概念查询失败")
        return []

    today_vols = {r.stock_code: (r.volume or 0) for r in today_rows}
    yest_vols = {r.stock_code: (r.volume or 0) for r in yest_rows}

    concept_agg: Dict[str, Dict] = {}
    for m in mapping_rows:
        key = m.concept_code
        if key not in concept_agg:
            concept_agg[key] = {
                "name": m.concept_name or "",
                "codes": set(),
                "today_vol": 0,
                "yest_vol": 0,
            }
        concept_agg[key]["codes"].add(m.stock_code)
        concept_agg[key]["today_vol"] += today_vols.get(m.stock_code, 0)
        concept_agg[key]["yest_vol"] += yest_vols.get(m.stock_code, 0)

    results = []
    for concept_code, cdata in concept_agg.items():
        today_v = cdata["today_vol"]
        yest_v = cdata["yest_vol"]
        if today_v <= 0 or yest_v <= 0:
            continue
        if today_v > 1.5 * yest_v:
            results.append({
                "code": concept_code,
                "name": cdata["name"],
                "agg_volume": today_v,
                "yesterday_agg_volume": yest_v,
                "ratio": round(today_v / yest_v, 2),
                "constituent_count": len(cdata["codes"]),
            })

    results.sort(key=lambda x: -x["ratio"])
    return results


def get_breakout_results(target_date: Optional[date] = None) -> Dict:
    db = DatabaseManager.get_instance()
    S = StockDailyStat

    if target_date is None:
        with db.get_session() as session:
            latest = session.execute(
                select(S.date).order_by(desc(S.date)).limit(1)
            ).scalars().first()
            if latest is None:
                return _empty_result("")
            target_date = latest if isinstance(latest, date) else datetime.strptime(str(latest), "%Y-%m-%d").date()

    trading_dates = _get_trading_dates_before(db, target_date, 4)
    if not trading_dates or trading_dates[0] != target_date:
        return _empty_result(target_date.isoformat())

    today = trading_dates[0]
    yesterday = trading_dates[1] if len(trading_dates) > 1 else None
    dates_3d = trading_dates[1:4] if len(trading_dates) > 1 else []

    stocks = _detect_stock_breakout(db, today, yesterday, dates_3d)
    etfs = _detect_etf_breakout(db, today, yesterday)
    sectors = _detect_sector_breakout(db, today, yesterday)
    concepts = _detect_concept_breakout(db, today, yesterday)

    # 获取放量个股的概念
    stock_codes = [s["code"] for s in stocks]
    concept_map: Dict[str, str] = {}
    if stock_codes:
        try:
            from src.services.concept_service import get_concept_map_for_stocks
            concept_map = get_concept_map_for_stocks(stock_codes, max_concepts=5)
        except ImportError:
            pass

    # 回填 concept_names 到个股
    for s in stocks:
        s["concept_names"] = concept_map.get(s["code"], "")

    # 构建词云
    sector_words = _build_sector_words(stocks)
    concept_words = _build_concept_words(stocks, concept_map)

    logger.info("[放量检测] 个股%d ETF%d 板块%d 概念%d",
                len(stocks), len(etfs), len(sectors), len(concepts))

    return {
        "date": target_date.isoformat(),
        "stock_count": len(stocks),
        "etf_count": len(etfs),
        "sector_count": len(sectors),
        "concept_count": len(concepts),
        "stocks": stocks,
        "etfs": etfs,
        "sectors": sectors,
        "concepts": concepts,
        "sector_words": sector_words,
        "concept_words": concept_words,
    }


def _build_sector_words(stocks: List[Dict]) -> List[Dict]:
    weight: Dict[str, int] = defaultdict(int)
    for s in stocks:
        sn = s.get("sector_name", "").strip()
        if sn:
            weight[sn] += 1
    return sorted(
        [{"text": k, "value": v} for k, v in weight.items()],
        key=lambda x: -x["value"],
    )[:80]


def _build_concept_words(stocks: List[Dict], concept_map: Dict[str, str]) -> List[Dict]:
    try:
        from src.services.concept_service import _EXCLUDE_CONCEPT_PATTERNS
    except ImportError:
        _EXCLUDE_CONCEPT_PATTERNS = []

    _FILTER_RE = re.compile("|".join(_EXCLUDE_CONCEPT_PATTERNS), re.IGNORECASE) if _EXCLUDE_CONCEPT_PATTERNS else None

    weight: Dict[str, int] = defaultdict(int)
    for s in stocks:
        concepts_str = concept_map.get(s["code"], "")
        if not concepts_str:
            continue
        for cname in concepts_str.split("/"):
            cname = cname.strip()
            if not cname:
                continue
            if _FILTER_RE and _FILTER_RE.search(cname):
                continue
            weight[cname] += 1

    return sorted(
        [{"text": k, "value": v} for k, v in weight.items()],
        key=lambda x: -x["value"],
    )[:100]


def _empty_result(date_str: str) -> Dict:
    return {
        "date": date_str,
        "stock_count": 0,
        "etf_count": 0,
        "sector_count": 0,
        "concept_count": 0,
        "stocks": [],
        "etfs": [],
        "sectors": [],
        "concepts": [],
        "sector_words": [],
        "concept_words": [],
    }


def get_available_dates(days: int = 30) -> List[str]:
    db = DatabaseManager.get_instance()
    S = StockDailyStat
    try:
        with db.get_session() as session:
            rows = session.execute(
                select(S.date)
                .distinct()
                .order_by(desc(S.date))
                .limit(min(days, 90))
            ).scalars().all()
            return [d.isoformat() if isinstance(d, date) else str(d) for d in rows]
    except Exception:
        logger.exception("[放量检测] 日期查询失败")
        return []
