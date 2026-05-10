/**
 * Watchlist-related type definitions.
 * Aligned with the new API schema.
 */

// ============ Tag Types ============

export interface TagInfo {
  id: number;
  name: string;
}

// ============ Group Types ============

export interface GroupInfo {
  id: number;
  name: string;
  sortOrder: number;
  stockCount: number;
  isDefault?: boolean;
}

// ============ Item Types ============

export interface ItemInfo {
  tsCode: string;
  name: string;
  industry?: string;
  tags: TagInfo[];
  close?: number;
  changePct?: number;
  totalMv?: number;
  turnoverRate?: number;
}

// ============ Response Types ============

export interface GroupListResp {
  groups: GroupInfo[];
}

export interface ItemListResp {
  items: ItemInfo[];
  total: number;
}

export interface ItemSearchResp {
  items: ItemInfo[];
}

// ============ Request Types ============

export interface GroupCreateReq {
  name: string;
}

export interface GroupUpdateReq {
  id: number;
  name: string;
}

export interface GroupSortReq {
  items: number[];
}

export interface ItemAddReq {
  tsCode: string;
  groupIds: number[];
}

export interface ItemMoveReq {
  tsCode: string;
  fromGroupId: number;
  toGroupId: number;
}

export interface ItemSortReq {
  groupId: number;
  items: { tsCode: string; action: string }[];
}

// ============ Legacy Types (for backward compatibility) ============
// These are kept to minimize breaking changes in other parts of the app

export interface TagItem {
  id: number;
  name: string;
  color: string;
  createdAt?: string;
}

export interface TagCreate {
  name: string;
  color?: string;
}

export interface TagUpdate {
  name?: string;
  color?: string;
}

export interface GroupItem {
  id: number;
  name: string;
  sortOrder: number;
  stockCount: number;
  createdAt?: string;
}

export interface GroupCreate {
  name: string;
  sortOrder?: number;
}

export interface GroupUpdate {
  name?: string;
  sortOrder?: number;
}

export interface StockAdd {
  code: string;
  name?: string;
}

export interface StockListItem {
  code: string;
  name?: string;
  tags: TagItem[];
  group?: GroupItem;
  lastAnalysisAt?: string;
  lastPrediction?: string;
  lastAdvice?: string;
  createdAt?: string;
}

export interface StockListResponse {
  items: StockListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface AnalysisHistoryItem {
  id: number;
  analysisDate?: string;
  analysisTime?: string;
  trendPrediction?: string;
  operationAdvice?: string;
  sentimentScore?: number;
  analysisSummary?: string;
  backtestOutcome?: string;
  directionCorrect?: boolean;
}

export interface AccuracyStats {
  directionAccuracy?: number;
  winCount: number;
  lossCount: number;
  neutralCount: number;
}

export interface StockHistoryResponse {
  items: AnalysisHistoryItem[];
  total: number;
  page: number;
  limit: number;
  accuracyStats?: AccuracyStats;
}

export interface MessageResponse {
  message: string;
}
