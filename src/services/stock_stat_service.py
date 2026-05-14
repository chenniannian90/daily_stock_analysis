# -*- coding: utf-8 -*-
"""全A股每日统计服务 — 采集+词云聚合。

采集全A股（剔除ST）每日行情快照，支持多时间窗口的
涨幅>5% / 波动率>5% 统计，聚合板块/概念词云数据。
"""

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete as sa_delete, desc, select

from data_provider.base import is_st_stock
from src.storage import DatabaseManager, StockDailyStat

logger = logging.getLogger(__name__)

WINDOWS = [1, 3, 5, 10, 20]

# ── Industry mapping cache (tushare stock_basic, rarely changes) ─────────────

_industry_cache: Dict[str, str] = {}
_industry_cache_loaded = False


def _load_industry_map() -> Dict[str, str]:
    """从 tushare stock_basic 加载全市场股票→申万行业映射，缓存于内存。"""
    global _industry_cache, _industry_cache_loaded
    if _industry_cache_loaded:
        return _industry_cache

    try:
        import tushare as ts
        import os
        token = os.getenv('TUSHARE_TOKEN', '')
        if not token:
            logger.warning("[股票统计] TUSHARE_TOKEN 未配置，无法获取行业分类")
            _industry_cache_loaded = True
            return _industry_cache
        ts.set_token(token)
        pro = ts.pro_api()
        df = pro.stock_basic(
            exchange='', list_status='L',
            fields='ts_code,industry',
        )
        if df is None or df.empty:
            logger.warning("[股票统计] tushare stock_basic 返回空")
            _industry_cache_loaded = True
            return _industry_cache

        for _, row in df.iterrows():
            ts_code = str(row.get('ts_code', ''))
            industry = str(row.get('industry', ''))
            if not ts_code or not industry or industry == 'nan':
                continue
            std_code = _ts_code_to_standard(ts_code)
            if std_code:
                _industry_cache[std_code] = industry

        logger.info("[股票统计] 加载行业映射: %d 条", len(_industry_cache))
    except Exception:
        logger.exception("[股票统计] tushare 行业映射加载失败")
    _industry_cache_loaded = True
    return _industry_cache


def _ts_code_to_standard(ts_code: str) -> str:
    """tushare 代码格式 → 项目标准格式: 000001.SZ → sz000001"""
    if not ts_code:
        return ""
    parts = ts_code.split(".")
    if len(parts) == 2:
        return f"{parts[1].lower()}{parts[0]}"
    return ts_code.lower()


# ── Daily snapshot collection ────────────────────────────────────────────────

def collect_daily_stats(target_date: Optional[date] = None) -> int:
    """采集全A股当日行情快照（剔除ST），返回写入条数。"""
    import akshare as ak

    today = target_date or date.today()
    df: Any = None
    source = ""

    # 1. 新浪行情（Docker 中连通性更好）
    logger.info("[股票统计] 获取全A股行情(新浪)...")
    try:
        df = ak.stock_zh_a_spot()
        if df is not None and not df.empty:
            source = "sina"
            logger.info("[股票统计] 新浪行情: %d 条", len(df))
    except Exception:
        logger.warning("[股票统计] 新浪行情失败，尝试东财")

    # 2. 东财 fallback
    if df is None or df.empty:
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                source = "em"
                logger.info("[股票统计] 东财行情: %d 条", len(df))
        except Exception:
            logger.exception("[股票统计] 东财行情也失败")
            return 0

    if df is None or df.empty:
        logger.error("[股票统计] 无可用行情数据")
        return 0

    # 3. 字段映射（兼容新浪/东财列名差异）
    code_col = next((c for c in ['代码', '股票代码'] if c in df.columns), None)
    name_col = next((c for c in ['名称', '股票名称'] if c in df.columns), None)
    pct_col = next((c for c in ['涨跌幅', 'pct_chg'] if c in df.columns), None)
    high_col = next((c for c in ['最高', 'high'] if c in df.columns), None)
    low_col = next((c for c in ['最低', 'low'] if c in df.columns), None)
    pre_col = next((c for c in ['昨收', 'pre_close'] if c in df.columns), None)
    vol_col = next((c for c in ['成交量', 'volume'] if c in df.columns), None)
    sector_col = next((c for c in ['行业', '所属行业'] if c in df.columns), None)

    if not all([code_col, name_col, pct_col, high_col, low_col, pre_col]):
        logger.error("[股票统计] 列匹配失败(%s): %s", source, list(df.columns)[:20])
        return 0

    # 4. 构建快照 + 过滤 ST
    snapshots: list = []
    skipped_st = 0
    for _, row in df.iterrows():
        code = str(row.get(code_col, ''))
        name = str(row.get(name_col, ''))
        if not code or not name:
            continue
        if is_st_stock(name):
            skipped_st += 1
            continue

        try:
            pct = float(row.get(pct_col, 0) or 0)
            high = float(row.get(high_col, 0) or 0)
            low = float(row.get(low_col, 0) or 0)
            pre = float(row.get(pre_col, 0) or 0)
            vol = float(row.get(vol_col, 0) or 0) if vol_col else 0
        except (ValueError, TypeError):
            continue

        sector = str(row.get(sector_col, '')) if sector_col else ''
        if sector == 'nan':
            sector = ''

        snapshots.append({
            "date": today,
            "stock_code": code,
            "stock_name": name,
            "pct_chg": pct,
            "high": high,
            "low": low,
            "pre_close": pre,
            "volume": vol,
            "security_type": "stock",
            "sector_name": sector,
        })

    if not snapshots:
        logger.warning("[股票统计] 无有效数据（ST过滤:%d）", skipped_st)
        return 0

    logger.info("[股票统计] 有效: %d, 剔除ST: %d, 来源: %s", len(snapshots), skipped_st, source)

    # 5. 回填行业分类（tushare 申万行业）
    industry_map = _load_industry_map()
    if industry_map:
        filled = 0
        for s in snapshots:
            if not s["sector_name"]:
                ind = industry_map.get(s["stock_code"], "")
                if ind:
                    s["sector_name"] = ind
                    filled += 1
        if filled:
            logger.info("[股票统计] 行业回填: %d 条", filled)

    # 6. 写入 DB（先删后插）
    db = DatabaseManager.get_instance()
    try:
        with db.session_scope() as session:
            session.execute(
                sa_delete(StockDailyStat).where(StockDailyStat.date == today)
            )
            session.bulk_insert_mappings(StockDailyStat, snapshots)
        logger.info("[股票统计] %s: 写入 %d 条", today.isoformat(), len(snapshots))
    except Exception:
        logger.exception("[股票统计] DB写入失败")
        return 0

    return len(snapshots)


