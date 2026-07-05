export function entropy(probabilities: readonly number[]): number {
  validateDistribution(probabilities);
  return -probabilities.reduce((sum, probability) =>
    probability === 0 ? sum : sum + probability * Math.log2(probability), 0);
}

export function normalizedEntropy(probabilities: readonly number[]): number {
  if (probabilities.length <= 1) return 0;
  return entropy(probabilities) / Math.log2(probabilities.length);
}

export function concentration(probabilities: readonly number[]): number {
  validateDistribution(probabilities);
  return probabilities.reduce((sum, probability) => sum + probability ** 2, 0);
}

export function topKCoverage(probabilities: readonly number[], k: number): number {
  if (!Number.isInteger(k) || k < 1) throw new Error('k must be a positive integer');
  validateDistribution(probabilities);
  return [...probabilities].sort((a, b) => b - a).slice(0, k).reduce((sum, p) => sum + p, 0);
}

function validateDistribution(probabilities: readonly number[]): void {
  if (probabilities.length === 0) throw new Error('distribution must not be empty');
  if (probabilities.some((value) => !Number.isFinite(value) || value < 0 || value > 1)) {
    throw new Error('probabilities must be finite values between 0 and 1');
  }
  const total = probabilities.reduce((sum, value) => sum + value, 0);
  if (Math.abs(total - 1) > 1e-6) throw new Error(`probabilities must sum to 1; received ${total}`);
}
