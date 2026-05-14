# -*- coding: utf-8 -*-
"""板块排名服务 — 采集行业/概念板块每日快照，支持多时间窗口排名查询"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import and_, delete as sa_delete, desc, func, select

from src.storage import DatabaseManager, SectorDailySnapshot

logger = logging.getLogger(__name__)

WINDOWS = [1, 3, 5, 10, 20]
SECTOR_TYPES = ['industry', 'concept']
SORT_FIELDS = {
    'gain': 'change_pct',
    'capital_flow': 'net_capital_flow',
    'limit_up': 'limit_up_count',
}

# ── Name normalisation for cross-API matching ──────────────────────────────

def _normalise(name: str) -> str:
    """Remove common suffixes so names from different APIs can match."""
    if not name:
        return ""
    for sfx in ["行业", "板块", "概念", "申万"]:
        if name.endswith(sfx):
            name = name[:-len(sfx)]
    return name.strip()


# ── Board list fetch (with fallback) ────────────────────────────────────────

def _fetch_board_list(sector_type: str) -> Optional[pd.DataFrame]:
    """Fetch sector board list, falling back to Sina if EastMoney fails."""
    import akshare as ak

    # Primary: EastMoney
    try:
        if sector_type == "industry":
            df = ak.stock_board_industry_name_em()
        else:
            df = ak.stock_board_concept_name_em()
        if df is not None and not df.empty:
            return df
    except Exception:
        logger.warning("[板块排名] 东财%s板块列表失败，尝试新浪", sector_type)

    # Fallback: Sina stock_sector_spot
    try:
        indicator = "行业" if sector_type == "industry" else "概念"
        df = ak.stock_sector_spot(indicator=indicator)
        if df is not None and not df.empty:
            # Normalise columns to match EastMoney format
            col_map = {}
            for c in df.columns:
                if c == "板块":
                    col_map["板块"] = "板块名称"
                if c == "总成交额(万元)":
                    col_map["总成交额(万元)"] = "总成交额"
            if col_map:
                df = df.rename(columns=col_map)
            # Sina doesn't have 板块代码; generate pseudo-codes
            if "板块代码" not in df.columns:
                pseudo_codes = []
                for _, row in df.iterrows():
                    name = str(row.get("板块名称", row.get("板块", "")))
                    pseudo_codes.append(f"SINA_{hash(name) & 0x7FFFFFFF:08x}")
                df["板块代码"] = pseudo_codes
            # Convert 总成交额 from 万元 to 元 so our /1e8 conversion works
            if "总成交额" in df.columns:
                try:
                    df["总成交额"] = pd.to_numeric(df["总成交额"], errors="coerce") * 1e4
                except Exception:
                    pass
            return df
    except Exception:
        logger.exception("[板块排名] 新浪%s板块列表也失败", sector_type)
        return None


# ── Fund-flow fetch ─────────────────────────────────────────────────────────

def _fetch_fund_flow(sector_type: str) -> Optional[pd.DataFrame]:
    """Try akshare fund-flow APIs, return first successful DataFrame."""
    import akshare as ak

    stype_cn = "行业资金流" if sector_type == "industry" else "概念资金流"
    fn = "stock_fund_flow_industry" if sector_type == "industry" else "stock_fund_flow_concept"

    # Ordered candidates: most specific → generic fallback
    candidates = [
        ("stock_sector_fund_flow_rank", {"sector_type": stype_cn, "indicator": "今日"}),
        ("stock_sector_fund_flow_rank", {"indicator": "今日排行"}),
        (fn, {"symbol": "今日排行"}),
    ]

    for fn_name, kwargs in candidates:
        fn_obj = getattr(ak, fn_name, None)
        if fn_obj is None:
            continue
        try:
            df = fn_obj(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.info("[板块排名] 资金流数据源: %s(%s)", fn_name, kwargs)
                return df
        except Exception:
            continue

    return None


def _extract_fund_flow_map(df: pd.DataFrame) -> Dict[str, float]:
    """Extract {normalised_name: net_capital_flow} from fund flow DataFrame."""
    name_col = next((c for c in df.columns
                     if any(k in str(c) for k in ("板块", "行业", "名称", "name", "概念"))), None)
    flow_col = next((c for c in df.columns
                     if any(k in str(c) for k in ("净流入", "主力", "flow", "净额"))), None)

    if name_col is None or flow_col is None:
        logger.warning("[板块排名] 资金流列匹配失败，可用列: %s", list(df.columns))
        return {}

    result: Dict[str, float] = {}
    for _, row in df.iterrows():
        n = _normalise(str(row.get(name_col, "")))
        try:
            v = float(row.get(flow_col, 0))
        except (ValueError, TypeError):
            continue
        if n:
            result[n] = v / 1e8  # 元 → 亿
    return result


# ── Limit-up count per sector ────────────────────────────────────────────────

def _fetch_limit_up_map(trade_date: str) -> Dict[str, int]:
    """Get limit-up count grouped by sector from stock_zt_pool_em."""
    try:
        import akshare as ak
        df = ak.stock_zt_pool_em(date=trade_date)
        if df is None or df.empty:
            return {}
        counts = df.groupby("所属行业").size()
        return {_normalise(str(k)): int(v) for k, v in counts.items()}
    except Exception:
        logger.debug("[板块排名] 涨停池获取失败", exc_info=True)
        return {}


# ── Main collection ─────────────────────────────────────────────────────────

def collect_daily_snapshots(sector_type: str = "industry",
                            target_date: Optional[date] = None) -> int:
    """采集当日板块快照，返回写入条数。

    Args:
        sector_type: 'industry' 或 'concept'
        target_date: 目标日期，默认今天
    """
    import akshare as ak

    if sector_type not in ("industry", "concept"):
        logger.error("[板块排名] 无效 sector_type: %s", sector_type)
        return 0

    today = target_date or date.today()
    today_str = today.strftime("%Y%m%d")

    # 1. Get sector list with daily gain
    try:
        if sector_type == "industry":
            board_df = _fetch_board_list("industry")
        else:
            board_df = _fetch_board_list("concept")
        if board_df is None or board_df.empty:
            logger.error("[板块排名] %s板块列表为空", sector_type)
            return 0
        logger.info("[板块排名] 获取到 %d 个%s板块", len(board_df),
                     "行业" if sector_type == "industry" else "概念")
    except Exception:
        logger.exception("[板块排名] 板块列表获取失败")
        return 0

    # 2. Get fund flow
    fund_flow_map: Dict[str, float] = {}
    try:
        ff_df = _fetch_fund_flow(sector_type)
        if ff_df is not None:
            fund_flow_map = _extract_fund_flow_map(ff_df)
            logger.info("[板块排名] 匹配到 %d 个板块资金流", len(fund_flow_map))
    except Exception:
        logger.exception("[板块排名] 资金流采集失败")

    # 3. Get limit-up count per sector
    limit_up_map: Dict[str, int] = {}
    try:
        limit_up_map = _fetch_limit_up_map(today_str)
        logger.info("[板块排名] 匹配到 %d 个板块涨停数据", len(limit_up_map))
    except Exception:
        logger.exception("[板块排名] 涨停统计失败")

    # 4. Build snapshots
    snapshots: list = []
    for _, row in board_df.iterrows():
        code = str(row.get("板块代码", ""))
        name = str(row.get("板块名称", ""))
        if not code or not name:
            continue

        norm_name = _normalise(name)
        change_pct = float(row.get("涨跌幅", 0) or 0)
        up_cnt = int(row.get("上涨家数", 0) or 0)
        down_cnt = int(row.get("下跌家数", 0) or 0)
        amount = float(row.get("总成交额", 0) or 0) / 1e8  # 元→亿

        snapshots.append({
            "date": today,
            "sector_code": code,
            "sector_name": name,
            "sector_type": sector_type,
            "change_pct": change_pct,
            "net_capital_flow": fund_flow_map.get(norm_name, 0.0),
            "limit_up_count": limit_up_map.get(norm_name, 0),
            "up_count": up_cnt,
            "down_count": down_cnt,
            "total_amount": amount,
        })

    # 5. Clear old data for this date+sector_type, then bulk write
    db = DatabaseManager.get_instance()
    written = 0
    try:
        with db.session_scope() as session:
            session.execute(
                sa_delete(SectorDailySnapshot).where(
                    SectorDailySnapshot.date == today,
                    SectorDailySnapshot.sector_type == sector_type,
                )
            )
            session.bulk_insert_mappings(SectorDailySnapshot, snapshots)
            written = len(snapshots)
        logger.info("[板块排名] %s 板块 %s: 写入 %d 条",
                     sector_type, today.isoformat(), written)
    except Exception:
        logger.exception("[板块排名] DB 写入失败")
        return 0

    return written


# ── Query ────────────────────────────────────────────────────────────────────

def _get_trading_dates_before(db, ref_date: date, count: int) -> List[date]:
    """Return up to `count` trading dates on or before ref_date that have data."""
    from src.storage import SectorDailySnapshot as S
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


def get_rankings(
    target_date: Optional[date] = None,
    sector_type: str = "industry",
    window: int = 1,
    sort_by: str = "gain",
    limit: int = 20,
) -> List[Dict]:
    """查询板块排名。

    Args:
        target_date: 基准日期，默认最新有数据的交易日
        sector_type: 'industry' | 'concept'
        window: 时间窗口 (1/3/5/10/20 交易日)
        sort_by: 'gain' | 'capital_flow' | 'limit_up'
        limit: 返回条数
    """
    if sector_type not in ("industry", "concept"):
        return []
    if window not in WINDOWS:
        return []
    field = SORT_FIELDS.get(sort_by)
    if field is None:
        return []

    db = DatabaseManager.get_instance()
    S = SectorDailySnapshot

    # Determine base date
    if target_date is None:
        with db.get_session() as session:
            latest = session.execute(
                select(S.date).where(S.sector_type == sector_type)
                .order_by(desc(S.date)).limit(1)
            ).scalars().first()
            if latest is None:
                return []
            target_date = latest if isinstance(latest, date) else datetime.strptime(str(latest), "%Y-%m-%d").date()

    # Get trading dates in window
    trading_dates = _get_trading_dates_before(db, target_date, window)
    if not trading_dates:
        return []

    try:
        with db.get_session() as session:
            rows = session.execute(
                select(
                    S.sector_code,
                    S.sector_name,
                    func.sum(S.change_pct).label("change_pct"),
                    func.sum(S.net_capital_flow).label("net_capital_flow"),
                    func.sum(S.limit_up_count).label("limit_up_count"),
                )
                .where(
                    and_(S.sector_type == sector_type, S.date.in_(trading_dates))
                )
                .group_by(S.sector_code, S.sector_name)
                .order_by(desc(field))
                .limit(limit)
            ).all()
    except Exception:
        logger.exception("[板块排名] 查询失败")
        return []

    result = []
    for rank_i, r in enumerate(rows, 1):
        result.append({
            "rank": rank_i,
            "sector_code": r.sector_code,
            "sector_name": r.sector_name,
            "change_pct": round(r.change_pct or 0, 2),
            "net_capital_flow": round(r.net_capital_flow or 0, 2),
            "limit_up_count": int(r.limit_up_count or 0),
            "window": window,
            "date": target_date.isoformat() if target_date else "",
        })
    return result


def get_available_dates(sector_type: str = "industry", days: int = 30) -> List[str]:
    """获取最近有数据的交易日列表。"""
    db = DatabaseManager.get_instance()
    S = SectorDailySnapshot
    try:
        with db.get_session() as session:
            rows = session.execute(
                select(S.date)
                .where(S.sector_type == sector_type)
                .distinct()
                .order_by(desc(S.date))
                .limit(min(days, 90))
            ).scalars().all()
            return [d.isoformat() if isinstance(d, date) else str(d) for d in rows]
    except Exception:
        logger.exception("[板块排名] 日期查询失败")
        return []


def backfill_history(sector_type: str = "industry", days: int = 30) -> int:
    """回填历史数据 — 遍历过去 N 个自然日，对每个交易日采集快照。"""
    from src.core.trading_calendar import is_market_open

    collected = 0
    d = date.today()
    while days > 0:
        if is_market_open("cn", d):
            logger.info("[板块排名] 回填 %s %s", sector_type, d.isoformat())
            n = collect_daily_snapshots(sector_type, target_date=d)
            if n > 0:
                collected += n
            days -= 1
        d = d - timedelta(days=1)
    return collected
