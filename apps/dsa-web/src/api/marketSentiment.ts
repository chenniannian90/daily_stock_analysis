import apiClient from './index';
import { toCamelCase } from './utils';

export interface SentimentSnapshot {
  date: string;
  time: string;
  upCount: number;
  downCount: number;
  flatCount: number;
  limitUpCount: number;
  limitDownCount: number;
  totalVolume: number;
  totalAmount: number;
  upMedianPct: number;
  downMedianPct: number;
  upAvgPct: number;
  downAvgPct: number;
  allMedianPct: number;
  allAvgPct: number;
}

export interface DailySentimentResponse {
  date: string;
  snapshots: SentimentSnapshot[];
}

export interface RangeSentimentResponse {
  snapshots: SentimentSnapshot[];
}

export const marketSentimentApi = {
  getByDate: async (date: string): Promise<DailySentimentResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/market-sentiment', {
      params: { date },
    });
    const data = toCamelCase<DailySentimentResponse>(response.data);
    return {
      date: data.date,
      snapshots: (data.snapshots || []).map((s) => toCamelCase<SentimentSnapshot>(s)),
    };
  },

  getRange: async (start: string, end: string): Promise<RangeSentimentResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/market-sentiment/range', {
      params: { start, end },
    });
    const data = toCamelCase<RangeSentimentResponse>(response.data);
    return {
      snapshots: (data.snapshots || []).map((s) => toCamelCase<SentimentSnapshot>(s)),
    };
  },
};
