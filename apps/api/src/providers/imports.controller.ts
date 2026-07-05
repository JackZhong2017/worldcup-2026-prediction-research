import { Body, Controller, Post } from '@nestjs/common';
import { FootballDataClient } from './football-data.client.js';
import { PolymarketClient } from './polymarket.client.js';

interface PreviewImportRequest {
  footballDataMatchId: number;
  polymarketEventId: string;
}

@Controller('imports')
export class ImportsController {
  constructor(
    private readonly footballData: FootballDataClient,
    private readonly polymarket: PolymarketClient,
  ) {}

  @Post('preview')
  async preview(@Body() request: PreviewImportRequest) {
    if (!Number.isInteger(request.footballDataMatchId) || !request.polymarketEventId) {
      throw new Error('footballDataMatchId and polymarketEventId are required');
    }
    const [match, event] = await Promise.all([
      this.footballData.getMatch(request.footballDataMatchId),
      this.polymarket.getEvent(request.polymarketEventId),
    ]);
    return {
      match: {
        externalId: String(match.id),
        competition: match.competition.name,
        kickoffAt: match.utcDate,
        homeTeam: match.homeTeam.name,
        awayTeam: match.awayTeam.name,
        status: match.status,
        result: match.score.fullTime,
      },
      marketEvent: {
        externalId: event.id,
        title: event.title,
        closesAt: event.endDate,
        liquidity: event.liquidity ?? null,
        volume: event.volume ?? null,
        markets: event.markets.map((market) => ({
          externalId: market.id,
          question: market.question,
          outcomes: this.polymarket.normalizeMarket(market),
          liquidity: market.liquidityNum ?? null,
          volume: market.volumeNum ?? null,
        })),
      },
      linkage: {
        status: 'MANUAL_REVIEW_REQUIRED',
        reason: 'Cross-provider team and event identity must be confirmed before persistence.',
      },
      provenance: {
        collectedAt: new Date().toISOString(),
        sources: ['football-data.org', 'polymarket.com'],
      },
    };
  }
}
