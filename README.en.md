# World Cup 2026 Prediction Research

[![GitHub stars](https://img.shields.io/github/stars/JackZhong2017/worldcup-2026-prediction-research?style=flat-square)](https://github.com/JackZhong2017/worldcup-2026-prediction-research/stargazers)
[![License](https://img.shields.io/github/license/JackZhong2017/worldcup-2026-prediction-research?style=flat-square)](./LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square)](https://nextjs.org/)
[![NestJS](https://img.shields.io/badge/NestJS-11-E0234E?style=flat-square)](https://nestjs.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square)](https://www.postgresql.org/)

> 🇨🇳 **中文版：[README.md](README.md)** | 🇪🇸 **Español: [README.es.md](README.es.md)**

A research platform for measuring the calibration and statistical quality of football prediction markets, focused on the 2026 World Cup. Every match is treated as an observation. The platform compares market-implied probabilities from Polymarket against statistical models built from StatsBomb event-level xG data, then evaluates whether a fused model can be scientifically validated as predictive.

**No betting recommendations, no staking strategies, no position sizing.** This is a pure research tool — it would rather honestly report that a model was rejected than make unscientific predictions.

---

## Quick Start

```bash
git clone https://github.com/JackZhong2017/worldcup-2026-prediction-research.git
cd worldcup-2026-prediction-research
cp .env.example .env
# Edit .env and add your football-data.org API token
docker compose up -d postgres redis
pnpm install
pnpm db:generate
pnpm dev
```

Verify the API is running:

```bash
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'
```

---

## What It Answers

Not "who will win," but more fundamental questions: **Are prediction markets actually well-calibrated? Can statistical models provide incremental information?**

**Market Quality**
- How accurate are Polymarket exact-score implied probabilities?
- Does the market systematically over- or under-estimate certain outcomes?
- Is the "other score" tail reasonably priced?

**Statistical Model Validation**
- Can an independent xG-based Poisson model beat the market?
- Does logarithmic opinion pool fusion outperform either source alone?
- Strict out-of-sample evaluation with chronological splits — no look-ahead bias

**Reproducible Research**
- Every experiment records its dataset snapshot, code version, parameters, and random seed
- 88 reconstructed pre-kickoff CLOB distributions for 2026 World Cup matches
- All intermediate artifacts (snapshots, reports, evaluations) are fully auditable

---

## Data Sources

| Source | What It Provides |
|---|---|
| **Polymarket** | Real-time exact-score probability snapshots; CLOB batch price history for 88 closed World Cup events |
| **StatsBomb Open Data** | Event-level xG from 262 international matches, extracted into rolling attacking/defensive strength indicators |
| **football-data.org** | Match schedules, live status, final scores — used for cross-provider pairing and post-match settlement |

---

## How It Works

```
Provider Adapters → Normalized Domain Objects → Immutable PostgreSQL Storage → API Deterministic Metrics → Python Statistical Experiments → Report Consumption
                                                        ↑                              ↑
                                                  Polymarket Snapshots          StatsBomb xG Data
```

### Three Core Modules

| Module | Stack | Responsibility |
|---|---|---|
| **API** (`apps/api`) | NestJS 11 | Data collection, normalization, prediction fusion, metric computation |
| **Dashboard** (`apps/web`) | Next.js 15 | Research workbench: match explorer, calibration curves, market quality |
| **Worker** (`apps/worker`) | Python 3.11 | Statistical computation: backtesting, parameter optimization, fusion experiments, CLOB reconstruction |

---

## Scientific Basis

### Logarithmic Opinion Pool Fusion

Market and statistical distributions are combined via a **weighted geometric mean** (logarithmic opinion pool). The geometric mean is chosen over the arithmetic mean because it prevents one source from dominating purely due to numerical scale. The fusion weight is frozen before any out-of-sample evaluation to prevent overfitting.

### Poisson Score Distribution

The statistical model constructs **independent Poisson rates** from pre-kickoff attacking xG, defensive xG conceded, league averages, and home advantage. These generate a full 0–10 goal grid. Polymarket's "other score" tail is expanded across unlisted score cells in proportion to the statistical model.

### Model Validation Gate

The API has two output states. The default is **`RESEARCH_OUTPUT_NOT_VALIDATED`**. Output is upgraded to **`MODEL_PREDICTION`** only when all five thresholds are met on a frozen out-of-sample cohort:

| Threshold | Criterion |
|---|---|
| **① Sample Size** | ≥ 200 completed out-of-sample matches |
| **② Brier Score** | ≤ 0.85 (bootstrap 95% upper bound, 2000 resamples) |
| **③ Log Loss** | ≤ 3.20 (bootstrap 95% upper bound) |
| **④ Calibration Error** | ≤ 0.05 (Top-Label ECE — only the single most likely exact score per match) |
| **⑤ Incremental Log Loss** | ≤ -0.01 (fused vs. market-only, paired bootstrap 95% upper bound) |

All thresholds use **bootstrap 95% confidence upper bounds**, not point estimates — this prevents statistical noise from producing false positives. Train/validation/test windows are strictly chronological and never overlap. The final test window is evaluated exactly once to prevent multiple comparison issues. The API never trusts a backtest embedded in a prediction request — it requires a server-stored evaluation report with `isOutOfSample=true` and `admitted=true`.

### Top-Label Expected Calibration Error

Flattening all 121 score cells (0–10 × 0–10) into a calibration sample makes error appear artificially small due to the many near-zero negative classes. This project uses only the **single most likely exact score per match** for calibration evaluation, providing a more honest assessment of whether the model assigns probability accurately.

---

## Repository Structure

```
├── apps/
│   ├── api/         # NestJS backend API (port 3001)
│   ├── web/         # Next.js research dashboard
│   └── worker/      # Python statistical worker (11 CLI entry points)
├── packages/
│   ├── domain/      # Provider-independent domain types
│   └── database/    # Prisma ORM schema and migrations
├── data/
│   ├── processed/   # StatsBomb international xG data (262 matches)
│   ├── snapshots/   # Polymarket market snapshots
│   ├── reports/     # Fused score reports and statistical baselines
│   ├── backfill/    # 88 WC 2026 CLOB historical reconstructions
│   ├── manifests/   # Active sample manifests
│   └── evaluations/ # Settled observations
├── docs/            # Architecture, roadmap, model validation docs
├── docker-compose.yml
└── pnpm-workspace.yaml
```

---

## Installation

### Prerequisites

- Node.js 22+, pnpm 10+
- Python 3.11+
- Docker (PostgreSQL 16 + Redis 7)

### Full Setup

```bash
# 1. Clone the repository
git clone https://github.com/JackZhong2017/worldcup-2026-prediction-research.git
cd worldcup-2026-prediction-research

# 2. Configure environment
cp .env.example .env
# Edit .env and set FOOTBALL_DATA_API_TOKEN (free registration at football-data.org)

# 3. Start services
docker compose up -d postgres redis

# 4. Install dependencies
pnpm install
pnpm db:generate

# 5. Start development
pnpm dev
```

### Python Worker Setup

```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

---

## Usage Examples

### Explore Market Data

```bash
# List Polymarket sports events
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'

# Query football fixtures (requires API token)
curl 'http://localhost:3001/api/v1/providers/football-data/matches?dateFrom=2026-07-04&dateTo=2026-07-05'

# Get order book for a specific market
curl 'http://localhost:3001/api/v1/providers/polymarket/orderbook/TOKEN_ID'
```

### Cross-Provider Match Pairing

Cross-provider identity (football-data match ↔ Polymarket event) must always be **manually reviewed** before persistence:

```bash
curl -X POST 'http://localhost:3001/api/v1/imports/preview' \
  -H 'content-type: application/json' \
  -d '{"footballDataMatchId": 537376, "polymarketEventId": "650891"}'
```

### Run Statistical Experiments

```bash
cd apps/worker
source .venv/bin/activate

sprp-collect-statsbomb       # Collect xG data from 262 international matches
sprp-backtest                # Chronological 80/20 statistical baseline test
sprp-optimize                # 60/20/20 parameter grid search
sprp-collect-polymarket 650891  # Snapshot a single Polymarket exact-score event
sprp-fuse-current            # Full market/statistical/fused score grids
sprp-settle 537376           # Post-match evaluation (idempotent)
sprp-batch                   # Discover, pair, snapshot, and fuse upcoming events
sprp-settle-batch            # Settle all finished items in the active manifest
sprp-backfill                # Reconstruct pre-kickoff CLOB distributions
sprp-recent-experiment       # Causal tournament-form fusion experiment
```

### Run a Prediction Analysis

```bash
curl -X POST 'http://localhost:3001/api/v1/analysis/predict' \
  -H 'content-type: application/json' \
  -d '{
    "matchId": "537376",
    "homeAttack": 1.2, "homeDefense": 0.8,
    "awayAttack": 0.9, "awayDefense": 1.1,
    "homeAdvantage": 0.3,
    "marketDistribution": [...]
  }'
```

---

## Current Experimental Results

Using 88 settled 2026 World Cup matches with CLOB-reconstructed pre-kickoff distributions:

| Metric | Market Only | Statistical Model |
|---|---|---|
| **Log Loss** | 2.443 ✅ | 2.665 ❌ |
| **Matches** | 88 WC 2026 | 262 international |
| **Validation Outcome** | Baseline | Rejected — 0% statistical weight selected |

> **No model is currently admitted.** The statistical model failed to demonstrate incremental value over the market and remains a rejected research candidate. A larger out-of-sample cohort (≥ 200 matches) is needed for re-evaluation.

See [docs/model-validation.md](docs/model-validation.md) for details.

---

## Architecture Principles

1. **Append-only, immutable** — Market snapshots are never modified; result corrections are auditable
2. **Cross-provider identity isolation** — Match pairing requires mandatory manual review
3. **Metric provenance** — Every metric records its input snapshot, implementation version, parameters, and timestamp
4. **Chronological splits** — No look-ahead bias; train/validation/test windows never overlap
5. **Bootstrap inference** — Calibration error and loss use bootstrap confidence intervals, not point estimates
6. **Single evaluation** — The final out-of-sample window is evaluated exactly once to prevent multiple comparison

See [docs/architecture.md](docs/architecture.md).

---

## Roadmap

- **M0 Foundation** ✅ — Monorepo, local services, domain contract, database schema, metric primitives
- **M1 Single Sample Pipeline** ✅ — Collection, snapshot, fusion, settlement, reporting
- **M2 Historical Evaluation** ✅ — Batch pipeline, CLOB reconstruction, parameter optimization
- **M3 Research Workbench** 🚧 — Custom grouping, regression/Bayesian experiments, chart export, pattern review

Explicitly out of scope: multi-provider coverage (nail one first), real-time trading, betting recommendations.

See [docs/roadmap.md](docs/roadmap.md).

---

## Important Notes

- This project provides **no prediction recommendations** — all output is labeled `RESEARCH_OUTPUT_NOT_VALIDATED` until the model validation gate is passed
- StatsBomb Open Data must be attributed when research based on it is published or shared
- The football-data.org free tier has rate limits (10 requests/minute); batch operations include built-in delays
- All experimental data is for research purposes only and does not constitute investment or trading advice
- The statistical model is **currently not admitted** — no fusion weight may be deployed as validated without passing a later, pre-specified out-of-sample cohort

---

## License

MIT © 2026 JackZhong2017 — Free to use, modify, and distribute commercially with copyright notice preserved.
