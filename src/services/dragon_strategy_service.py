# -*- coding: utf-8 -*-
"""龙头战法数据服务 — 板块排行、龙头识别、涨停板数据采集。

真龙头判定链（由外而内逐层筛选）:
  指数 ──→ 板块（强于指数的板块才是主线板块）
  板块 ──→ 个股（强于板块内其他个股的才是龙头）
  龙头 ──→ 连板高度 + 分歧转一致（禁得起考验的才是真龙头）

数据源: 新浪财经 (money.finance.sina.com.cn / hq.sinajs.cn)
东财接口因网络限制暂不可用，涨停板/连板数据待补充。
"""

import json
import logging
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据采集层
# ---------------------------------------------------------------------------


def _curl_get(url: str, timeout: int = 15) -> Optional[str]:
    """通过 curl 子进程发送 GET 请求（绕过网络层对 Python requests 的拦截）。"""
    try:
        result = subprocess.run(
            ["curl", "-sL", url,
             "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "-H", "Accept: text/html,application/json,*/*",
             "-H", "Referer: https://finance.sina.com.cn/"],
            capture_output=True, timeout=timeout)
        raw = result.stdout
        for enc in ("gb2312", "gbk", "utf-8"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"[curl] 请求失败: {url[:80]} - {e}")
        return None


def _fetch_sector_rankings(indicator: str = "industry") -> List[Dict]:
    """从新浪获取板块排行数据。概念/地域走 akshare 避免编码错位。"""
    if indicator in ("concept", "area"):
        return _fetch_sector_via_akshare(indicator)

    url = "http://money.finance.sina.com.cn/q/view/newFLJK.php?param=industry"
    text = _curl_get(url)
    if not text:
        return _fetch_sector_via_akshare(indicator)

    json_start = text.find("{")
    if json_start < 0:
        return _fetch_sector_via_akshare(indicator)

    try:
        raw_data = json.loads(text[json_start:])
    except json.JSONDecodeError:
        return _fetch_sector_via_akshare(indicator)

    items = []
    for code, val in raw_data.items():
        parts = val.split(",")
        try:
            items.append({
                "board_code": code,
                "name": parts[1],
                "stocks_count": int(parts[2]),
                "avg_price": float(parts[3]),
                "change_pct": float(parts[5]) if len(parts) > 5 else 0.0,
                "total_amount": int(parts[7]) if len(parts) > 7 else 0,
                "rep_stock_code": parts[8] if len(parts) > 8 else "",
                "rep_stock_pct": float(parts[9]) if len(parts) > 9 else 0.0,
                "rep_stock_name": parts[12].rstrip(";") if len(parts) > 12 else "",
            })
        except (ValueError, IndexError) as e:
            logger.debug(f"[板块解析] 跳过 {code}: {e}")

    items.sort(key=lambda x: x["change_pct"], reverse=True)
    return items


def _fetch_sector_via_akshare(indicator: str) -> List[Dict]:
    """通过 akshare 新浪源获取板块排行（兜底）。"""
    try:
        import akshare as ak
        indicator_map = {"industry": "行业", "concept": "概念", "area": "地域"}
        df = ak.stock_sector_spot(indicator=indicator_map.get(indicator, "行业"))
        items = []
        for _, row in df.iterrows():
            items.append({
                "board_code": row.get("label", ""),
                "name": row.get("板块", ""),
                "stocks_count": int(row.get("公司家数", 0)),
                "avg_price": float(row.get("平均价格", 0)),
                "change_pct": float(row.get("涨跌幅", 0)),
                "total_amount": int(float(row.get("总成交额", 0))),
                "rep_stock_code": row.get("股票代码", ""),
                "rep_stock_pct": float(row.get("个股-涨跌幅", 0)),
                "rep_stock_name": row.get("股票名称", ""),
            })
        items.sort(key=lambda x: x["change_pct"], reverse=True)
        return items
    except Exception as e:
        logger.error(f"[akshare 板块排行] 获取失败: {e}")
        return []


# ---------------------------------------------------------------------------
# 指数数据
# ---------------------------------------------------------------------------

# 主要指数代码
MAIN_INDICES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
    "sh000300": "沪深300",
}


def _parse_sina_quote(raw: str) -> Optional[Dict]:
    """解析新浪实时行情数据 var hq_str_XXX="name,open,...,date,time,..." """
    m = re.search(r'"([^"]*)"', raw)
    if not m:
        return None
    fields = m.group(1).split(",")
    if len(fields) < 32:
        return None
    return {
        "name": fields[0],
        "open": float(fields[1]) if fields[1] else 0,
        "close_yesterday": float(fields[2]) if fields[2] else 0,
        "price": float(fields[3]) if fields[3] else 0,
        "high": float(fields[4]) if fields[4] else 0,
        "low": float(fields[5]) if fields[5] else 0,
        "volume": int(fields[8]) if fields[8] else 0,
        "amount": float(fields[9]) if fields[9] else 0,
        "date": fields[30] if len(fields) > 30 else "",
    }


def get_major_indices() -> Dict[str, Dict]:
    """获取主要指数实时行情。

    Returns:
        {"sh000001": {"name": "上证指数", "price": 4192.31, "change_pct": -0.52}, ...}
    """
    codes = ",".join(MAIN_INDICES.keys())
    url = f"https://hq.sinajs.cn/list={codes}"
    text = _curl_get(url)
    if not text:
        return {}

    result = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"var hq_str_(\w+)=", line)
        if not m:
            continue
        code = m.group(1)
        quote = _parse_sina_quote(line)
        if not quote:
            continue

        yesterday = quote["close_yesterday"]
        change_pct = round((quote["price"] - yesterday) / yesterday * 100, 2) if yesterday else 0

        result[code] = {
            "name": MAIN_INDICES.get(code, quote["name"]),
            "price": quote["price"],
            "change_pct": change_pct,
            "high": quote["high"],
            "low": quote["low"],
            "amount": quote["amount"],
        }
    return result


# ---------------------------------------------------------------------------
# 涨停板 & 连板数据（远程服务器可获取完整数据）
# ---------------------------------------------------------------------------


def _fetch_limit_up_pool(trade_date: Optional[str] = None) -> List[Dict]:
    """获取涨停板池（含连板数、封板资金、炸板次数等）。

    数据源: 东财 stock_zt_pool_em，仅远程服务器可用。
    """
    try:
        import akshare as ak
        today = trade_date or datetime.now().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=today)
        items = []
        for _, row in df.iterrows():
            items.append({
                "stock_code": _normalize_em_code(str(row.get("代码", ""))),
                "stock_name": str(row.get("名称", "")),
                "change_pct": float(row.get("涨跌幅", 0)),
                "limit_price": float(row.get("最新价", 0)),
                "turnover": float(row.get("换手率", 0)),
                "seal_amount": float(row.get("封板资金", 0)),
                "first_seal_time": str(row.get("首次封板时间", "")),
                "last_seal_time": str(row.get("最后封板时间", "")),
                "break_count": int(row.get("炸板次数", 0)),
                "consecutive_board": int(row.get("连板数", 0)),
                "board_name": str(row.get("所属行业", "")),
                "limit_stat": str(row.get("涨停统计", "")),
                "float_market_cap": float(row.get("流通市值", 0)),
            })
        return items
    except Exception as e:
        logger.warning(f"[涨停板池] 获取失败: {e}")
        return []


def _normalize_em_code(code: str) -> str:
    """将东财代码格式转为标准格式: 600519 -> sh600519"""
    if not code:
        return ""
    code = code.strip()
    if code.startswith("sh") or code.startswith("sz") or code.startswith("bj"):
        return code
    if code.startswith("6") or code.startswith("5"):
        return f"sh{code}"
    if code.startswith("0") or code.startswith("3") or code.startswith("2"):
        return f"sz{code}"
    if code.startswith("8") or code.startswith("4") or code.startswith("9"):
        return f"bj{code}"
    return code


def get_consecutive_board_leaders(min_boards: int = 2) -> List[Dict]:
    """获取连板龙头——连板数 >= min_boards 的涨停股。

    这是第四层判定的关键数据:
    - 连板高度越高，龙头辨识度越强
    - 结合炸板次数判断是否经历过分歧
    """
    limit_ups = _fetch_limit_up_pool()
    leaders = [s for s in limit_ups if s["consecutive_board"] >= min_boards]
    leaders.sort(key=lambda x: (-x["consecutive_board"], -x["change_pct"]))
    return leaders


def get_divergence_recovery_stocks() -> List[Dict]:
    """获取分歧转一致候选——炸板后回封的涨停股。

    分歧转一致特征:
    - 炸板次数 > 0（盘中出现分歧）
    - 最终封板（在涨停板池中）
    - 换手率较高（筹码充分交换）
    """
    limit_ups = _fetch_limit_up_pool()
    candidates = [
        s for s in limit_ups
        if s["break_count"] > 0 and s["change_pct"] >= 9.9
    ]
    candidates.sort(key=lambda x: (-x["break_count"], -x["turnover"]))
    return candidates


# ---------------------------------------------------------------------------
# 龙头识别 — 三层筛选链
# ---------------------------------------------------------------------------


def identify_dragon_sectors(
    n: int = 5,
    min_sector_pct: float = 0.5,
) -> Dict:
    """第一层：识别龙头板块。

    龙头板块 = 涨幅靠前 + 成交量放大 + 强于指数

    Returns:
        {"industry": [...], "concept": [...], "indices": {...}, "timestamp": "..."}
    """
    indices = get_major_indices()
    industries = _fetch_sector_rankings("industry")
    concepts = _fetch_sector_rankings("concept")

    # 取最强的指数作为基准（通常是当天最强的那个）
    benchmark_pct = max((v["change_pct"] for v in indices.values()), default=0)

    def _enrich(sector_list):
        """标记板块是否强于指数"""
        for s in sector_list:
            s["index_benchmark_pct"] = round(benchmark_pct, 2)
            s["stronger_than_index"] = s["change_pct"] > benchmark_pct
        return [s for s in sector_list if s["change_pct"] >= min_sector_pct]

    return {
        "industry": _enrich(industries[:n]),
        "concept": _enrich(concepts[:n]),
        "indices": indices,
        "benchmark_index_pct": round(benchmark_pct, 2),
        "timestamp": datetime.now().isoformat(),
    }


def identify_dragon_stocks(sector_count: int = 5) -> Dict:
    """识别龙头股 + 真龙头四层判定。

    筛选链条：
      1. 板块强于指数 → 主线板块
      2. 个股强于板块 → 板块龙头
      3. 个股涨停 → 龙头品相
      4. 连板高度 + 分歧转一致 → 真龙头成色

    真龙头 = 四层全过的最高辨识度个股

    Returns:
        {
            "dragon_stocks": [...],           # 全部龙头候选
            "true_dragons": [...],            # 严格真龙头（三层全过）
            "super_dragons": [...],           # 超级龙头（三层+连板高度）
            "consecutive_leaders": [...],     # 连板龙头排行
            "divergence_stocks": [...],       # 分歧转一致候选
            "sectors": {...},
            "indices": {...},
        }
    """
    sectors = identify_dragon_sectors(n=sector_count)
    indices = sectors.get("indices", {})

    # 获取涨停板池数据（第四层数据源）
    limit_up_pool = _fetch_limit_up_pool()
    limit_up_map = {s["stock_code"]: s for s in limit_up_pool}
    logger.info(f"[龙头识别] 涨停板池: {len(limit_up_pool)}只, 可用于连板交叉验证")

    dragon_stocks = []
    true_dragons = []
    super_dragons = []
    seen_stocks = set()

    def _check_dragon_level(
        sector_pct: float, stock_pct: float, board_rank: int,
        is_limit_up: bool, benchmark_pct: float,
        consecutive_board: int = 0, break_count: int = 0,
    ) -> tuple:
        """四层判定:
        level1: 板块强于指数? (sector_pct > benchmark_pct)
        level2: 个股强于板块? (stock_pct > sector_pct)
        level3: 个股涨停? (is_limit_up)
        level4: 连板高度>=2 或 分歧转一致?
        """
        level1 = sector_pct > benchmark_pct
        level2 = stock_pct > sector_pct
        level3 = is_limit_up
        level4 = consecutive_board >= 2 or (break_count > 0 and is_limit_up)

        # 通过层数
        passed = sum([level1, level2, level3])
        passed4 = sum([level1, level2, level3, level4])

        # 龙头评分 0-100
        score = 0
        # 板块地位 (0-20)
        score += max(0, 20 - (board_rank - 1) * 3)
        # 个股相对板块的超额收益 (0-25)
        alpha = stock_pct - sector_pct
        score += min(25, max(0, alpha * 2.5 + 3))
        # 板块相对指数的超额收益 (0-15)
        sector_alpha = sector_pct - benchmark_pct
        score += min(15, max(0, sector_alpha * 3))
        # 涨停龙虎加成 (0-20)
        if is_limit_up:
            score += 20
        elif stock_pct >= 7:
            score += 12
        elif stock_pct >= 5:
            score += 6
        # 连板高度加成 (0-20) — 第四层核心
        if consecutive_board >= 5:
            score += 20
        elif consecutive_board >= 4:
            score += 16
        elif consecutive_board >= 3:
            score += 12
        elif consecutive_board >= 2:
            score += 8
        elif consecutive_board >= 1:
            score += 3

        return min(100, int(score)), passed, passed4, level1, level2, level3, level4

    # 构建 股票代码→概念名 映射（从本地 DB 查询，取最新5个概念）
    code_concept_map: Dict[str, str] = {}
    try:
        from src.services.concept_service import get_concept_map_for_stocks
    except ImportError:
        get_concept_map_for_stocks = None  # type: ignore[assignment]

    for sector_type, sector_list in [("industry", sectors.get("industry", [])),
                                      ("concept", sectors.get("concept", []))]:
        for rank, sector in enumerate(sector_list, 1):
            code = sector.get("rep_stock_code", "")
            name = sector.get("rep_stock_name", "")
            stock_pct = sector.get("rep_stock_pct", 0)
            board_pct = sector["change_pct"]
            benchmark_pct = sector.get("index_benchmark_pct", 0)

            if not code or code in seen_stocks:
                continue
            seen_stocks.add(code)

            # 从涨停板池获取第四层数据
            lu = limit_up_map.get(code, {})
            consecutive_board = lu.get("consecutive_board", 0)
            break_count = lu.get("break_count", 0)
            seal_amount = lu.get("seal_amount", 0)
            turnover = lu.get("turnover", 0)

            is_limit_up = stock_pct >= 9.9 or bool(lu)
            score, passed3, passed4, l1, l2, l3, l4 = _check_dragon_level(
                board_pct, stock_pct, rank, is_limit_up, benchmark_pct,
                consecutive_board, break_count)

            # 理由
            reasons = []
            if l1:
                reasons.append(f"板块强于指数({board_pct:.1f}%>{benchmark_pct:.1f}%)")
            else:
                reasons.append(f"板块弱于指数")
            if l2:
                reasons.append(f"个股强于板块({stock_pct:.1f}%>{board_pct:.1f}%)")
            if l3:
                reasons.append("涨停")
            if l4:
                if consecutive_board >= 2:
                    reasons.append(f"{consecutive_board}连板")
                if break_count > 0 and is_limit_up:
                    reasons.append(f"分歧转一致(炸{break_count}次回封)")
            elif stock_pct >= 5:
                reasons.append("大涨")
            if rank == 1:
                reasons.insert(0, f"{'行业' if sector_type=='industry' else '概念'}龙头")

            entry = {
                "stock_code": code,
                "stock_name": name,
                "board_name": sector["name"],
                "board_type": sector_type,
                "concept_name": "",
                "board_rank": rank,
                "board_pct": round(board_pct, 2),
                "stock_pct": round(stock_pct, 2),
                "stock_vs_board_alpha": round(stock_pct - board_pct, 2),
                "board_vs_index_alpha": round(board_pct - benchmark_pct, 2),
                "consecutive_board": consecutive_board,
                "break_count": break_count,
                "seal_amount": seal_amount,
                "turnover": turnover,
                "float_market_cap": lu.get("float_market_cap", 0),
                "levels_passed_3": passed3,
                "levels_passed_4": passed4,
                "dragon_score": score,
                "is_true_dragon": passed3 >= 3,
                "is_super_dragon": passed3 >= 3 and l4,
                "dragon_reason": " | ".join(reasons),
            }
            dragon_stocks.append(entry)
            if entry["is_true_dragon"]:
                true_dragons.append(entry)
            if entry["is_super_dragon"]:
                super_dragons.append(entry)

    dragon_stocks.sort(key=lambda x: (-x["levels_passed_4"], -x["dragon_score"]))
    true_dragons.sort(key=lambda x: -x["dragon_score"])
    super_dragons.sort(key=lambda x: -x["dragon_score"])

    # 连板龙头排行 (复用已拉取的涨停板池)
    leaders = [s for s in limit_up_pool if s["consecutive_board"] >= 2]
    leaders.sort(key=lambda x: (-x["consecutive_board"], -x["change_pct"]))
    consecutive_leaders = leaders

    # 分歧转一致候选 (复用已拉取的涨停板池)
    divergence_stocks = [
        s for s in limit_up_pool
        if s["break_count"] > 0 and s["change_pct"] >= 9.9
    ]
    divergence_stocks.sort(key=lambda x: (-x["break_count"], -x["turnover"]))

    # 交叉分析：涨停板池中属于领涨板块的连板龙头
    # 板块名模糊匹配——涨停板池用简称("电力")，新浪用全称("电力、热力生产和供应业")
    top_board_names = set()
    sector_pct_map = {}  # 板块名 → 涨跌幅
    for s in sectors.get("industry", []) + sectors.get("concept", []):
        top_board_names.add(s["name"])
        sector_pct_map[s["name"]] = s["change_pct"]

    cross_dragons = []
    for lu in limit_up_pool:
        if lu["consecutive_board"] < 2:
            continue
        if lu["stock_code"] in seen_stocks:
            continue

        # 模糊匹配：涨停板的"所属行业"在任一领涨板块全称中出现
        lu_board = lu["board_name"]
        matched_board_name = None
        matched_board_pct = 0.0
        for board_name in top_board_names:
            if lu_board in board_name or board_name in lu_board:
                matched_board_name = board_name
                matched_board_pct = sector_pct_map.get(board_name, 0.0)
                break
        if not matched_board_name:
            continue

        cross_dragons.append({
            "stock_code": lu["stock_code"],
            "stock_name": lu["stock_name"],
            "board_name": lu["board_name"],
            "board_type": "涨停板交叉",
            "concept_name": "",
            "board_rank": 0,
            "board_pct": round(matched_board_pct, 2),
            "stock_pct": lu["change_pct"],
            "stock_vs_board_alpha": 0.0,
            "board_vs_index_alpha": 0.0,
            "consecutive_board": lu["consecutive_board"],
            "break_count": lu["break_count"],
            "seal_amount": lu["seal_amount"],
            "turnover": lu["turnover"],
            "float_market_cap": lu.get("float_market_cap", 0),
            "levels_passed_3": 0,
            "levels_passed_4": 0,
            "dragon_score": min(100, 40 + lu["consecutive_board"] * 12),
            "is_true_dragon": False,
            "is_super_dragon": True,
            "dragon_reason": f"涨停板交叉发现: {lu['consecutive_board']}连板领涨板块龙头",
        })
        seen_stocks.add(lu["stock_code"])

    # 合并交叉发现的龙头
    all_dragons = dragon_stocks + cross_dragons
    all_dragons.sort(key=lambda x: (-x.get("levels_passed_4", x.get("consecutive_board", 0)),
                                     -x["dragon_score"]))
    super_dragons = [d for d in all_dragons if d.get("is_super_dragon")]

    # 从本地 DB 批量查询概念数据，补充到所有条目
    if get_concept_map_for_stocks:
        all_codes = set()
        for e in all_dragons:
            all_codes.add(e["stock_code"])
        for e in consecutive_leaders:
            all_codes.add(e["stock_code"])
        try:
            code_concept_map = get_concept_map_for_stocks(list(all_codes))
        except Exception:
            logger.warning("[龙头战法] 概念查询失败，使用空映射")
            code_concept_map = {}
        for e in all_dragons:
            e["concept_name"] = code_concept_map.get(e["stock_code"], e.get("concept_name", ""))
        for e in consecutive_leaders:
            e["concept_name"] = code_concept_map.get(e["stock_code"], e.get("concept_name", ""))

    return {
        "dragon_stocks": all_dragons,
        "true_dragons": true_dragons,
        "super_dragons": super_dragons,
        "cross_board_dragons": cross_dragons,
        "consecutive_leaders": consecutive_leaders[:10],
        "divergence_stocks": divergence_stocks[:10],
        "sectors": {
            "top_industry": sectors.get("industry", []),
            "top_concept": sectors.get("concept", []),
        },
        "indices": indices,
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# 自选股 × 龙头板块 交叉分析
# ---------------------------------------------------------------------------


def analyze_watchlist_dragon(watchlist_codes: List[str]) -> Dict:
    """分析自选股中的龙头潜力，与当前龙头板块做交叉匹配。

    Returns:
        {
            "dragon_hits": [...],       # 命中龙头板块代表股的自选股
            "watchlist_total": N,
            "hit_rate": 12.5,
        }
    """
    result = identify_dragon_stocks(sector_count=10)
    dragon_stocks = result["dragon_stocks"]

    # 建立龙头股快速索引
    dragon_map = {d["stock_code"]: d for d in dragon_stocks}

    hits = []
    for code in watchlist_codes:
        if code in dragon_map:
            d = dragon_map[code]
            hits.append({
                "stock_code": code,
                "stock_name": d["stock_name"],
                "board_name": d["board_name"],
                "board_pct": d["board_pct"],
                "stock_pct": d["stock_pct"],
                "dragon_score": d["dragon_score"],
                "is_true_dragon": d["is_true_dragon"],
                "dragon_reason": d["dragon_reason"],
            })

    return {
        "dragon_hits": hits,
        "true_dragon_hits": [h for h in hits if h["is_true_dragon"]],
        "watchlist_total": len(watchlist_codes),
        "hit_rate": round(len(hits) / max(1, len(watchlist_codes)) * 100, 1),
        "timestamp": datetime.now().isoformat(),
    }


def get_board_summary() -> Dict:
    """获取全量板块概况 + 指数概况。"""
    indices = get_major_indices()
    industries = _fetch_sector_rankings("industry")
    concepts = _fetch_sector_rankings("concept")

    top_ind_pct = industries[0]["change_pct"] if industries else 0
    top5_avg = sum(s["change_pct"] for s in industries[:5]) / 5 if len(industries) >= 5 else 0

    if top_ind_pct >= 3 and top5_avg >= 1.5:
        sentiment = "强势"
    elif top_ind_pct <= 0 or top5_avg <= -0.5:
        sentiment = "弱势"
    else:
        sentiment = "正常"

    # 强于指数的板块数
    sh_pct = indices.get("sh000001", {}).get("change_pct", 0)
    strong_sectors = sum(1 for s in industries if s["change_pct"] > sh_pct)

    return {
        "indices": {k: {"name": v["name"], "change_pct": v["change_pct"]}
                     for k, v in indices.items()},
        "industry_count": len(industries),
        "concept_count": len(concepts),
        "top_industry_name": industries[0]["name"] if industries else "",
        "top_industry_pct": round(top_ind_pct, 2),
        "top_concept_name": concepts[0]["name"] if concepts else "",
        "top_concept_pct": round(concepts[0]["change_pct"], 2) if concepts else 0,
        "stronger_than_index_count": strong_sectors,
        "market_sentiment": sentiment,
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# CLI 测试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    print("=" * 60)
    print("龙头战法数据采集测试")
    print("=" * 60)

    # 1. 指数概况
    print("\n--- 1. 主要指数 ---")
    indices = get_major_indices()
    for code, info in indices.items():
        print(f"  {code} {info['name']}: {info['price']:.2f} ({info['change_pct']:+.2f}%)")

    # 2. 板块概况
    print("\n--- 2. 板块概况 ---")
    summary = get_board_summary()
    for k, v in summary.items():
        if k != "indices":
            print(f"  {k}: {v}")

    # 3. 龙头板块
    print("\n--- 3. 龙头板块 (强于指数标记 ★) ---")
    sectors = identify_dragon_sectors(n=5)
    for stype in ["industry", "concept"]:
        slist = sectors.get(stype, [])
        print(f"\n[{stype}] 基准指数涨幅: {sectors.get('benchmark_index_pct', 0)}%")
        for i, s in enumerate(slist, 1):
            star = "★" if s.get("stronger_than_index") else "  "
            print(f"  {star} {i}. {s['name']} 涨幅:{s['change_pct']:.2f}% "
                  f"代表:{s['rep_stock_code']} {s['rep_stock_name']}")

    # 4. 龙头股 (四层筛选)
    print("\n--- 4. 龙头股识别 (四层筛选) ---")
    result = identify_dragon_stocks(sector_count=5)

    # 4a. 连板龙头
    print(f"\n[连板龙头] ({len(result['consecutive_leaders'])}只, 连板≥2)")
    for i, s in enumerate(result["consecutive_leaders"][:8], 1):
        print(f"  {i}. {s['stock_code']} {s['stock_name']} "
              f"{s['consecutive_board']}连板 换手{s['turnover']:.1f}% "
              f"炸板{s['break_count']}次 封板资金{s['seal_amount']/1e8:.1f}亿 "
              f"[{s['sector_name']}]")

    # 4b. 分歧转一致
    print(f"\n[分歧转一致] ({len(result['divergence_stocks'])}只, 炸板后回封)")
    for i, s in enumerate(result["divergence_stocks"][:5], 1):
        print(f"  {i}. {s['stock_code']} {s['stock_name']} "
              f"炸{s['break_count']}次回封 换手{s['turnover']:.1f}% "
              f"连板{s['consecutive_board']}")

    # 4c. 真龙头
    print(f"\n[真龙头] ({len(result['true_dragons'])}只) — 板块强于指数 + 个股强于板块 + 涨停")
    if result["true_dragons"]:
        for i, d in enumerate(result["true_dragons"], 1):
            super_tag = " ★超级龙头" if d.get("is_super_dragon") else ""
            print(f"  {i}. [{d['dragon_score']}分]{super_tag} {d['stock_code']} {d['stock_name']}")
            print(f"     板块:{d['board_name']}({d['board_type']}#{d['board_rank']}) "
                  f"板块{d['board_pct']}% 个股{d['stock_pct']}% "
                  f"连板{d['consecutive_board']} 炸板{d['break_count']}次")
            print(f"     理由: {d['dragon_reason']}")
    else:
        print("  (今日无满足三层全部条件的真龙头)")

    # 4d. 超级龙头
    print(f"\n[超级龙头] ({len(result['super_dragons'])}只) — 真龙头 + 连板/分歧转一致")
    for i, d in enumerate(result["super_dragons"], 1):
        print(f"  {i}. [{d['dragon_score']}分] {d['stock_code']} {d['stock_name']} "
              f"{d['consecutive_board']}连板 | {d['dragon_reason']}")

    print(f"\n[全部候选] ({len(result['dragon_stocks'])}只)")
    for i, d in enumerate(result["dragon_stocks"][:15], 1):
        tag = "★超龙" if d.get("is_super_dragon") else ("★真龙" if d["is_true_dragon"] else f"L{d['levels_passed_3']}")
        print(f"  {i:2d}. [{d['dragon_score']:3d}分][{tag}] {d['stock_code']} {d['stock_name']} "
              f"| {d['board_name']} | 连板{d['consecutive_board']} | {d['dragon_reason']}")
