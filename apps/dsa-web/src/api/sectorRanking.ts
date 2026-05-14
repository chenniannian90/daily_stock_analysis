import apiClient from './index';
import { toCamelCase } from './utils';

export interface SectorRankingItem {
  rank: number;
  sectorCode: string;
  sectorName: string;
  changePct: number;
  netCapitalFlow: number;
  limitUpCount: number;
  window: number;
  date: string;
}

export interface SectorRankingResponse {
  date: string;
  sectorType: string;
  window: number;
  sortBy: string;
  items: SectorRankingItem[];
}

export interface SectorRankingDatesResponse {
  dates: string[];
}

export const sectorRankingApi = {
  getRankings: async (params: {
    date?: string;
    sectorType?: string;
    window?: number;
    sortBy?: string;
    limit?: number;
  }): Promise<SectorRankingResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/sector-rankings', { params });
    return toCamelCase<SectorRankingResponse>(response.data);
  },

  getDates: async (sectorType: string = 'industry', days: number = 30): Promise<string[]> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/sector-rankings/dates', {
      params: { sectorType, days },
    });
    return toCamelCase<SectorRankingDatesResponse>(response.data).dates || [];
  },
};
