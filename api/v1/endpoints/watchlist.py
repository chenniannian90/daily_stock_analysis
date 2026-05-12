# -*- coding: utf-8 -*-
"""自选股 API 端点 - 升级版"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.v1.schemas.watchlist import (
    AccuracyStats,
    AnalysisHistoryItem,
    GroupCreate,
    GroupUpdate,
    GroupSort,
    GroupListResp,
    GroupInfo,
    ItemAdd,
    ItemMove,
    ItemSort,
    ItemListResp,
    ItemSearchResp,
    ItemSearchInfo,
    MessageResp,
    StockHistoryResp,
    TagInfo,
    TagItem,
    TagCreate,
    TagUpdate,
    StockTagSet,
    ItemInfo,
)
from src.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])


# ========== 分组接口 ==========

@router.get("/group/list", response_model=GroupListResp, summary="获取分组列表")
def list_groups(db: Session = Depends(get_db)):
    """获取分组列表（含"全部"虚拟分组）"""
    service = WatchlistService(db)
    result = service.list_groups()
    return GroupListResp(groups=[GroupInfo(**g) for g in result['groups']])


@router.post("/group/create", response_model=GroupInfo, summary="创建分组")
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    """创建分组"""
    service = WatchlistService(db)
    try:
        result = service.create_group(data.name)
        return GroupInfo(id=result['id'], name=result['name'], sortOrder=0, stockCount=0, isDefault=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/group/update", response_model=GroupInfo, summary="更新分组")
def update_group(data: GroupUpdate, db: Session = Depends(get_db)):
    """更新分组名称"""
    service = WatchlistService(db)
    result = service.update_group(data.id, data.name)
    if not result:
        raise HTTPException(status_code=404, detail="分组不存在")
    return GroupInfo(id=result['id'], name=result['name'], sortOrder=0, stockCount=0, isDefault=False)


@router.delete("/group/delete", response_model=MessageResp, summary="删除分组")
def delete_group(id: int = Query(..., description="分组ID"), db: Session = Depends(get_db)):
    """删除分组"""
    service = WatchlistService(db)
    if not service.delete_group(id):
        raise HTTPException(status_code=404, detail="分组不存在")
    return MessageResp(message="success")


@router.put("/group/sort", response_model=MessageResp, summary="分组排序")
def sort_groups(data: GroupSort, db: Session = Depends(get_db)):
    """设置分组排序顺序"""
    service = WatchlistService(db)
    service.sort_groups(data.items)
    return MessageResp(message="success")


# ========== 条目接口 ==========

@router.get("/item/list", response_model=ItemListResp, summary="获取条目列表")
def list_items(
    groupId: int = Query(0, description="分组ID，0表示全部"),
    size: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """获取条目列表（含行情数据）"""
    service = WatchlistService(db)
    result = service.list_items(groupId, size, offset)
    items = [ItemInfo(**item) for item in result['items']]
    return ItemListResp(items=items, total=result['total'])


@router.post("/item/add", response_model=MessageResp, summary="添加条目")
def add_item(data: ItemAdd, db: Session = Depends(get_db)):
    """添加条目到分组"""
    service = WatchlistService(db)
    service.add_item(data.tsCode, data.groupIds)
    return MessageResp(message="success")


@router.delete("/item/remove", response_model=MessageResp, summary="删除条目")
def remove_item(
    tsCode: str = Query(..., description="股票代码"),
    groupId: int = Query(0, description="分组ID"),
    db: Session = Depends(get_db),
):
    """从指定分组删除条目"""
    service = WatchlistService(db)
    if not service.remove_item(tsCode, groupId):
        raise HTTPException(status_code=404, detail="条目不存在")
    return MessageResp(message="success")


@router.put("/item/move", response_model=MessageResp, summary="移动条目")
def move_item(data: ItemMove, db: Session = Depends(get_db)):
    """移动条目到其他分组"""
    service = WatchlistService(db)
    service.move_item(data.tsCode, data.fromGroupId, data.toGroupId)
    return MessageResp(message="success")


@router.put("/item/sort", response_model=MessageResp, summary="条目排序")
def sort_items(data: ItemSort, db: Session = Depends(get_db)):
    """条目排序（置顶/置底）"""
    service = WatchlistService(db)
    items = [{'tsCode': item.tsCode, 'action': item.action} for item in data.items]
    service.sort_items(data.groupId, items)
    return MessageResp(message="success")


@router.get("/item/search", response_model=ItemSearchResp, summary="搜索股票")
def search_stocks(
    keyword: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """搜索股票代码/名称"""
    service = WatchlistService(db)
    results = service.search_stocks(keyword, limit)
    items = [ItemSearchInfo(**r) for r in results]
    return ItemSearchResp(items=items)


# ========== 标签接口 ==========

@router.get("/tags", response_model=List[TagItem], summary="获取所有标签")
def list_tags(db: Session = Depends(get_db)):
    """获取用户的所有标签"""
    service = WatchlistService(db)
    result = service.list_tags()
    return [TagItem(**t) for t in result]


@router.post("/tags", response_model=TagItem, summary="创建标签")
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """创建标签"""
    service = WatchlistService(db)
    try:
        result = service.create_tag(data.name, data.color or "#00d4ff")
        return TagItem(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/tags/{tag_id}", response_model=TagItem, summary="更新标签")
def update_tag(tag_id: int, data: TagUpdate, db: Session = Depends(get_db)):
    """更新标签"""
    service = WatchlistService(db)
    try:
        result = service.update_tag(tag_id, data.name, data.color)
        if not result:
            raise HTTPException(status_code=404, detail="标签不存在")
        return TagItem(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tags/{tag_id}", response_model=MessageResp, summary="删除标签")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """删除标签"""
    service = WatchlistService(db)
    if not service.delete_tag(tag_id):
        raise HTTPException(status_code=404, detail="标签不存在")
    return MessageResp(message="success")


@router.get("/stocks/{code}/tags", response_model=List[TagInfo], summary="获取股票标签")
def get_stock_tags(code: str, db: Session = Depends(get_db)):
    """获取某只股票的标签"""
    service = WatchlistService(db)
    return [TagInfo(id=t.id, name=t.name, color=t.color) for t in service.get_stock_tags(code)]


@router.post("/stocks/{code}/tags", response_model=MessageResp, summary="设置股票标签")
def set_stock_tags(code: str, data: StockTagSet, db: Session = Depends(get_db)):
    """设置股票的标签"""
    service = WatchlistService(db)
    try:
        service.set_stock_tags(code, data.tag_ids)
        return MessageResp(message="success")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 分析历史 ==========

@router.get("/stocks/{code}/history", response_model=StockHistoryResp, summary="获取分析历史")
def get_stock_analysis_history(
    code: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取单只股票的历史分析记录和回测统计"""
    service = WatchlistService(db)
    result = service.get_stock_analysis_history(code, page, limit)
    return StockHistoryResp(
        items=[AnalysisHistoryItem(**item) for item in result['items']],
        total=result['total'],
        page=result['page'],
        limit=result['limit'],
        accuracyStats=AccuracyStats(**result['accuracyStats']) if result['accuracyStats'] else None,
    )
