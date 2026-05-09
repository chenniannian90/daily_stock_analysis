# -*- coding: utf-8 -*-
"""自选股 API 端点"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_database_manager
from api.v1.schemas.watchlist import (
    AnalysisHistoryItem,
    AccuracyStats,
    GroupCreate,
    GroupItem,
    GroupUpdate,
    MessageResponse,
    StockAdd,
    StockGroupUpdate,
    StockHistoryResponse,
    StockListItem,
    StockListResponse,
    StockTagUpdate,
    TagCreate,
    TagItem,
    TagUpdate,
)
from src.repositories.watchlist_repo import WatchlistRepository
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def get_repo(db_manager: DatabaseManager = Depends(get_database_manager)) -> WatchlistRepository:
    return WatchlistRepository(db_manager=db_manager)


# ========== 自选股 ==========

@router.get("/stocks", response_model=StockListResponse, summary="获取自选股列表")
def list_stocks(
    group_id: Optional[int] = Query(None, description="分组ID筛选"),
    tag_id: Optional[int] = Query(None, description="标签ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    repo: WatchlistRepository = Depends(get_repo),
):
    """获取自选股列表，支持按分组/标签筛选"""
    offset = (page - 1) * limit
    stocks = repo.list_stocks(group_id=group_id, tag_id=tag_id, limit=limit, offset=offset)
    total = repo.count_stocks(group_id=group_id, tag_id=tag_id)

    items = []
    for stock in stocks:
        tags = repo.get_stock_tags(stock.code)
        group = repo.get_stock_group(stock.code)

        items.append(StockListItem(
            code=stock.code,
            name=stock.name,
            tags=[TagItem(id=t.id, name=t.name, color=t.color, created_at=t.created_at) for t in tags],
            group=GroupItem(id=group.id, name=group.name, sort_order=group.sort_order, stock_count=0, created_at=group.created_at) if group else None,
            last_analysis_at=stock.last_analysis_at,
            last_prediction=None,
            last_advice=None,
            created_at=stock.created_at,
        ))

    return StockListResponse(items=items, total=total, page=page, limit=limit)


@router.post("/stocks", response_model=StockListItem, summary="添加自选股")
def add_stock(
    request: StockAdd,
    repo: WatchlistRepository = Depends(get_repo),
):
    """添加自选股"""
    try:
        stock = repo.add_stock(code=request.code, name=request.name)
        return StockListItem(
            code=stock.code,
            name=stock.name,
            tags=[],
            group=None,
            last_analysis_at=None,
            last_prediction=None,
            last_advice=None,
            created_at=stock.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/stocks/{code}", response_model=MessageResponse, summary="删除自选股")
def delete_stock(
    code: str,
    repo: WatchlistRepository = Depends(get_repo),
):
    """删除自选股"""
    if not repo.delete_stock(code):
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    return MessageResponse(message=f"股票 {code} 已删除")


@router.get("/stocks/{code}/history", response_model=StockHistoryResponse, summary="获取历史分析记录")
def get_stock_history(
    code: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    repo: WatchlistRepository = Depends(get_repo),
    db_manager: DatabaseManager = Depends(get_database_manager),
):
    """获取单只股票的历史分析记录"""
    from sqlalchemy import select, func
    from src.storage import AnalysisHistory, BacktestResult

    stock = repo.get_stock_by_code(code)
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不在自选股中")

    offset = (page - 1) * limit
    with db_manager.get_session() as session:
        total = session.execute(
            select(func.count(AnalysisHistory.id)).where(AnalysisHistory.code == code)
        ).scalar() or 0

        records = session.execute(
            select(AnalysisHistory)
            .where(AnalysisHistory.code == code)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        items = []
        for r in records:
            backtest = session.execute(
                select(BacktestResult)
                .where(BacktestResult.analysis_history_id == r.id)
                .limit(1)
            ).scalar_one_or_none()

            analysis_time = r.created_at.strftime("%H:%M") if r.created_at else None
            analysis_date = r.created_at.strftime("%Y-%m-%d") if r.created_at else None

            items.append(AnalysisHistoryItem(
                id=r.id,
                analysis_date=analysis_date,
                analysis_time=analysis_time,
                trend_prediction=r.trend_prediction,
                operation_advice=r.operation_advice,
                sentiment_score=r.sentiment_score,
                analysis_summary=r.analysis_summary[:100] + "..." if r.analysis_summary and len(r.analysis_summary) > 100 else r.analysis_summary,
                backtest_outcome=backtest.outcome if backtest else None,
                direction_correct=backtest.direction_correct if backtest else None,
            ))

        completed_backtests = session.execute(
            select(BacktestResult)
            .join(AnalysisHistory, BacktestResult.analysis_history_id == AnalysisHistory.id)
            .where(AnalysisHistory.code == code)
            .where(BacktestResult.eval_status == "completed")
        ).scalars().all()

        if completed_backtests:
            correct = sum(1 for b in completed_backtests if b.direction_correct is True)
            win = sum(1 for b in completed_backtests if b.outcome == "win")
            loss = sum(1 for b in completed_backtests if b.outcome == "loss")
            neutral = sum(1 for b in completed_backtests if b.outcome == "neutral")

            stats = AccuracyStats(
                direction_accuracy=round(correct / len(completed_backtests) * 100, 2) if completed_backtests else None,
                win_count=win,
                loss_count=loss,
                neutral_count=neutral,
            )
        else:
            stats = None

    return StockHistoryResponse(items=items, total=total, page=page, limit=limit, accuracy_stats=stats)


# ========== 标签 ==========

@router.get("/tags", response_model=list[TagItem], summary="获取所有标签")
def list_tags(repo: WatchlistRepository = Depends(get_repo)):
    """获取所有标签"""
    tags = repo.list_tags()
    return [TagItem(id=t.id, name=t.name, color=t.color, created_at=t.created_at) for t in tags]


@router.post("/tags", response_model=TagItem, summary="创建标签")
def create_tag(request: TagCreate, repo: WatchlistRepository = Depends(get_repo)):
    """创建标签"""
    try:
        tag = repo.create_tag(name=request.name, color=request.color)
        return TagItem(id=tag.id, name=tag.name, color=tag.color, created_at=tag.created_at)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/tags/{tag_id}", response_model=TagItem, summary="更新标签")
def update_tag(tag_id: int, request: TagUpdate, repo: WatchlistRepository = Depends(get_repo)):
    """更新标签"""
    tag = repo.update_tag(tag_id, name=request.name, color=request.color)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    return TagItem(id=tag.id, name=tag.name, color=tag.color, created_at=tag.created_at)


@router.delete("/tags/{tag_id}", response_model=MessageResponse, summary="删除标签")
def delete_tag(tag_id: int, repo: WatchlistRepository = Depends(get_repo)):
    """删除标签"""
    if not repo.delete_tag(tag_id):
        raise HTTPException(status_code=404, detail="标签不存在")
    return MessageResponse(message="标签已删除")


@router.post("/stocks/{code}/tags", response_model=MessageResponse, summary="设置股票标签")
def set_stock_tags(code: str, request: StockTagUpdate, repo: WatchlistRepository = Depends(get_repo)):
    """设置股票标签（全量替换）"""
    stock = repo.get_stock_by_code(code)
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    current_tags = repo.get_stock_tags(code)
    current_ids = {t.id for t in current_tags}
    new_ids = set(request.tag_ids)

    for tag in current_tags:
        if tag.id not in new_ids:
            repo.remove_tag_from_stock(code, tag.id)

    for tag_id in request.tag_ids:
        if tag_id not in current_ids:
            repo.add_tag_to_stock(code, tag_id)

    return MessageResponse(message="标签已更新")


# ========== 分组 ==========

@router.get("/groups", response_model=list[GroupItem], summary="获取所有分组")
def list_groups(repo: WatchlistRepository = Depends(get_repo)):
    """获取所有分组（含「全部」虚拟分组）"""
    groups = repo.list_groups()
    total_count = repo.count_stocks()

    items = []
    items.append(GroupItem(id=0, name="全部", sort_order=-1, stock_count=total_count))

    for g in groups:
        count = repo.count_stocks(group_id=g.id)
        items.append(GroupItem(id=g.id, name=g.name, sort_order=g.sort_order, stock_count=count, created_at=g.created_at))

    return items


@router.post("/groups", response_model=GroupItem, summary="创建分组")
def create_group(request: GroupCreate, repo: WatchlistRepository = Depends(get_repo)):
    """创建分组"""
    try:
        group = repo.create_group(name=request.name, sort_order=request.sort_order)
        return GroupItem(id=group.id, name=group.name, sort_order=group.sort_order, stock_count=0, created_at=group.created_at)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/groups/{group_id}", response_model=GroupItem, summary="更新分组")
def update_group(group_id: int, request: GroupUpdate, repo: WatchlistRepository = Depends(get_repo)):
    """更新分组"""
    group = repo.update_group(group_id, name=request.name, sort_order=request.sort_order)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    count = repo.count_stocks(group_id=group.id)
    return GroupItem(id=group.id, name=group.name, sort_order=group.sort_order, stock_count=count, created_at=group.created_at)


@router.delete("/groups/{group_id}", response_model=MessageResponse, summary="删除分组")
def delete_group(group_id: int, repo: WatchlistRepository = Depends(get_repo)):
    """删除分组"""
    if not repo.delete_group(group_id):
        raise HTTPException(status_code=404, detail="分组不存在")
    return MessageResponse(message="分组已删除")


@router.put("/stocks/{code}/group", response_model=MessageResponse, summary="设置股票分组")
def set_stock_group(code: str, request: StockGroupUpdate, repo: WatchlistRepository = Depends(get_repo)):
    """设置股票所属分组"""
    stock = repo.get_stock_by_code(code)
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    if request.group_id is None:
        repo.remove_stock_from_group(code)
    else:
        group = repo.get_group_by_id(request.group_id)
        if not group:
            raise HTTPException(status_code=404, detail="分组不存在")
        repo.set_stock_group(code, request.group_id)

    return MessageResponse(message="分组已更新")
