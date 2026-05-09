/**
 * Watchlist-related type definitions.
 * Aligned with the API schema.
 */

// ============ Tag Types ============

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

// ============ Group Types ============

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

// ============ Stock Types ============

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

// ============ History Types ============

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

// ============ Common Types ============

export interface MessageResponse {
  message: string;
}
