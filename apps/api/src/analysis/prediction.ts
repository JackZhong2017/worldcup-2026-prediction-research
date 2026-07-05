import { concentration, entropy, normalizedEntropy, topKCoverage } from './metrics.js';

export interface ScoreCell { homeGoals: number; awayGoals: number; probability: number }
export interface TeamStrengthInput {
  homeAttackXg: number;
  homeDefenceXgAllowed: number;
  awayAttackXg: number;
  awayDefenceXgAllowed: number;
  leagueMeanHomeXg: number;
  leagueMeanAwayXg: number;
  homeAdvantage?: number;
}

export interface DistributionDiagnostics {
  entropy: number;
  normalizedEntropy: number;
  concentration: number;
  top3Coverage: number;
}

export function poissonScoreDistribution(input: TeamStrengthInput, maxGoals = 10): ScoreCell[] {
  validatePositiveInput(input);
  if (!Number.isInteger(maxGoals) || maxGoals < 3) throw new Error('maxGoals must be an integer >= 3');
  const homeLambda = input.leagueMeanHomeXg
    * (input.homeAttackXg / input.leagueMeanHomeXg)
    * (input.awayDefenceXgAllowed / input.leagueMeanHomeXg)
    * (input.homeAdvantage ?? 1);
  const awayLambda = input.leagueMeanAwayXg
    * (input.awayAttackXg / input.leagueMeanAwayXg)
    * (input.homeDefenceXgAllowed / input.leagueMeanAwayXg);
  const cells: ScoreCell[] = [];
  for (let h = 0; h <= maxGoals; h += 1) {
    for (let a = 0; a <= maxGoals; a += 1) {
      cells.push({ homeGoals: h, awayGoals: a, probability: poisson(h, homeLambda) * poisson(a, awayLambda) });
    }
  }
  return normalize(cells);
}

export function fuseDistributions(
  statistical: readonly ScoreCell[], market: readonly ScoreCell[], statisticalWeight: number,
): ScoreCell[] {
  if (!(statisticalWeight >= 0 && statisticalWeight <= 1)) throw new Error('statisticalWeight must be in [0, 1]');
  const stats = toMap(statistical);
  const prices = toMap(market);
  const keys = new Set([...stats.keys(), ...prices.keys()]);
  const epsilon = 1e-12;
  const fused = [...keys].map((key) => {
    const [homeGoals, awayGoals] = key.split(':').map(Number);
    // Logarithmic opinion pool prevents one source from dominating on raw scale.
    const probability = Math.pow(stats.get(key) ?? epsilon, statisticalWeight)
      * Math.pow(prices.get(key) ?? epsilon, 1 - statisticalWeight);
    return { homeGoals: homeGoals!, awayGoals: awayGoals!, probability };
  });
  return normalize(fused);
}

export function expandMarketTail(market: readonly ScoreCell[], statistical: readonly ScoreCell[]): ScoreCell[] {
  const normalizedMarket = normalize(market);
  const other = normalizedMarket.find((cell) => cell.homeGoals === -1 && cell.awayGoals === -1)?.probability ?? 0;
  const explicit = new Map(normalizedMarket.filter((cell) => cell.homeGoals >= 0 && cell.awayGoals >= 0)
    .map((cell) => [`${cell.homeGoals}:${cell.awayGoals}`, cell.probability]));
  const missing = normalize(statistical).filter((cell) => !explicit.has(`${cell.homeGoals}:${cell.awayGoals}`));
  const missingMass = missing.reduce((sum, cell) => sum + cell.probability, 0);
  const result = normalize(statistical).map((cell) => {
    const exact = explicit.get(`${cell.homeGoals}:${cell.awayGoals}`);
    return { ...cell, probability: exact ?? (missingMass > 0 ? other * cell.probability / missingMass : 0) };
  });
  return normalize(result);
}

export function distributionDiagnostics(distribution: readonly ScoreCell[]): DistributionDiagnostics {
  const probabilities = normalize(distribution).map((cell) => cell.probability);
  return {
    entropy: entropy(probabilities),
    normalizedEntropy: normalizedEntropy(probabilities),
    concentration: concentration(probabilities),
    top3Coverage: topKCoverage(probabilities, 3),
  };
}

export function parseExactScoreMarkets(markets: readonly { question: string; yesProbability: number }[]): ScoreCell[] {
  const cells = markets.map(({ question, yesProbability }) => {
    const match = question.match(/(?:score[^0-9]*|)(\d+)\s*[-–:]\s*(\d+)/i);
    if (!match && /other|另.*比分|其他/i.test(question)) return { homeGoals: -1, awayGoals: -1, probability: yesProbability };
    if (!match) throw new Error(`Cannot parse exact score from: ${question}`);
    return { homeGoals: Number(match[1]), awayGoals: Number(match[2]), probability: yesProbability };
  });
  return normalize(cells);
}

export function normalize(distribution: readonly ScoreCell[]): ScoreCell[] {
  if (!distribution.length) throw new Error('distribution must not be empty');
  const total = distribution.reduce((sum, cell) => sum + cell.probability, 0);
  if (!Number.isFinite(total) || total <= 0 || distribution.some((cell) => cell.probability < 0)) {
    throw new Error('distribution contains invalid probabilities');
  }
  return distribution.map((cell) => ({ ...cell, probability: cell.probability / total }));
}

function poisson(k: number, lambda: number): number {
  let factorial = 1;
  for (let i = 2; i <= k; i += 1) factorial *= i;
  return Math.exp(-lambda) * lambda ** k / factorial;
}

function toMap(distribution: readonly ScoreCell[]): Map<string, number> {
  return new Map(normalize(distribution).map((cell) => [`${cell.homeGoals}:${cell.awayGoals}`, cell.probability]));
}

function validatePositiveInput(input: TeamStrengthInput): void {
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && (!Number.isFinite(value) || value <= 0)) throw new Error(`${key} must be positive`);
  }
}
