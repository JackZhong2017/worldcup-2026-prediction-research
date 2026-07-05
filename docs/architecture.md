# Architecture

## Data flow

1. Provider adapters acquire pre-kickoff snapshots and preserve the raw payload.
2. Normalizers map provider fields into versioned domain objects.
3. PostgreSQL stores match identity, immutable snapshots, derived metrics, results, and reports.
4. The API calculates lightweight deterministic metrics and dispatches heavier jobs through Redis/BullMQ.
5. The Python worker runs statistical evaluation and pattern experiments.
6. Reports and the dashboard consume stored outputs; they do not recalculate results implicitly.

## Boundaries

- Provider-specific concepts remain inside adapters.
- Domain types contain no transport, database, or UI concerns.
- Every metric records input snapshot, implementation version, parameters, and timestamp.
- Historical market observations are append-only.
- Result corrections are auditable rather than silently overwritten.

## Reproducibility key

An experiment result is identified by dataset snapshot, query definition, code/metric version, parameters, and random seed where applicable.
