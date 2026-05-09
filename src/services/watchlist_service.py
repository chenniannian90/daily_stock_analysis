# -*- coding: utf-8 -*-
"""自选股业务逻辑"""

import logging
from datetime import datetime
from typing import List, Optional

from src.config import get_config
from src.repositories.watchlist_repo import WatchlistRepository
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)


class WatchlistService:
    """自选股业务逻辑"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = WatchlistRepository(db_manager=self.db)

    def get_all_watchlist_codes(self) -> List[str]:
        """获取所有自选股代码"""
        stocks = self.repo.list_stocks(limit=1000)
        return [s.code for s in stocks]

    def run_scheduled_analysis(self, analysis_time: str = "morning") -> dict:
        """
        执行定时分析（遍历所有自选股）

        Args:
            analysis_time: "morning" (11:30) 或 "evening" (19:00)

        Returns:
            统计结果: {total, success, failed, errors}
        """
        from src.core.pipeline import StockAnalysisPipeline

        codes = self.get_all_watchlist_codes()
        total = len(codes)
        success = 0
        failed = 0
        errors = []

        if total == 0:
            logger.info("自选股列表为空，跳过分析")
            return {"total": 0, "success": 0, "failed": 0, "errors": []}

        logger.info(f"开始自选股定时分析 [{analysis_time}]，共 {total} 只股票")

        config = get_config()
        pipeline = StockAnalysisPipeline(config=config)

        for code in codes:
            try:
                logger.info(f"分析自选股: {code}")
                pipeline.run(code)
                self.repo.update_stock_last_analysis(code)
                success += 1
            except Exception as e:
                logger.error(f"分析 {code} 失败: {e}")
                failed += 1
                errors.append({"code": code, "error": str(e)})

        logger.info(f"自选股定时分析完成 [{analysis_time}]: 成功 {success}, 失败 {failed}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors[:10],
        }

    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        判断是否交易日（简单实现：排除周末）

        Note: 实际应接入交易日历 API
        """
        d = date or datetime.now()
        if d.weekday() >= 5:
            return False
        return True
