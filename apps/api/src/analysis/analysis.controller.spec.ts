import { AnalysisController } from './analysis.controller.js';

describe('prediction admission gate', () => {
  it('does not trust a caller-submitted passing backtest', async () => {
    const database = { evaluationReport: { findUnique: jest.fn() }, predictionRun: { create: jest.fn() } };
    const controller = new AnalysisController(database as never);
    const observations = Array.from({ length: 200 }, () => ({
      distribution: [{ homeGoals: 1, awayGoals: 0, probability: 1 }], homeGoals: 1, awayGoals: 0,
    }));
    const result = await controller.predict({
      teamStrength: { homeAttackXg: 1.4, homeDefenceXgAllowed: 1.1, awayAttackXg: 1.0,
        awayDefenceXgAllowed: 1.3, leagueMeanHomeXg: 1.3, leagueMeanAwayXg: 1.1 },
      marketDistribution: [{ homeGoals: 1, awayGoals: 0, probability: 1 }],
      backtest: { observations, outOfSample: true,
        thresholds: { minSampleSize: 200, maxBrierScore: 1, maxLogLoss: 1, maxCalibrationError: 1 } },
    });
    expect(result.label).toBe('RESEARCH_OUTPUT_NOT_VALIDATED');
    expect(result.confidence).toBeNull();
    expect(result.admission.serverVerified).toBe(false);
  });
});