def collect_etf_daily_stats(target_date: Optional[date] = None) -> int:
    """采集全市场ETF当日行情快照（成交量），返回写入条数。"""
    import akshare as ak

    today = target_date or date.today()

    logger.info("[ETF统计] 获取全市场ETF行情(东财)...")
    try:
        df = ak.fund_etf_spot_em()
        if df is None or df.empty:
            logger.warning("[ETF统计] fund_etf_spot_em 返回空")
            return 0
        logger.info("[ETF统计] 东财ETF行情: %d 条", len(df))
    except Exception:
        logger.exception("[ETF统计] fund_etf_spot_em 失败")
        return 0

    # 字段映射
    code_col = next((c for c in ['代码', '基金代码'] if c in df.columns), None)
    name_col = next((c for c in ['名称', '基金简称'] if c in df.columns), None)
    vol_col = next((c for c in ['成交量', 'volume'] if c in df.columns), None)
    pct_col = next((c for c in ['涨跌幅', 'pct_chg'] if c in df.columns), None)
    high_col = next((c for c in ['最高', 'high'] if c in df.columns), None)
    low_col = next((c for c in ['最低', 'low'] if c in df.columns), None)
    pre_col = next((c for c in ['昨收', 'pre_close'] if c in df.columns), None)

    if not all([code_col, name_col, vol_col]):
        logger.error("[ETF统计] 列匹配失败: %s", list(df.columns)[:20])
        return 0

    snapshots: list = []
    for _, row in df.iterrows():
        code = str(row.get(code_col, ''))
        name = str(row.get(name_col, ''))
        if not code or not name:
            continue

        try:
            vol = float(row.get(vol_col, 0) or 0)
            pct = float(row.get(pct_col, 0) or 0) if pct_col else 0
            high = float(row.get(high_col, 0) or 0) if high_col else 0
            low = float(row.get(low_col, 0) or 0) if low_col else 0
            pre = float(row.get(pre_col, 0) or 0) if pre_col else 0
        except (ValueError, TypeError):
            continue

        snapshots.append({
            "date": today,
            "stock_code": code,
            "stock_name": name,
            "pct_chg": pct,
            "high": high,
            "low": low,
            "pre_close": pre,
            "volume": vol,
            "security_type": "etf",
            "sector_name": "",
        })

    if not snapshots:
        logger.warning("[ETF统计] 无有效数据")
        return 0

    logger.info("[ETF统计] 有效: %d 条", len(snapshots))

    db = DatabaseManager.get_instance()
    try:
        with db.session_scope() as session:
            session.execute(
                sa_delete(StockDailyStat).where(
                    StockDailyStat.date == today,
                    StockDailyStat.security_type == "etf",
                )
            )
            session.bulk_insert_mappings(StockDailyStat, snapshots)
        logger.info("[ETF统计] %s: 写入 %d 条", today.isoformat(), len(snapshots))
    except Exception:
        logger.exception("[ETF统计] DB写入失败")
        return 0

    return len(snapshots)


# ── Trading date helpers ─────────────────────────────────────────────────────

def _get_trading_dates_before(db, ref_date: date, count: int) -> List[date]:
    """Return up to `count` trading dates on or before ref_date that have data."""
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


