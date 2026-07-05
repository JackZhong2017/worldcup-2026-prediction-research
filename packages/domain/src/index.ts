export type Probability = number;

export interface MatchIdentity {
  id: string;
  competition: string;
  kickoffAt: string;
  homeTeam: string;
  awayTeam: string;
}

export interface ScoreProbability {
  homeGoals: number;
  awayGoals: number;
  probability: Probability;
}

export interface WinMarket {
  home: Probability;
  draw: Probability;
  away: Probability;
}

export interface GoalMarket {
  line: number;
  over: Probability;
  under: Probability;
}

export interface BttsMarket {
  yes: Probability;
  no: Probability;
}

export interface LiquiditySnapshot {
  volume: number | null;
  traders: number | null;
  observedAt: string;
}

export interface NormalizedMarketSnapshot {
  match: MatchIdentity;
  provider: string;
  observedAt: string;
  score: ScoreProbability[];
  win: WinMarket | null;
  goals: GoalMarket[];
  btts: BttsMarket | null;
  liquidity: LiquiditySnapshot | null;
  rawPayloadRef: string;
}

export interface DataProvider {
  readonly name: string;
  fetchMatch(externalId: string): Promise<MatchIdentity>;
  fetchScoreMarket(externalId: string): Promise<ScoreProbability[]>;
  fetchWinMarket(externalId: string): Promise<WinMarket | null>;
  fetchGoalMarket(externalId: string): Promise<GoalMarket[]>;
  fetchBttsMarket(externalId: string): Promise<BttsMarket | null>;
  fetchLiquidity(externalId: string): Promise<LiquiditySnapshot | null>;
}

export interface MetricProvenance {
  metricVersion: string;
  inputSnapshotId: string;
  calculatedAt: string;
  parameters: Readonly<Record<string, string | number | boolean>>;
}

export interface MarketAnalysis {
  entropy: number;
  normalizedEntropy: number;
  concentration: number;
  topProbabilities: number[];
  provenance: MetricProvenance;
}
