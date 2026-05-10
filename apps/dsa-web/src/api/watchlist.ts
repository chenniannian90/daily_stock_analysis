import apiClient from './index';
import type {
  TagItem,
  TagCreate,
  TagUpdate,
  GroupItem,
  GroupCreate,
  GroupUpdate,
  StockAdd,
  StockListItem,
  StockListResponse,
  StockHistoryResponse,
  MessageResponse,
  // New types
  GroupInfo,
  ItemInfo,
  GroupListResp,
  ItemListResp,
  ItemSearchResp,
} from '../types/watchlist';

const BASE = '/api/v1/watchlist';

export const watchlistApi = {
  // ============ Group Operations (New API) ============

  listGroups: async (): Promise<GroupInfo[]> => {
    const response = await apiClient.get<GroupListResp>(`${BASE}/group/list`);
    return response.data.groups || [];
  },

  createGroup: async (name: string): Promise<void> => {
    await apiClient.post(`${BASE}/group/create`, { name });
  },

  updateGroup: async (id: number, name: string): Promise<void> => {
    await apiClient.put(`${BASE}/group/update`, { id, name });
  },

  deleteGroup: async (id: number): Promise<void> => {
    await apiClient.delete(`${BASE}/group/delete?id=${id}`);
  },

  sortGroups: async (items: number[]): Promise<void> => {
    await apiClient.put(`${BASE}/group/sort`, { items });
  },

  // ============ Item Operations (New API) ============

  listItems: async (groupId: number, size = 20, offset = 0): Promise<{ items: ItemInfo[]; total: number }> => {
    const response = await apiClient.get<ItemListResp>(
      `${BASE}/item/list?groupId=${groupId}&size=${size}&offset=${offset}`
    );
    return {
      items: response.data.items || [],
      total: response.data.total || 0,
    };
  },

  addItem: async (tsCode: string, groupIds: number[]): Promise<void> => {
    await apiClient.post(`${BASE}/item/add`, { tsCode, groupIds });
  },

  removeItem: async (tsCode: string, groupId: number): Promise<void> => {
    await apiClient.delete(`${BASE}/item/remove?tsCode=${tsCode}&groupId=${groupId}`);
  },

  moveItem: async (tsCode: string, fromGroupId: number, toGroupId: number): Promise<void> => {
    await apiClient.put(`${BASE}/item/move`, { tsCode, fromGroupId, toGroupId });
  },

  sortItems: async (groupId: number, items: { tsCode: string; action: string }[]): Promise<void> => {
    await apiClient.put(`${BASE}/item/sort`, { groupId, items });
  },

  searchStocks: async (keyword: string, limit = 10): Promise<ItemSearchResp> => {
    const response = await apiClient.get<ItemSearchResp>(
      `${BASE}/item/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`
    );
    return response.data;
  },

  // ============ Legacy Stock Operations ============

  getStocks: async (params?: {
    groupId?: number;
    tagId?: number;
    page?: number;
    limit?: number;
  }): Promise<StockListResponse> => {
    const query = new URLSearchParams();
    if (params?.groupId) query.set('groupId', String(params.groupId));
    if (params?.tagId) query.set('tagId', String(params.tagId));
    if (params?.page) query.set('page', String(params.page));
    if (params?.limit) query.set('limit', String(params.limit));
    const response = await apiClient.get<StockListResponse>(`${BASE}/stocks?${query}`);
    return response.data;
  },

  addStock: async (data: StockAdd): Promise<StockListItem> => {
    const response = await apiClient.post<StockListItem>(`${BASE}/stocks`, data);
    return response.data;
  },

  deleteStock: async (code: string): Promise<MessageResponse> => {
    const response = await apiClient.delete<MessageResponse>(`${BASE}/stocks/${code}`);
    return response.data;
  },

  getStockHistory: async (code: string, params?: { page?: number; limit?: number }): Promise<StockHistoryResponse> => {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', String(params.page));
    if (params?.limit) query.set('limit', String(params.limit));
    const response = await apiClient.get<StockHistoryResponse>(`${BASE}/stocks/${code}/history?${query}`);
    return response.data;
  },

  setStockTags: async (code: string, tagIds: number[]): Promise<MessageResponse> => {
    const response = await apiClient.post<MessageResponse>(`${BASE}/stocks/${code}/tags`, { tag_ids: tagIds });
    return response.data;
  },

  setStockGroup: async (code: string, groupId: number | null): Promise<MessageResponse> => {
    const response = await apiClient.put<MessageResponse>(`${BASE}/stocks/${code}/group`, { group_id: groupId });
    return response.data;
  },

  // ============ Legacy Tag Operations ============

  getTags: async (): Promise<TagItem[]> => {
    const response = await apiClient.get<TagItem[]>(`${BASE}/tags`);
    return response.data;
  },

  createTag: async (data: TagCreate): Promise<TagItem> => {
    const response = await apiClient.post<TagItem>(`${BASE}/tags`, data);
    return response.data;
  },

  updateTag: async (id: number, data: TagUpdate): Promise<TagItem> => {
    const response = await apiClient.put<TagItem>(`${BASE}/tags/${id}`, data);
    return response.data;
  },

  deleteTag: async (id: number): Promise<MessageResponse> => {
    const response = await apiClient.delete<MessageResponse>(`${BASE}/tags/${id}`);
    return response.data;
  },

  // ============ Legacy Group Operations ============

  getGroups: async (): Promise<GroupItem[]> => {
    const response = await apiClient.get<GroupItem[]>(`${BASE}/groups`);
    return response.data;
  },

  createGroupLegacy: async (data: GroupCreate): Promise<GroupItem> => {
    const response = await apiClient.post<GroupItem>(`${BASE}/groups`, data);
    return response.data;
  },

  updateGroupLegacy: async (id: number, data: GroupUpdate): Promise<GroupItem> => {
    const response = await apiClient.put<GroupItem>(`${BASE}/groups/${id}`, data);
    return response.data;
  },

  deleteGroupLegacy: async (id: number): Promise<MessageResponse> => {
    const response = await apiClient.delete<MessageResponse>(`${BASE}/groups/${id}`);
    return response.data;
  },
};
