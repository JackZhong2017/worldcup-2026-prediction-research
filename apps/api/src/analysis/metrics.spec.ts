import { concentration, entropy, normalizedEntropy, topKCoverage } from './metrics.js';

describe('market quality metrics', () => {
  const distribution = [0.5, 0.3, 0.2];

  it('calculates entropy and normalized entropy', () => {
    expect(entropy(distribution)).toBeCloseTo(1.485475, 6);
    expect(normalizedEntropy(distribution)).toBeCloseTo(0.937231, 6);
  });

  it('calculates concentration and top-k coverage', () => {
    expect(concentration(distribution)).toBeCloseTo(0.38, 10);
    expect(topKCoverage(distribution, 2)).toBeCloseTo(0.8, 10);
  });

  it('rejects invalid probability distributions', () => {
    expect(() => entropy([0.4, 0.4])).toThrow('probabilities must sum to 1');
    expect(() => concentration([])).toThrow('distribution must not be empty');
    expect(() => topKCoverage(distribution, 0)).toThrow('k must be a positive integer');
  });
});
