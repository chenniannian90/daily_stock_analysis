# -*- coding: utf-8 -*-
"""自选股 API 端点 - 升级版"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.v1.schemas.watchlist import (
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
    TagInfo,
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
