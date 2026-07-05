import { Controller, Get, Param, ParseIntPipe, Query } from '@nestjs/common';
import { FootballDataClient } from './football-data.client.js';
import { PolymarketClient } from './polymarket.client.js';

@Controller('providers')
export class ProvidersController {
  constructor(
    private readonly footballData: FootballDataClient,
    private readonly polymarket: PolymarketClient,
  ) {}

  @Get('football-data/matches')
  listMatches(
    @Query('dateFrom') dateFrom: string,
    @Query('dateTo') dateTo: string,
    @Query('competitions') competitions?: string,
  ) {
    return this.footballData.listMatches(dateFrom, dateTo, competitions);
  }

  @Get('football-data/matches/:id')
  getMatch(@Param('id', ParseIntPipe) id: number) {
    return this.footballData.getMatch(id);
  }

  @Get('polymarket/events')
  listEvents(@Query('limit') limit?: string, @Query('offset') offset?: string) {
    return this.polymarket.listSportsEvents(Number(limit ?? 20), Number(offset ?? 0));
  }

  @Get('polymarket/events/:id')
  getEvent(@Param('id') id: string) {
    return this.polymarket.getEvent(id);
  }

  @Get('polymarket/orderbook/:tokenId')
  getOrderBook(@Param('tokenId') tokenId: string) {
    return this.polymarket.getOrderBook(tokenId);
  }
}
