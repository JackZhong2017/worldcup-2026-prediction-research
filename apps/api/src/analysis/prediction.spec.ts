import { distributionDiagnostics, expandMarketTail, fuseDistributions, poissonScoreDistribution } from './prediction.js';
import { admissionDecision, evaluateForecasts } from './evaluation.js';

describe('scientific prediction pipeline', () => {
  const strength = {
    homeAttackXg: 1.6, homeDefenceXgAllowed: 1.1,
    awayAttackXg: 1.2, awayDefenceXgAllowed: 1.4,
    leagueMeanHomeXg: 1.5, leagueMeanAwayXg: 1.2, homeAdvantage: 1.05,
  };

  it('creates a complete normalized independent score grid', () => {
    const distribution = poissonScoreDistribution(strength, 8);
    expect(distribution).toHaveLength(81);
    expect(distribution.reduce((sum, cell) => sum + cell.probability, 0)).toBeCloseTo(1, 12);
    expect(distributionDiagnostics(distribution).top3Coverage).toBeGreaterThan(0);
  });

  it('fuses market and statistical distributions without dropping score cells', () => {
    const statistical = poissonScoreDistribution(strength, 4);
    const market = [{ homeGoals: 0, awayGoals: 0, probability: 0.4 }, { homeGoals: 1, awayGoals: 0, probability: 0.6 }];
    const fused = fuseDistributions(statistical, market, 0.5);
    expect(fused).toHaveLength(25);
    expect(fused.reduce((sum, cell) => sum + cell.probability, 0)).toBeCloseTo(1, 12);
  });

  it('allocates the other-score market tail across the complete grid', () => {
    const statistical = poissonScoreDistribution(strength, 4);
    const market = [{ homeGoals: 0, awayGoals: 0, probability: 0.4 }, { homeGoals: -1, awayGoals: -1, probability: 0.6 }];
    const expanded = expandMarketTail(market, statistical);
    expect(expanded).toHaveLength(25);
    expect(expanded.find((cell) => cell.homeGoals === 0 && cell.awayGoals === 0)?.probability).toBeCloseTo(0.4);
    expect(expanded.reduce((sum, cell) => sum + cell.probability, 0)).toBeCloseTo(1);
  });

  it('blocks model labeling until every out-of-sample threshold passes', () => {
    const distribution = [{ homeGoals: 1, awayGoals: 0, probability: 0.8 }, { homeGoals: 0, awayGoals: 0, probability: 0.2 }];
    const report = evaluateForecasts([{ distribution, homeGoals: 1, awayGoals: 0 }], 5);
    expect(report.brierScore).toBeCloseTo(0.08);
    expect(report.logLoss).toBeCloseTo(-Math.log(0.8));
    expect(admissionDecision(report, { minSampleSize: 20, maxBrierScore: 0.2, maxLogLoss: 1, maxCalibrationError: 0.2 }).admitted).toBe(false);
  });
});
