import type { ScoreCell } from './prediction.js';
import { normalize } from './prediction.js';

export interface ForecastObservation { distribution: ScoreCell[]; homeGoals: number; awayGoals: number }
export interface CalibrationBin { lower: number; upper: number; meanForecast: number; observedRate: number; count: number }
export interface BacktestReport {
  sampleSize: number; brierScore: number; logLoss: number; calibrationError: number; calibration: CalibrationBin[];
}
export interface AdmissionThresholds { minSampleSize: number; maxBrierScore: number; maxLogLoss: number; maxCalibrationError: number }

export function evaluateForecasts(items: readonly ForecastObservation[], bins = 10): BacktestReport {
  if (!items.length) throw new Error('at least one forecast is required');
  const rows: { probability: number; outcome: number }[] = [];
  let brier = 0;
  let logLoss = 0;
  for (const item of items) {
    const distribution = normalize(item.distribution);
    let actualProbability = 0;
    let topIndex = 0;
    distribution.forEach((cell, index) => { if (cell.probability > distribution[topIndex]!.probability) topIndex = index; });
    for (const cell of distribution) {
      const outcome = Number(cell.homeGoals === item.homeGoals && cell.awayGoals === item.awayGoals);
      brier += (cell.probability - outcome) ** 2;
      if (outcome) actualProbability = cell.probability;
    }
    const top = distribution[topIndex]!;
    rows.push({ probability: top.probability,
      outcome: Number(top.homeGoals === item.homeGoals && top.awayGoals === item.awayGoals) });
    logLoss += -Math.log(Math.max(actualProbability, 1e-15));
  }
  const calibration = calibrationCurve(rows, bins);
  const calibrationError = calibration.reduce((sum, bin) =>
    sum + bin.count / rows.length * Math.abs(bin.meanForecast - bin.observedRate), 0);
  return { sampleSize: items.length, brierScore: brier / items.length, logLoss: logLoss / items.length, calibrationError, calibration };
}

export function admissionDecision(report: BacktestReport, thresholds: AdmissionThresholds) {
  const checks = {
    sampleSize: report.sampleSize >= thresholds.minSampleSize,
    brierScore: report.brierScore <= thresholds.maxBrierScore,
    logLoss: report.logLoss <= thresholds.maxLogLoss,
    calibrationError: report.calibrationError <= thresholds.maxCalibrationError,
  };
  return { admitted: Object.values(checks).every(Boolean), checks };
}

function calibrationCurve(rows: readonly { probability: number; outcome: number }[], bins: number): CalibrationBin[] {
  if (!Number.isInteger(bins) || bins < 2) throw new Error('bins must be an integer >= 2');
  return Array.from({ length: bins }, (_, index) => {
    const lower = index / bins;
    const upper = (index + 1) / bins;
    const selected = rows.filter((row) => row.probability >= lower && (index === bins - 1 ? row.probability <= upper : row.probability < upper));
    return selected.length ? {
      lower, upper, count: selected.length,
      meanForecast: selected.reduce((sum, row) => sum + row.probability, 0) / selected.length,
      observedRate: selected.reduce((sum, row) => sum + row.outcome, 0) / selected.length,
    } : { lower, upper, count: 0, meanForecast: 0, observedRate: 0 };
  });
}
