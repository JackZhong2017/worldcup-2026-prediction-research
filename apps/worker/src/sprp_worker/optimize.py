from __future__ import annotations

import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from .backtest import poisson_grid
from .metrics import brier_score, log_loss, top_label_calibration_curve


def optimize(input_path: Path, output_path: Path) -> dict:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    matches = sorted(source["matches"], key=lambda row: (row["kickoff_at"], row["match_id"]))
    validation_start, test_start = int(len(matches) * 0.6), int(len(matches) * 0.8)
    candidates = []
    for strength, xg_weight, home_factor in itertools.product(
        (2.0, 5.0, 10.0), (0.5, 0.75, 1.0), (0.9, 1.0, 1.1)
    ):
        forecasts = _forecast(matches, strength, xg_weight, home_factor)
        validation = forecasts[validation_start:test_start]
        candidates.append({"prior_strength": strength, "xg_weight": xg_weight,
          "home_factor": home_factor, "validation_log_loss": _mean_log_loss(validation)})
    candidates.sort(key=lambda row: row["validation_log_loss"])
    selected = candidates[0]
    forecasts = _forecast(matches, selected["prior_strength"], selected["xg_weight"], selected["home_factor"])
    test = forecasts[test_start:]
    probabilities = [row["distribution"] for row in test]
    outcomes = [row["outcome_index"] for row in test]
    curve = top_label_calibration_curve(probabilities, outcomes)
    ece = sum(row["count"] * abs(row["mean_forecast"] - row["observed_rate"]) for row in curve)
    ece /= sum(row["count"] for row in curve)
    report = {
      "status": "RESEARCH_OUTPUT_NOT_VALIDATED", "model": "tuned-xg-goals-poisson-v2",
      "source": source["provenance"],
      "split": {"method": "chronological-60-20-20", "train_size": validation_start,
                "validation_size": test_start - validation_start, "test_size": len(test)},
      "selection": {"objective": "validation_log_loss", "selected": selected,
                    "candidate_count": len(candidates), "candidates": candidates},
      "test_metrics": {"brier_score": float(np.mean([brier_score(p, y) for p, y in zip(probabilities, outcomes, strict=True)])),
                       "log_loss": _mean_log_loss(test), "top_label_calibration_error": ece,
                       "top_label_calibration_curve": curve},
      "admission": {"admitted": False,
        "reason": "This evaluates the statistical model only; the fused model still lacks 200 out-of-sample market observations."},
      "test_forecasts": test,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _forecast(matches: list[dict], strength: float, xg_weight: float, home_factor: float) -> list[dict]:
    states: dict[str, dict[str, float]] = defaultdict(lambda: {"xgf": 0, "xga": 0, "gf": 0, "ga": 0, "n": 0})
    total_xg = 0.0
    forecasts = []
    for index, match in enumerate(matches):
        prior = total_xg / (2 * index) if index else 1.25
        home, away = states[match["home_team"]], states[match["away_team"]]
        home_attack = _rate(home, "xgf", "gf", prior, strength, xg_weight)
        home_defence = _rate(home, "xga", "ga", prior, strength, xg_weight)
        away_attack = _rate(away, "xgf", "gf", prior, strength, xg_weight)
        away_defence = _rate(away, "xga", "ga", prior, strength, xg_weight)
        home_lambda = math.sqrt(home_attack * away_defence) * home_factor
        away_lambda = math.sqrt(away_attack * home_defence) / home_factor
        distribution = poisson_grid(home_lambda, away_lambda)
        outcome = min(match["home_goals"], 10) * 11 + min(match["away_goals"], 10)
        forecasts.append({"match_id": match["match_id"], "kickoff_at": match["kickoff_at"],
          "home_team": match["home_team"], "away_team": match["away_team"],
          "home_lambda": home_lambda, "away_lambda": away_lambda,
          "home_goals": match["home_goals"], "away_goals": match["away_goals"],
          "outcome_index": outcome, "distribution": distribution})
        home["xgf"] += match["home_xg"]; home["xga"] += match["away_xg"]
        home["gf"] += match["home_goals"]; home["ga"] += match["away_goals"]; home["n"] += 1
        away["xgf"] += match["away_xg"]; away["xga"] += match["home_xg"]
        away["gf"] += match["away_goals"]; away["ga"] += match["home_goals"]; away["n"] += 1
        total_xg += match["home_xg"] + match["away_xg"]
    return forecasts


def _rate(state: dict[str, float], xg_key: str, goal_key: str, prior: float,
          strength: float, xg_weight: float) -> float:
    evidence = xg_weight * state[xg_key] + (1 - xg_weight) * state[goal_key]
    return max(0.05, (evidence + prior * strength) / (state["n"] + strength))


def _mean_log_loss(rows: list[dict]) -> float:
    return float(np.mean([log_loss(row["distribution"], row["outcome_index"]) for row in rows]))


def main() -> None:
    report = optimize(Path("data/processed/statsbomb-international-xg.json"),
                      Path("data/reports/statistical-optimized-v2.json"))
    print(json.dumps({"status": report["status"], "split": report["split"],
      "selected": report["selection"]["selected"], "test_metrics": report["test_metrics"] | {"top_label_calibration_curve": "saved"},
      "admission": report["admission"]}, indent=2))


if __name__ == "__main__":
    main()
