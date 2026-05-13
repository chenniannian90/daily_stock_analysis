import apiClient from './index';
import { toCamelCase } from './utils';

export interface DragonStock {
  stockCode: string;
  stockName: string;
  boardName: string;
  boardType: string;
  conceptName?: string;
  boardRank: number;
  boardPct: number;
  stockPct: number;
  stockVsBoardAlpha: number;
  boardVsIndexAlpha: number;
  consecutiveBoard: number;
  breakCount: number;
  sealAmount: number;
  turnover: number;
  floatMarketCap?: number;
  levelsPassed3: number;
  levelsPassed4: number;
  dragonScore: number;
  isTrueDragon: boolean;
  isSuperDragon: boolean;
  dragonReason: string;
}

export interface DragonResult {
  dragonStocks: DragonStock[];
  trueDragons: DragonStock[];
  superDragons: DragonStock[];
  crossBoardDragons: DragonStock[];
  consecutiveLeaders: DragonStock[];
  divergenceStocks: Record<string, unknown>[];
  sectors: Record<string, unknown>;
  indices: Record<string, unknown>;
  timestamp: string;
}

export interface BoardSummary {
  industryCount: number;
  conceptCount: number;
  topIndustryName: string;
  topIndustryPct: number;
  topConceptName: string;
  topConceptPct: number;
  strongerThanIndexCount: number;
  marketSentiment: string;
  indices: Record<string, unknown>;
  timestamp: string;
}

export interface DragonAnalysisResponse {
  date: string;
  runTime?: string;
  boardSummary?: BoardSummary;
  dragonResult?: DragonResult;
}

export interface DragonDatesResponse {
  dates: string[];
}

export const dragonStrategyApi = {
  getByDate: async (date: string): Promise<DragonAnalysisResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/dragon-strategy', {
      params: { date },
    });
    return toCamelCase<DragonAnalysisResponse>(response.data);
  },

  getDates: async (days?: number): Promise<DragonDatesResponse> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/dragon-strategy/dates', {
      params: { days: days ?? 30 },
    });
    return toCamelCase<DragonDatesResponse>(response.data);
  },
};
