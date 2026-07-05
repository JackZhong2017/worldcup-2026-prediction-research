# Sports Prediction Research Platform

A research platform for measuring the calibration and statistical quality of football prediction markets. It treats every match as an observation and does **not** provide betting recommendations, stake sizing, or wagering strategies.

## Repository map

- `apps/web` — Next.js research dashboard
- `apps/api` — NestJS collection, analysis, and reporting API
- `apps/worker` — Python statistical worker
- `packages/domain` — provider-independent domain types
- `packages/database` — Prisma schema and migrations
- `docs` — architecture and research definitions
- `infra` — local PostgreSQL and Redis services

## Local setup

Prerequisites: Node.js 22+, pnpm 10+, Python 3.11+, and Docker.

```bash
cp .env.example .env
# Add a football-data.org API token to .env
docker compose up -d postgres redis
pnpm install
pnpm db:generate
pnpm dev
```

Run the Python worker separately:

```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Research data and validation

The worker can reproduce the current evidence chain:

```bash
cd apps/worker
source .venv/bin/activate
sprp-collect-statsbomb       # event-level xG for 262 international matches
sprp-backtest                # chronological 80/20 statistical baseline test
sprp-optimize                # chronological 60/20/20 parameter selection and test
sprp-collect-polymarket 650891
sprp-fuse-current            # full market/statistical/fused score grids
sprp-settle 537376           # idempotently evaluate after the match is FINISHED
sprp-batch                   # discover, pair, snapshot, and fuse upcoming World Cup score events
sprp-settle-batch            # settle every finished item in the active sample manifest
sprp-backfill                # reconstruct pre-kickoff CLOB distributions for closed events
sprp-recent-experiment       # causal tournament-form fusion experiment
```

Generated artifacts are saved under `data/processed`, `data/snapshots`, and
`data/reports`. Large event-file cache entries are local-only. StatsBomb must be
attributed when research based on its open data is published or shared.

## First milestone

The initial vertical slice is: import one normalized match snapshot, persist its score and 1X2 markets, calculate deterministic entropy/concentration/top-k metrics, store provenance, then expose the result through the API.

See [docs/architecture.md](docs/architecture.md) and [docs/roadmap.md](docs/roadmap.md).

The model output gate and frozen out-of-sample evaluation rules are documented in
[docs/model-validation.md](docs/model-validation.md). Until those gates pass on real
historical data, API output is explicitly labeled `RESEARCH_OUTPUT_NOT_VALIDATED` and
contains no confidence level.

## Data-source smoke test

After starting the API, inspect the public Polymarket sports feed:

```bash
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'
```

List football matches (requires `FOOTBALL_DATA_API_TOKEN`):

```bash
curl 'http://localhost:3001/api/v1/providers/football-data/matches?dateFrom=2026-07-04&dateTo=2026-07-05'
```

Once one match and its corresponding market event have been identified, create a normalized preview. The explicit ID pairing is intentional: cross-provider identity must be reviewed before anything is persisted.

```bash
curl -X POST 'http://localhost:3001/api/v1/imports/preview' \
  -H 'content-type: application/json' \
  -d '{"footballDataMatchId": 123456, "polymarketEventId": "30615"}'
```
