from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import skellam

from .metrics import brier_score, log_loss, top_label_calibration_curve


def poisson_grid(home_lambda: float, away_lambda: float, max_goals: int = 10) -> list[float]:
    values = []
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            values.append(_poisson(home, home_lambda) * _poisson(away, away_lambda))
    total = sum(values)
    return [value / total for value in values]


def run_backtest(input_path: Path, output_path: Path, test_fraction: float = 0.2) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    matches = sorted(payload["matches"], key=lambda row: (row["kickoff_at"], row["match_id"]))
    split = max(1, int(len(matches) * (1 - test_fraction)))
    states: dict[str, dict[str, float]] = defaultdict(lambda: {"for": 0.0, "against": 0.0, "n": 0.0})
    forecasts = []
    for index, match in enumerate(matches):
        prior = _league_prior(matches[:index])
        home_state, away_state = states[match["home_team"]], states[match["away_team"]]
        home_attack = _shrunk(home_state["for"], home_state["n"], prior, 5)
        home_defence = _shrunk(home_state["against"], home_state["n"], prior, 5)
        away_attack = _shrunk(away_state["for"], away_state["n"], prior, 5)
        away_defence = _shrunk(away_state["against"], away_state["n"], prior, 5)
        home_lambda = math.sqrt(home_attack * away_defence)
        away_lambda = math.sqrt(away_attack * home_defence)
        distribution = poisson_grid(home_lambda, away_lambda)
        outcome_index = min(match["home_goals"], 10) * 11 + min(match["away_goals"], 10)
        forecasts.append({
            "match_id": match["match_id"], "kickoff_at": match["kickoff_at"],
            "home_team": match["home_team"], "away_team": match["away_team"],
            "home_goals": match["home_goals"], "away_goals": match["away_goals"],
            "home_lambda": home_lambda, "away_lambda": away_lambda,
            "skellam": {"home_win": float(1 - skellam.cdf(0, home_lambda, away_lambda)),
                        "draw": float(skellam.pmf(0, home_lambda, away_lambda)),
                        "away_win": float(skellam.cdf(-1, home_lambda, away_lambda))},
            "distribution": distribution, "outcome_index": outcome_index,
            "partition": "test" if index >= split else "train",
        })
        home_state["for"] += match["home_xg"]
        home_state["against"] += match["away_xg"]
        home_state["n"] += 1
        away_state["for"] += match["away_xg"]
        away_state["against"] += match["home_xg"]
        away_state["n"] += 1
    test = forecasts[split:]
    probabilities = [row["distribution"] for row in test]
    outcomes = [row["outcome_index"] for row in test]
    curve = top_label_calibration_curve(probabilities, outcomes, bins=10)
    ece = sum(bin_["count"] * abs(bin_["mean_forecast"] - bin_["observed_rate"])
              for bin_ in curve) / sum(bin_["count"] for bin_ in curve)
    report = {
        "status": "RESEARCH_OUTPUT_NOT_VALIDATED",
        "model": "chronological-shrunk-xg-poisson-skellam-v1",
        "source": payload["provenance"], "split": {"method": "chronological", "index": split,
          "train_size": split, "test_size": len(test), "test_fraction": test_fraction},
        "metrics": {"brier_score": float(np.mean([brier_score(p, y) for p, y in zip(probabilities, outcomes, strict=True)])),
          "log_loss": float(np.mean([log_loss(p, y) for p, y in zip(probabilities, outcomes, strict=True)])),
          "top_label_calibration_error": ece, "top_label_calibration_curve": curve},
        "admission": {"admitted": False, "reason": "Statistical baseline only; fused market model has no out-of-sample history and test sample is below 200."},
        "forecasts": forecasts,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _league_prior(matches: list[dict]) -> float:
    if not matches:
        return 1.25
    return max(0.2, sum(row["home_xg"] + row["away_xg"] for row in matches) / (2 * len(matches)))


def _shrunk(total: float, count: float, prior: float, strength: float) -> float:
    return (total + prior * strength) / (count + strength)


def _poisson(k: int, rate: float) -> float:
    return math.exp(-rate) * rate**k / math.factorial(k)


def main() -> None:
    report = run_backtest(Path("data/processed/statsbomb-international-xg.json"),
                          Path("data/reports/statistical-baseline-v1.json"))
    print(json.dumps({"status": report["status"], "split": report["split"],
                      "metrics": report["metrics"] | {"top_label_calibration_curve": "saved in report"},
                      "admission": report["admission"]}, indent=2))


if __name__ == "__main__":
    main()