# ── Word cloud query ─────────────────────────────────────────────────────────

def get_word_cloud_data(
    target_date: Optional[date] = None,
    window: int = 5,
    stat_type: str = "gain",
) -> Dict:
    """计算词云数据。

    Args:
        target_date: 基准日期，默认最新有数据的交易日
        window: 时间窗口（交易日数）
        stat_type: 'gain'（涨幅>5%）或 'vol'（波动率>5%）

    Returns:
        {date, window, type, qualifyingCount, sectorWords, conceptWords}
    """
    if window not in WINDOWS:
        logger.warning("[股票统计] 无效window=%s，回退为5", window)
        window = 5
    if stat_type not in ("gain", "vol"):
        logger.warning("[股票统计] 无效stat_type=%s，回退为gain", stat_type)
        stat_type = "gain"

    db = DatabaseManager.get_instance()
    S = StockDailyStat

    # Determine base date
    if target_date is None:
        with db.get_session() as session:
            latest = session.execute(
                select(S.date).order_by(desc(S.date)).limit(1)
            ).scalars().first()
            if latest is None:
                return _empty_result("", window, stat_type)
            target_date = latest if isinstance(latest, date) else datetime.strptime(str(latest), "%Y-%m-%d").date()

    trading_dates = _get_trading_dates_before(db, target_date, window)
    if not trading_dates:
        return _empty_result(target_date.isoformat(), window, stat_type)

    # Fetch all rows in window
    try:
        with db.get_session() as session:
            rows = session.execute(
                select(
                    S.stock_code,
                    S.stock_name,
                    S.pct_chg,
                    S.high,
                    S.low,
                    S.pre_close,
                    S.sector_name,
                ).where(S.date.in_(trading_dates))
            ).all()
    except Exception:
        logger.exception("[股票统计] 查询失败")
        return _empty_result(target_date.isoformat(), window, stat_type)

    if not rows:
        return _empty_result(target_date.isoformat(), window, stat_type)

    # Per-stock aggregation
    stock_stats: Dict[str, Dict] = {}  # code → {name, sector, count}
    for r in rows:
        code = r.stock_code
        if code not in stock_stats:
            stock_stats[code] = {
                "name": r.stock_name or "",
                "sector": r.sector_name or "",
                "count": 0,
            }

        if stat_type == "gain":
            if r.pct_chg is not None and r.pct_chg > 5:
                stock_stats[code]["count"] += 1
        else:  # vol
            if (r.high is not None and r.low is not None and
                    r.pre_close is not None and r.pre_close > 0):
                volatility = (r.high - r.low) / r.pre_close
                if volatility > 0.05:
                    stock_stats[code]["count"] += 1

    # Filter stocks with at least 1 occurrence
    qualifying = {c: s for c, s in stock_stats.items() if s["count"] > 0}
    if not qualifying:
        return _empty_result(target_date.isoformat(), window, stat_type)

    # Aggregate sector words
    sector_weight: Dict[str, int] = defaultdict(int)
    for s in qualifying.values():
        if s["sector"]:
            sector_weight[s["sector"]] += s["count"]

    sector_words = sorted(
        [{"text": k, "value": v} for k, v in sector_weight.items()],
        key=lambda x: -x["value"],
    )[:80]

    # Aggregate concept words (batch lookup via concept_service)
    concept_words = _build_concept_words(list(qualifying.keys()), qualifying)

    return {
        "date": target_date.isoformat(),
        "window": window,
        "type": stat_type,
        "qualifying_count": len(qualifying),
        "sector_words": sector_words,
        "concept_words": concept_words,
    }


def _build_concept_words(codes: List[str], stock_stats: Dict) -> List[Dict]:
    """Batch-lookup concepts and aggregate word cloud data."""
    try:
        from src.services.concept_service import get_concept_map_for_stocks
    except ImportError:
        return []

    concept_map = get_concept_map_for_stocks(codes, max_concepts=5)
    if not concept_map:
        return []

    concept_weight: Dict[str, int] = defaultdict(int)
    for code, concepts_str in concept_map.items():
        if not concepts_str:
            continue
        count = stock_stats.get(code, {}).get("count", 1)
        for cname in concepts_str.split("/"):
            cname = cname.strip()
            if cname:
                concept_weight[cname] += count

    return sorted(
        [{"text": k, "value": v} for k, v in concept_weight.items()],
        key=lambda x: -x["value"],
    )[:100]


def _empty_result(date_str: str, window: int, stat_type: str) -> Dict:
    return {
        "date": date_str,
        "window": window,
        "type": stat_type,
        "qualifying_count": 0,
        "sector_words": [],
        "concept_words": [],
    }


# ── Date listing ─────────────────────────────────────────────────────────────

def get_available_dates(days: int = 30) -> List[str]:
    """获取有数据的交易日列表。"""
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
        logger.exception("[股票统计] 日期查询失败")
        return []
