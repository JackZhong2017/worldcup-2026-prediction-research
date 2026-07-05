import { Module } from '@nestjs/common';
import { HealthController } from './health/health.controller.js';
import { ImportsController } from './providers/imports.controller.js';
import { ProvidersController } from './providers/providers.controller.js';
import { FootballDataClient } from './providers/football-data.client.js';
import { PolymarketClient } from './providers/polymarket.client.js';
import { AnalysisController } from './analysis/analysis.controller.js';
import { DatabaseService } from './database.service.js';

@Module({
  controllers: [HealthController, ProvidersController, ImportsController, AnalysisController],
  providers: [FootballDataClient, PolymarketClient, DatabaseService],
})
export class AppModule {}
