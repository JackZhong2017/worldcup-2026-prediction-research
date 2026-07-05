from __future__ import annotations

import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

from .backfill import _score
from .backtest import poisson_grid


def run_experiment(root: Path) -> dict:
    source = json.loads((root / "data/backfill/fused-out-of-sample-report.json").read_text())
    records = source["records"]
    states: dict[str, dict[str, float]] = defaultdict(lambda: {"gf": 0, "ga": 0, "n": 0})
    enriched = []
    for row in records:
        report = json.loads((root / f"data/backfill/reports/fused-{row['event_id']}.json").read_text())
        enriched.append(row | {"base_home_lambda": report["inputs"]["home_lambda"],
                               "base_away_lambda": report["inputs"]["away_lambda"],
                               "home_recent": dict(states[row["home_team"]]),
                               "away_recent": dict(states[row["away_team"]])})
        home, away = states[row["home_team"]], states[row["away_team"]]
        home["gf"] += row["actual"][0]; home["ga"] += row["actual"][1]; home["n"] += 1
        away["gf"] += row["actual"][1]; away["ga"] += row["actual"][0]; away["n"] += 1
    validation_start, test_start = int(len(enriched) * 0.6), int(len(enriched) * 0.8)
    candidates = []
    for strength, weight in itertools.product((2.0, 5.0, 10.0, 20.0), [i / 10 for i in range(11)]):
        adjusted = _adjust(enriched, strength)
        score = _score(adjusted[validation_start:test_start], weight)
        candidates.append({"recent_strength": strength, "statistical_weight": weight,
                           "validation_log_loss": score["log_loss"]})
    selected = min(candidates, key=lambda row: row["validation_log_loss"])
    adjusted = _adjust(enriched, selected["recent_strength"])
    test = adjusted[test_start:]
    report = {"status": "RESEARCH_OUTPUT_NOT_VALIDATED", "experiment": "past-tournament-form-v1",
      "causal_rule": "For each match, recent state contains only earlier resolved matches.",
      "split": source["split"], "selection": {"selected": selected, "candidates": candidates},
      "test": {"market_only": _score(test, 0), "recent_adjusted_statistical_only": _score(test, 1),
               "selected_fusion": _score(test, selected["statistical_weight"])},
      "admission": {"admitted": False, "reason": f"Only {len(test)}/200 untouched test matches."}}
    output = root / "data/backfill/recent-form-experiment.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def _adjust(records: list[dict], strength: float) -> list[dict]:
    result = []
    for row in records:
        home, away = row["home_recent"], row["away_recent"]
        home_attack = (home["gf"] + row["base_home_lambda"] * strength) / (home["n"] + strength)
        home_defence = (home["ga"] + row["base_away_lambda"] * strength) / (home["n"] + strength)
        away_attack = (away["gf"] + row["base_away_lambda"] * strength) / (away["n"] + strength)
        away_defence = (away["ga"] + row["base_home_lambda"] * strength) / (away["n"] + strength)
        statistical = poisson_grid(math.sqrt(home_attack * away_defence),
                                   math.sqrt(away_attack * home_defence))
        result.append(row | {"statistical": statistical})
    return result


def main() -> None:
    report = run_experiment(Path.cwd())
    print(json.dumps({"status": report["status"], "selection": report["selection"]["selected"],
                      "test": report["test"], "admission": report["admission"]}, indent=2))


if __name__ == "__main__":
    main()
