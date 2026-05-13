# -*- coding: utf-8 -*-
"""龙头战法 API schemas。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DragonAnalysisResponse(BaseModel):
    """龙头战法分析结果"""

    date: str = Field(..., description="日期 YYYY-MM-DD")
    run_time: Optional[str] = Field(None, description="运行时间 14:30/17:00")
    board_summary: Optional[Dict[str, Any]] = Field(None, description="板块概况")
    dragon_result: Optional[Dict[str, Any]] = Field(None, description="龙头识别结果")


class DragonDatesResponse(BaseModel):
    """有数据的日期列表"""

    dates: List[str] = Field(default_factory=list)
