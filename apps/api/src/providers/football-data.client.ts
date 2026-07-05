import { Injectable } from '@nestjs/common';
import { getJson } from './http.js';

export interface FootballDataMatch {
  id: number;
  utcDate: string;
  status: string;
  competition: { id: number; name: string; code: string | null };
  homeTeam: { id: number; name: string; shortName: string | null };
  awayTeam: { id: number; name: string; shortName: string | null };
  score: {
    winner: string | null;
    fullTime: { home: number | null; away: number | null };
  };
  lastUpdated: string;
}

interface MatchListResponse {
  matches: FootballDataMatch[];
}

@Injectable()
export class FootballDataClient {
  private readonly baseUrl = process.env.FOOTBALL_DATA_BASE_URL ?? 'https://api.football-data.org/v4';

  async getMatch(id: number): Promise<FootballDataMatch> {
    return getJson('football-data.org', new URL(`${this.baseUrl}/matches/${id}`), this.headers());
  }

  async listMatches(dateFrom: string, dateTo: string, competitions?: string): Promise<FootballDataMatch[]> {
    const url = new URL(`${this.baseUrl}/matches`);
    url.searchParams.set('dateFrom', dateFrom);
    url.searchParams.set('dateTo', dateTo);
    if (competitions) url.searchParams.set('competitions', competitions);
    return (await getJson<MatchListResponse>('football-data.org', url, this.headers())).matches;
  }

  private headers(): Record<string, string> {
    const token = process.env.FOOTBALL_DATA_API_TOKEN;
    if (!token) throw new Error('FOOTBALL_DATA_API_TOKEN is required');
    return { 'X-Auth-Token': token };
  }
}
