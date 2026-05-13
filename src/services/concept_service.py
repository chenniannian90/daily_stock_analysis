# -*- coding: utf-8 -*-
"""同花顺概念数据服务 — 从 tushare 拉取概念成分股，存储到本地数据库。"""

import logging
import os
import re
import time
from typing import Dict, List

from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

# 每只股票最多保留的概念数（按概念代码倒序，取最新的）
MAX_CONCEPTS_PER_STOCK = 5

# 智能过滤：匹配以下模式的概念为"非真正投资概念"，自动排除
# 涵盖：通道/标的标签、指数成份、机构持仓、技术筛选、财务分类、规模标签
_EXCLUDE_CONCEPT_PATTERNS = [
    "通$", "标的", "成份", "成指", "综指",
    "MSCI", "罗素", "道琼斯",
    "重仓", "持股", "增持", "减持",
    "融资融券", "转融券",
    "昨日", "近期新", "连续",
    "市盈率", "市净率", "股息率", "破净",
    "含H", "含B", "含可转债",
    "盘股$", "价股$",
    "预增", "预减", "预亏",
    "养老金", "证金", "汇金",
]


def _ts_code_to_standard(ts_code: str) -> str:
    """tushare 代码格式 → 项目标准格式: 000859.SZ → sz000859"""
    if not ts_code:
        return ""
    parts = ts_code.split(".")
    if len(parts) == 2:
        return f"{parts[1].lower()}{parts[0]}"
    return ts_code.lower()


def fetch_and_store_concepts() -> bool:
    """从 tushare 拉取全量概念成分股数据并存入本地 DB。

    全量约 879 个概念、2 万+ 行数据，耗时约 5 分钟。
    """
    try:
        import tushare as ts
    except ImportError:
        logger.error("[概念服务] tushare 未安装")
        return False

    token = os.getenv('TUSHARE_TOKEN', '')
    if not token:
        logger.error("[概念服务] TUSHARE_TOKEN 未配置")
        return False

    try:
        ts.set_token(token)
        pro = ts.pro_api()
    except Exception:
        logger.exception("[概念服务] tushare 初始化失败")
        return False

    # 1. 获取全部概念列表
    try:
        concepts_df = pro.concept(src='ts')
        logger.info("[概念服务] 获取到 %d 个概念", len(concepts_df))
    except Exception:
        logger.exception("[概念服务] 获取概念列表失败")
        return False

    concept_codes = concepts_df['code'].tolist()
    concept_names = dict(zip(concepts_df['code'], concepts_df['name']))

    # 2. 清空旧数据
    db = DatabaseManager.get_instance()
    try:
        with db.session_scope() as session:
            from src.storage import ConceptStockMapping
            session.query(ConceptStockMapping).delete()
            session.flush()
        logger.info("[概念服务] 已清空旧概念数据")
    except Exception:
        logger.exception("[概念服务] 清空旧数据失败")
        return False

    # 3. 逐个概念拉取成分股
    total_rows = 0
    batch: list = []
    call_count = 0

    for i, code in enumerate(concept_codes):
        try:
            detail_df = pro.concept_detail(id=code)
            call_count += 1

            cname = concept_names.get(code, code)
            for _, row in detail_df.iterrows():
                batch.append({
                    "concept_code": code,
                    "concept_name": cname,
                    "stock_code": _ts_code_to_standard(str(row.get("ts_code", ""))),
                    "stock_name": str(row.get("name", "")),
                })
        except Exception:
            logger.debug("[概念服务] 概念 %s 拉取失败，跳过", code)
            continue

        # 每 50 个概念 flush 一次
        if (i + 1) % 50 == 0:
            _flush_batch(batch)
            total_rows += len(batch)
            batch = []
            logger.info(
                "[概念服务] 进度 %d/%d，已写入 %d 行",
                i + 1, len(concept_codes), total_rows,
            )

        # 限速：每 10 次调用 sleep 0.5s，避免触发 tushare 限流
        if call_count % 10 == 0:
            time.sleep(0.5)

    # 4. 刷剩余数据
    if batch:
        _flush_batch(batch)
        total_rows += len(batch)

    logger.info("[概念服务] 完成: %d 个概念, %d 行数据", len(concept_codes), total_rows)
    return True


def _flush_batch(batch: list) -> None:
    """将批次数据写入 DB。"""
    if not batch:
        return
    db = DatabaseManager.get_instance()
    try:
        with db.session_scope() as session:
            from src.storage import ConceptStockMapping
            session.add_all([ConceptStockMapping(**item) for item in batch])
    except Exception:
        logger.exception("[概念服务] 批次写入失败")


_FILTER_RE = re.compile("|".join(_EXCLUDE_CONCEPT_PATTERNS)) if _EXCLUDE_CONCEPT_PATTERNS else None


def get_concepts_for_stock(stock_code: str, max_concepts: int = MAX_CONCEPTS_PER_STOCK) -> List[str]:
    """获取某只股票的概念列表（最新的排在前面，自动过滤无意义概念）。"""
    from sqlalchemy import select, desc
    db = DatabaseManager.get_instance()
    try:
        with db.get_session() as session:
            from src.storage import ConceptStockMapping
            # 多查一些，补偿过滤掉的无效概念
            rows = session.execute(
                select(ConceptStockMapping.concept_name)
                .where(ConceptStockMapping.stock_code == stock_code)
                .order_by(desc(ConceptStockMapping.concept_code))
                .limit(max_concepts + 15)
            ).scalars().all()
            filtered: List[str] = []
            for name in rows:
                if name and (not _FILTER_RE or not _FILTER_RE.search(name)):
                    filtered.append(name)
                if len(filtered) >= max_concepts:
                    break
            return filtered
    except Exception:
        logger.debug("[概念服务] 查询 %s 概念失败", stock_code)
        return []


def get_concept_map_for_stocks(stock_codes: List[str], max_concepts: int = MAX_CONCEPTS_PER_STOCK) -> Dict[str, str]:
    """批量查询多只股票的概念，返回 {stock_code: "概念1/概念2/..."}。"""
    if not stock_codes:
        return {}
    from sqlalchemy import select, desc
    db = DatabaseManager.get_instance()
    try:
        with db.get_session() as session:
            from src.storage import ConceptStockMapping
            # 一次性查出所有 stock_codes 的概念，按概念代码降序
            rows = session.execute(
                select(
                    ConceptStockMapping.stock_code,
                    ConceptStockMapping.concept_name,
                )
                .where(ConceptStockMapping.stock_code.in_(stock_codes))
                .order_by(ConceptStockMapping.stock_code, desc(ConceptStockMapping.concept_code))
            ).all()
    except Exception:
        logger.debug("[概念服务] 批量查询概念失败")
        return {}

    # 按 stock_code 分组，应用过滤 + 截断
    result: Dict[str, list] = {}
    for stock_code, concept_name in rows:
        if stock_code not in result:
            result[stock_code] = []
        if len(result[stock_code]) >= max_concepts:
            continue
        if concept_name and (not _FILTER_RE or not _FILTER_RE.search(concept_name)):
            result[stock_code].append(concept_name)

    return {k: "/".join(v) for k, v in result.items()}
