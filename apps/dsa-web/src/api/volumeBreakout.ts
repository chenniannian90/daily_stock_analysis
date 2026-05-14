import apiClient from './index';
import { toCamelCase } from './utils';

export interface WordCloudWord {
  text: string;
  value: number;
}

export interface BreakoutStock {
  code: string;
  name: string;
  volume: number;
  yesterdayVolume: number;
  avg3dVolume: number;
  ratioVsYesterday: number;
  ratioVs3dAvg: number;
  sectorName: string;
  conceptNames: string;
}

export interface BreakoutETF {
  code: string;
  name: string;
  volume: number;
  yesterdayVolume: number;
  ratioVsYesterday: number;
}

export interface BreakoutSector {
  name: string;
  aggVolume: number;
  yesterdayAggVolume: number;
  ratio: number;
  constituentCount: number;
}

export interface BreakoutConcept {
  code: string;
  name: string;
  aggVolume: number;
  yesterdayAggVolume: number;
  ratio: number;
  constituentCount: number;
}

export interface BreakoutResponse {
  date: string;
  stockCount: number;
  etfCount: number;
  sectorCount: number;
  conceptCount: number;
  stocks: BreakoutStock[];
  etfs: BreakoutETF[];
  sectors: BreakoutSector[];
  concepts: BreakoutConcept[];
  sectorWords: WordCloudWord[];
  conceptWords: WordCloudWord[];
}

export interface BreakoutDatesResponse {
  dates: string[];
}

export const volumeBreakoutApi = {
  getResults: async (date?: string): Promise<BreakoutResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/volume-breakout/results', {
      params: { date },
    });
    return toCamelCase<BreakoutResponse>(response.data);
  },

  getDates: async (days = 30): Promise<BreakoutDatesResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/volume-breakout/dates', {
      params: { days },
    });
    return toCamelCase<BreakoutDatesResponse>(response.data);
  },
};
