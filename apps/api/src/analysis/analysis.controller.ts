import { Body, Controller, Post } from '@nestjs/common';
import { admissionDecision, evaluateForecasts, type AdmissionThresholds, type ForecastObservation } from './evaluation.js';
import { distributionDiagnostics, expandMarketTail, fuseDistributions, poissonScoreDistribution, type ScoreCell, type TeamStrengthInput } from './prediction.js';
import { DatabaseService } from '../database.service.js';
import { Prisma } from '@sprp/database';

interface PredictRequest {
  matchId?: string;
  teamStrength: TeamStrengthInput;
  marketDistribution: ScoreCell[];
  statisticalWeight?: number;
  backtest?: { observations: ForecastObservation[]; thresholds: AdmissionThresholds; outOfSample: boolean };
  verifiedEvaluationReportId?: string;
}

@Controller('analysis')
export class AnalysisController {
  constructor(private readonly database: DatabaseService) {}

  @Post('predict')
  async predict(@Body() request: PredictRequest) {
    const statistical = poissonScoreDistribution(request.teamStrength);
    const completeMarket = expandMarketTail(request.marketDistribution, statistical);
    const marketDiagnostics = distributionDiagnostics(completeMarket);
    const statisticalDiagnostics = distributionDiagnostics(statistical);
    const fused = fuseDistributions(statistical, completeMarket, request.statisticalWeight ?? 0.5);
    const fusedDiagnostics = distributionDiagnostics(fused);
    const backtestReport = request.backtest ? evaluateForecasts(request.backtest.observations) : null;
    const calculatedAdmission = request.backtest && backtestReport && request.backtest.outOfSample
      ? admissionDecision(backtestReport, request.backtest.thresholds) : null;
    const verifiedReport = request.verifiedEvaluationReportId
      ? await this.database.evaluationReport.findUnique({ where: { id: request.verifiedEvaluationReportId } })
      : null;
    const serverVerified = Boolean(verifiedReport?.isOutOfSample && verifiedReport.admitted
      && verifiedReport.type === 'FUSED_SCORE_MODEL');
    const admission = {
      admitted: serverVerified,
      checks: calculatedAdmission?.checks ?? { submittedBacktest: false },
      serverVerified,
      evaluationReportId: verifiedReport?.id ?? null,
      reason: serverVerified ? null : 'A server-stored, admitted, out-of-sample FUSED_SCORE_MODEL report is required.',
    };
    const ranked = [...fused].sort((a, b) => b.probability - a.probability);
    const output = {
      label: admission.admitted ? 'MODEL_PREDICTION' : 'RESEARCH_OUTPUT_NOT_VALIDATED',
      confidence: admission.admitted ? confidenceLevel(fusedDiagnostics.normalizedEntropy, fusedDiagnostics.concentration) : null,
      admission,
      distributions: { market: completeMarket, statistical, fused },
      diagnostics: { market: marketDiagnostics, statistical: statisticalDiagnostics, fused: fusedDiagnostics },
      top3: ranked.slice(0, 3),
      backtest: backtestReport,
      model: { statistical: 'independent-poisson-v1', fusion: 'log-opinion-pool-v1', statisticalWeight: request.statisticalWeight ?? 0.5 },
    };
    if (!request.matchId) return { ...output, persistedPredictionId: null };
    const prediction = await this.database.predictionRun.create({
      data: {
        matchId: request.matchId,
        observedAt: new Date(),
        modelVersion: 'poisson-log-pool-v1',
        statisticalWeight: request.statisticalWeight ?? 0.5,
        status: admission.admitted ? 'MODEL_PREDICTION' : 'RESEARCH_OUTPUT_NOT_VALIDATED',
        confidence: admission.admitted ? confidenceLevel(fusedDiagnostics.normalizedEntropy, fusedDiagnostics.concentration) : null,
        isOutOfSample: Boolean(request.backtest?.outOfSample),
        diagnostics: output.diagnostics as unknown as Prisma.InputJsonValue,
        admission: admission as unknown as Prisma.InputJsonValue,
        inputs: request.teamStrength as unknown as Prisma.InputJsonValue,
        cells: { create: [
          ...completeMarket.map((cell) => ({ ...cell, source: 'MARKET' })),
          ...statistical.map((cell) => ({ ...cell, source: 'STATISTICAL' })),
          ...fused.map((cell) => ({ ...cell, source: 'FUSED' })),
        ] },
      },
    });
    return { ...output, persistedPredictionId: prediction.id };
  }
}

function confidenceLevel(normalizedEntropyValue: number, concentrationValue: number): 'LOW' | 'MEDIUM' | 'HIGH' {
  if (normalizedEntropyValue <= 0.55 && concentrationValue >= 0.18) return 'HIGH';
  if (normalizedEntropyValue <= 0.75 && concentrationValue >= 0.10) return 'MEDIUM';
  return 'LOW';
}
