import { Injectable } from '@nestjs/common';
import { getJson } from './http.js';

export interface PolymarketMarket {
  id: string;
  question: string;
  conditionId: string;
  outcomes: string;
  outcomePrices: string;
  clobTokenIds: string;
  liquidityNum?: number;
  volumeNum?: number;
  acceptingOrders?: boolean;
}

export interface PolymarketEvent {
  id: string;
  slug: string;
  title: string;
  startDate?: string;
  endDate: string;
  active: boolean;
  closed: boolean;
  liquidity?: number;
  volume?: number;
  markets: PolymarketMarket[];
}

export interface OrderBookLevel { price: string; size: string }
export interface PolymarketOrderBook {
  market: string;
  asset_id: string;
  timestamp: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  last_trade_price?: string;
}

export interface NormalizedPolymarketOutcome {
  label: string;
  probability: number;
  tokenId: string;
}

@Injectable()
export class PolymarketClient {
  private readonly gammaUrl = process.env.POLYMARKET_GAMMA_BASE_URL ?? 'https://gamma-api.polymarket.com';
  private readonly clobUrl = process.env.POLYMARKET_CLOB_BASE_URL ?? 'https://clob.polymarket.com';

  async listSportsEvents(limit = 20, offset = 0): Promise<PolymarketEvent[]> {
    const url = new URL(`${this.gammaUrl}/events`);
    url.searchParams.set('active', 'true');
    url.searchParams.set('closed', 'false');
    url.searchParams.set('tag_slug', 'sports');
    url.searchParams.set('limit', String(Math.min(Math.max(limit, 1), 100)));
    url.searchParams.set('offset', String(Math.max(offset, 0)));
    return getJson('Polymarket Gamma', url);
  }

  async getEvent(id: string): Promise<PolymarketEvent> {
    return getJson('Polymarket Gamma', new URL(`${this.gammaUrl}/events/${encodeURIComponent(id)}`));
  }

  async getOrderBook(tokenId: string): Promise<PolymarketOrderBook> {
    const url = new URL(`${this.clobUrl}/book`);
    url.searchParams.set('token_id', tokenId);
    return getJson('Polymarket CLOB', url);
  }

  normalizeMarket(market: PolymarketMarket): NormalizedPolymarketOutcome[] {
    const labels = parseStringArray(market.outcomes, 'outcomes');
    const prices = parseStringArray(market.outcomePrices, 'outcomePrices').map(Number);
    const tokenIds = parseStringArray(market.clobTokenIds, 'clobTokenIds');
    if (labels.length !== prices.length || labels.length !== tokenIds.length) {
      throw new Error(`Polymarket market ${market.id} has mismatched outcome arrays`);
    }
    const total = prices.reduce((sum, value) => sum + value, 0);
    if (!Number.isFinite(total) || total <= 0) throw new Error(`Polymarket market ${market.id} has invalid prices`);
    return labels.map((label, index) => ({
      label,
      probability: prices[index]! / total,
      tokenId: tokenIds[index]!,
    }));
  }
}

function parseStringArray(value: string, field: string): string[] {
  const parsed: unknown = JSON.parse(value);
  if (!Array.isArray(parsed) || !parsed.every((item) => typeof item === 'string')) {
    throw new Error(`Polymarket ${field} is not a string array`);
  }
  return parsed;
}
