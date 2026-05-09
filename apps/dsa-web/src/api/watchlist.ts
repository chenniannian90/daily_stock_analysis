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
} from '../types/watchlist';

const BASE = '/api/v1/watchlist';

export const watchlistApi = {
  // ============ Stock Operations ============

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

  // ============ Tag Operations ============

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

  // ============ Group Operations ============

  getGroups: async (): Promise<GroupItem[]> => {
    const response = await apiClient.get<GroupItem[]>(`${BASE}/groups`);
    return response.data;
  },

  createGroup: async (data: GroupCreate): Promise<GroupItem> => {
    const response = await apiClient.post<GroupItem>(`${BASE}/groups`, data);
    return response.data;
  },

  updateGroup: async (id: number, data: GroupUpdate): Promise<GroupItem> => {
    const response = await apiClient.put<GroupItem>(`${BASE}/groups/${id}`, data);
    return response.data;
  },

  deleteGroup: async (id: number): Promise<MessageResponse> => {
    const response = await apiClient.delete<MessageResponse>(`${BASE}/groups/${id}`);
    return response.data;
  },
};
