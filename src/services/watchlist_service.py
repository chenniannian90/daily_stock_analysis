# -*- coding: utf-8 -*-
"""自选股业务逻辑 - 升级版"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

from sqlalchemy.orm import Session

from data_provider.base import DataFetcherManager
from src.repositories.watchlist_repo import WatchlistRepository

logger = logging.getLogger(__name__)

# Cache for stocks index
_stocks_index_cache: Optional[List[List]] = None
_stocks_index_cache_time: float = 0


def _load_stocks_index() -> List[List]:
    """Load stocks index from JSON file with cache."""
    global _stocks_index_cache, _stocks_index_cache_time
    import time

    current_time = time.time()
    # Cache for 5 minutes
    if _stocks_index_cache is not None and (current_time - _stocks_index_cache_time) < 300:
        return _stocks_index_cache

    # Try multiple paths
    possible_paths = [
        Path(__file__).parent.parent.parent / "static" / "stocks.index.json",
        Path(__file__).parent.parent.parent / "apps" / "dsa-web" / "public" / "stocks.index.json",
    ]

    for path in possible_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _stocks_index_cache = json.load(f)
                    _stocks_index_cache_time = current_time
                    return _stocks_index_cache
            except Exception as e:
                logger.warning(f"Failed to load stocks index from {path}: {e}")

    logger.warning("Stocks index file not found, returning empty list")
    return []


class WatchlistService:
    """自选股业务逻辑"""

    def __init__(self, session: Session, user_id: str = 'default'):
        self.repo = WatchlistRepository(session, user_id)

    # ========== 分组操作 ==========

    def list_groups(self) -> Dict[str, Any]:
        """获取分组列表"""
        groups = self.repo.list_groups()
        order = self.repo.get_group_order()
        order_map = {gid: i for i, gid in enumerate(order)}

        # 构建"全部"虚拟分组
        all_codes = self.repo.get_all_ts_codes()
        total_count = len(all_codes)

        infos = [{
            'id': 0,
            'name': '全部',
            'sortOrder': 0,
            'stockCount': total_count,
            'isDefault': True,
        }]

        for g in groups:
            count = self.repo.count_items_in_group(g.id)
            infos.append({
                'id': g.id,
                'name': g.name,
                'sortOrder': order_map.get(g.id, 999),
                'stockCount': count,
                'isDefault': False,
            })

        # 按 sortOrder 排序（"全部"始终第一）
        infos[1:] = sorted(infos[1:], key=lambda x: x['sortOrder'])

        return {'groups': infos}

    def create_group(self, name: str) -> Dict[str, Any]:
        """创建分组"""
        group = self.repo.create_group(name)
        return {'id': group.id, 'name': group.name, 'sortOrder': 999, 'stockCount': 0, 'isDefault': False}

    def update_group(self, group_id: int, name: str) -> Optional[Dict[str, Any]]:
        """更新分组"""
        group = self.repo.update_group(group_id, name)
        if group:
            return {'id': group.id, 'name': group.name, 'sortOrder': 999, 'stockCount': 0, 'isDefault': False}
        return None

    def delete_group(self, group_id: int) -> bool:
        """删除分组"""
        return self.repo.delete_group(group_id)

    def sort_groups(self, group_ids: List[int]) -> bool:
        """分组排序"""
        self.repo.set_group_order(group_ids)
        return True

    # ========== 条目操作 ==========

    def list_items(self, group_id: int, size: int = 20, offset: int = 0) -> Dict[str, Any]:
        """获取条目列表（含行情数据）"""
        items, total = self.repo.list_items(group_id, size, offset)

        if not items:
            return {'items': [], 'total': 0}

        # 获取所有代码
        ts_codes = [item.ts_code for item in items]

        # 批量获取名称和行情
        name_map = self._fetch_stock_names(ts_codes)
        quote_map = self._fetch_quotes(ts_codes)
        tag_map = self.repo.get_all_stock_tags(ts_codes)

        # 构建返回数据
        result_items = []
        for item in items:
            info = {
                'tsCode': item.ts_code,
                'name': name_map.get(item.ts_code, item.ts_code),
                'tags': [{'id': t.id, 'name': t.name} for t in tag_map.get(item.ts_code, [])],
            }

            # 添加行情数据
            if item.ts_code in quote_map:
                quote = quote_map[item.ts_code]
                info['close'] = quote.get('close')
                info['changePct'] = quote.get('changePct')
                info['totalMv'] = quote.get('totalMv')
                info['turnoverRate'] = quote.get('turnoverRate')

            result_items.append(info)

        return {'items': result_items, 'total': total}

    def add_item(self, ts_code: str, group_ids: List[int]) -> bool:
        """添加条目"""
        return self.repo.add_item(ts_code, group_ids)

    def remove_item(self, ts_code: str, group_id: int) -> bool:
        """删除条目"""
        return self.repo.remove_item(ts_code, group_id)

    def move_item(self, ts_code: str, from_group_id: int, to_group_id: int) -> bool:
        """移动条目"""
        return self.repo.move_item(ts_code, from_group_id, to_group_id)

    def sort_items(self, group_id: int, items: List[Dict[str, Any]]) -> bool:
        """条目排序"""
        return self.repo.sort_items(group_id, items)

    def search_stocks(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索股票"""
        keyword_lower = keyword.lower()
        results = []

        try:
            stocks_index = _load_stocks_index()
            for entry in stocks_index:
                if len(results) >= limit:
                    break

                # entry format: [ts_code, code, name, pinyin_full, pinyin_abbr, aliases, region, type, is_active, priority]
                if len(entry) < 6:
                    continue

                ts_code = entry[0]
                code = entry[1]
                name = entry[2]
                pinyin_full = entry[3] if len(entry) > 3 else ""
                pinyin_abbr = entry[4] if len(entry) > 4 else ""

                # Search by code, name, or pinyin
                if (keyword_lower in code.lower() or
                    keyword_lower in name.lower() or
                    keyword_lower in pinyin_full.lower() or
                    keyword_lower in pinyin_abbr.lower()):
                    results.append({
                        'tsCode': ts_code,
                        'name': name,
                    })

        except Exception as e:
            logger.error(f"搜索股票失败: {e}")

        return results

    # ========== 标签操作 ==========

    def list_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签"""
        tags = self.repo.list_tags()
        return [{"id": t.id, "name": t.name, "color": t.color, "createdAt": t.created_at.isoformat() if t.created_at else None} for t in tags]

    def create_tag(self, name: str, color: str = "#00d4ff") -> Dict[str, Any]:
        """创建标签"""
        tag = self.repo.create_tag(name, color)
        return {"id": tag.id, "name": tag.name, "color": tag.color, "createdAt": tag.created_at.isoformat() if tag.created_at else None}

    def update_tag(self, tag_id: int, name: Optional[str] = None, color: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """更新标签"""
        tag = self.repo.update_tag(tag_id, name, color)
        if tag:
            return {"id": tag.id, "name": tag.name, "color": tag.color, "createdAt": tag.created_at.isoformat() if tag.created_at else None}
        return None

    def delete_tag(self, tag_id: int) -> bool:
        """删除标签"""
        return self.repo.delete_tag(tag_id)

    def set_stock_tags(self, ts_code: str, tag_ids: List[int]) -> bool:
        """设置股票的标签（替换所有标签）"""
        # 校验请求的 tag ID 都存在
        if tag_ids:
            valid_tags = self.repo.list_tags()
            valid_ids = {t.id for t in valid_tags}
            invalid = set(tag_ids) - valid_ids
            if invalid:
                raise ValueError(f"标签不存在: {sorted(invalid)}")

        existing = self.repo.get_stock_tags(ts_code)
        existing_ids = {t.id for t in existing}
        to_remove = existing_ids - set(tag_ids)
        to_add = set(tag_ids) - existing_ids
        for tid in to_remove:
            self.repo.remove_tag_from_stock(ts_code, tid)
        for tid in to_add:
            self.repo.add_tag_to_stock(ts_code, tid)
        return True

    # ========== 分析历史 ==========

    def get_stock_analysis_history(
        self, code: str, page: int = 1, limit: int = 20
    ) -> Dict[str, Any]:
        """获取单只股票的历史分析记录"""
        from sqlalchemy import func, select as sa_select

        from src.storage import AnalysisHistory, BacktestResult

        offset = (page - 1) * limit

        total = self.repo._session.execute(
            sa_select(func.count(AnalysisHistory.id)).where(AnalysisHistory.code == code)
        ).scalar() or 0

        records = self.repo._session.execute(
            sa_select(AnalysisHistory)
            .where(AnalysisHistory.code == code)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        # 批量查询回测结果，避免 N+1
        record_ids = [r.id for r in records]
        backtest_map = {}
        if record_ids:
            backtests = self.repo._session.execute(
                sa_select(BacktestResult)
                .where(BacktestResult.analysis_history_id.in_(record_ids))
            ).scalars().all()
            for bt in backtests:
                if bt.analysis_history_id not in backtest_map:
                    backtest_map[bt.analysis_history_id] = bt

        items = []
        for r in records:
            backtest = backtest_map.get(r.id)

            analysis_time = r.created_at.strftime("%H:%M") if r.created_at else None
            analysis_date = r.created_at.strftime("%Y-%m-%d") if r.created_at else None

            items.append({
                "id": r.id,
                "analysisDate": analysis_date,
                "analysisTime": analysis_time,
                "trendPrediction": r.trend_prediction,
                "operationAdvice": r.operation_advice,
                "sentimentScore": r.sentiment_score,
                "analysisSummary": (
                    r.analysis_summary[:100] + "..."
                    if r.analysis_summary and len(r.analysis_summary) > 100
                    else r.analysis_summary
                ),
                "backtestOutcome": backtest.outcome if backtest else None,
                "directionCorrect": backtest.direction_correct if backtest else None,
            })

        # 统计准确率
        completed_backtests = self.repo._session.execute(
            sa_select(BacktestResult)
            .join(AnalysisHistory, BacktestResult.analysis_history_id == AnalysisHistory.id)
            .where(AnalysisHistory.code == code)
            .where(BacktestResult.eval_status == "completed")
        ).scalars().all()

        accuracy_stats = None
        if completed_backtests:
            correct = sum(1 for b in completed_backtests if b.direction_correct is True)
            win = sum(1 for b in completed_backtests if b.outcome == "win")
            loss = sum(1 for b in completed_backtests if b.outcome == "loss")
            neutral = sum(1 for b in completed_backtests if b.outcome == "neutral")

            accuracy_stats = {
                "directionAccuracy": round(correct / len(completed_backtests), 4),
                "winCount": win,
                "lossCount": loss,
                "neutralCount": neutral,
            }

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "accuracyStats": accuracy_stats,
        }

    # ========== 私有方法 ==========

    def _fetch_stock_names(self, ts_codes: List[str]) -> Dict[str, str]:
        """批量获取股票名称（优先本地索引）"""
        if not ts_codes:
            return {}
        result = {}
        missing = set(ts_codes)

        # 1. 优先从本地股票索引查（毫秒级，无网络开销）
        try:
            stocks_index = _load_stocks_index()
            for entry in stocks_index:
                if not missing:
                    break
                if len(entry) < 3:
                    continue
                ts_code = entry[0]
                name = entry[2]
                if ts_code in missing and name:
                    result[ts_code] = name
                    missing.discard(ts_code)
        except Exception as e:
            logger.debug(f"本地索引查名称失败: {e}")

        # 2. 本地未命中的再走远程
        if missing:
            try:
                fetcher = DataFetcherManager()
                remote_names = fetcher.batch_get_stock_names(list(missing))
                result.update(remote_names)
            except Exception as e:
                logger.warning(f"远程获取股票名称失败: {e}")

        return result

    def _fetch_quotes(self, ts_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取行情数据（腾讯 HTTP API 一次拉取，~200ms）"""
        result = {}
        if not ts_codes:
            return result

        import urllib.request
        import time as _time

        # 构造腾讯行情 API 批量请求: sh600519,sz000001,...
        symbols = []
        for code in ts_codes:
            code_upper = code.upper()
            if code_upper.endswith('.SH'):
                symbols.append(f'sh{code_upper[:-3]}')
            elif code_upper.endswith('.SZ'):
                symbols.append(f'sz{code_upper[:-3]}')
            else:
                symbols.append(code_upper.lower())

        if not symbols:
            return result

        try:
            url = f"http://qt.gtimg.cn/q={','.join(symbols)}"
            t0 = _time.time()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode('gbk')
            elapsed = _time.time() - t0
            logger.info(f"腾讯行情 API: {len(symbols)} 只, 耗时 {elapsed:.2f}s")

            # 解析腾讯返回格式: var hq_str_sh600519="...";
            for line in raw.strip().split('\n'):
                if '="' not in line:
                    continue
                try:
                    parts = line.split('="', 1)
                    sym = parts[0]
                    # Handle both v_sh600519 and var hq_str_sh600519 formats
                    if 'hq_str_' in sym:
                        sym = sym.split('hq_str_')[1]
                    elif sym.startswith('v_'):
                        sym = sym[2:]
                    data = parts[1].rstrip('";')
                    fields = data.split('~')
                    if len(fields) < 45:
                        continue

                    # 重建 tsCode: sh600519 -> 600519.SH
                    if sym.startswith('sh'):
                        ts_code = sym[2:] + '.SH'
                    elif sym.startswith('sz'):
                        ts_code = sym[2:] + '.SZ'
                    else:
                        ts_code = sym

                    price = float(fields[3]) if fields[3] else None
                    change_pct = float(fields[32]) if fields[32] else None
                    # 总市值：腾讯返回单位亿，转元
                    mv_raw = float(fields[45]) if len(fields) > 45 and fields[45] else None
                    total_mv = mv_raw * 100000000 if mv_raw else None
                    turnover = float(fields[38]) if len(fields) > 38 and fields[38] else None

                    if price is not None and price > 0:
                        result[ts_code] = {
                            'close': price,
                            'changePct': change_pct,
                            'totalMv': total_mv,
                            'turnoverRate': turnover,
                        }
                except (ValueError, IndexError) as e:
                    logger.debug(f"解析腾讯行情 {sym} 失败: {e}")
        except Exception as e:
            logger.warning(f"腾讯行情获取失败: {e}，回退到串行取数")
            from data_provider.base import DataFetcherManager
            fetcher = DataFetcherManager()
            for code in ts_codes:
                try:
                    quote = fetcher.get_realtime_quote(code, log_final_failure=False)
                    if quote and quote.has_basic_data():
                        result[code] = {
                            'close': quote.price,
                            'changePct': quote.change_pct,
                            'totalMv': quote.total_mv,
                            'turnoverRate': quote.turnover_rate,
                        }
                except Exception:
                    pass

        return result
