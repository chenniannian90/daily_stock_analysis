import apiClient from './index';
import { toCamelCase } from './utils';

export interface WordCloudWord {
  text: string;
  value: number;
}

export interface WordCloudResponse {
  date: string;
  window: number;
  type: string;
  qualifyingCount: number;
  sectorWords: WordCloudWord[];
  conceptWords: WordCloudWord[];
}

export interface DatesResponse {
  dates: string[];
}

export const stockStatApi = {
  getWordCloud: async (date?: string, window = 5, type = 'gain'): Promise<WordCloudResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/stock-stat/wordcloud', {
      params: { date, window, type },
    });
    return toCamelCase<WordCloudResponse>(response.data);
  },

  getDates: async (days = 30): Promise<DatesResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/stock-stat/dates', {
      params: { days },
    });
    return toCamelCase<DatesResponse>(response.data);
  },
};
