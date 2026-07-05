# Model validation policy

The API has two output states. `RESEARCH_OUTPUT_NOT_VALIDATED` is the default. The label
`MODEL_PREDICTION` and a confidence level are emitted only when an explicitly
out-of-sample backtest passes every configured threshold.

Initial research thresholds (must be frozen before running a test set):

- minimum 200 completed matches;
- multiclass Brier score <= 0.85;
- exact-score log loss <= 3.20;
- expected calibration error <= 0.05.
- fused exact-score log loss at least 0.01 lower than the market-only control.

For Brier Score and Log Loss, admission is evaluated against the upper bound of a
deterministic 2,000-resample bootstrap 95% interval, not the point estimate. Incremental
Log Loss uses paired resampling by match; its upper 95% bound must be at most -0.01.

Calibration uses top-label ECE: each match contributes the probability assigned to its
single most likely exact score and whether that score occurred. Flattening every 0–10
score cell into the calibration sample is prohibited because the many near-zero negative
classes make error appear artificially tiny.

These are admission criteria, not evidence that the thresholds are optimal. Train,
validation, and chronological test windows must never overlap. Model weights and
thresholds may be selected on training/validation data only; the final test window is
evaluated once. Each report stores `isOutOfSample`, the metric version, thresholds,
sample size, calibration bins, and admission decision.

## Distribution construction

1. Save all listed exact-score prices plus the “other score” outcome.
2. Expand “other score” across the unlisted score grid in proportion to the independent
   statistical model, retaining a normalized full grid (default 0–10 goals per team).
3. Build independent Poisson rates from rolling pre-match attack xG, defensive xG
   allowed, league means, and home advantage. Inputs must be timestamped before kickoff.
4. Fuse statistical and market distributions with a logarithmic opinion pool. Its weight
   is frozen before the out-of-sample run.
5. Save market, statistical, and fused cells along with entropy, normalized entropy,
   concentration, and Top-3 Coverage.

Confidence is a description of distribution sharpness. It is available only after the
admission gate passes and must never be presented as certainty that a score will occur.

The API never trusts a backtest embedded in a prediction request. Admission requires the
identifier of a server-stored `FUSED_SCORE_MODEL` evaluation report whose
`isOutOfSample` and `admitted` fields are both true. This prevents callers from fabricating
a passing report or relaxing thresholds at prediction time.

## Current evidence

The historical CLOB reconstruction produced 88 usable 2026 World Cup matches. “Other
score” settlements were recovered from football-data.org's regular-time score field,
including matches later decided in extra time or penalties. The untouched final block has
18 matches. Market-only log loss was 2.443; the independent statistical baseline scored
2.665. Validation selected 0% statistical weight. A causal tournament-form adjustment also
selected 0%. The statistical model therefore failed to show incremental value and remains
a rejected research candidate. No positive statistical weight may be deployed as a
validated model until a later, pre-specified cohort reverses that result and the total
untouched sample reaches 200.
