from __future__ import annotations

import json
import math
from pathlib import Path

from .backtest import poisson_grid


def fuse_match(history_path: Path, market_path: Path, output_path: Path,
               home_team: str, away_team: str, statistical_weight: float = 0.5,
               model_config_path: Path | None = None) -> dict:
    history = json.loads(history_path.read_text(encoding="utf-8"))["matches"]
    market = json.loads(market_path.read_text(encoding="utf-8"))
    prior = sum(row["home_xg"] + row["away_xg"] for row in history) / (2 * len(history))
    config = {"prior_strength": 5.0, "xg_weight": 1.0, "home_factor": 1.0}
    if model_config_path:
        config.update(json.loads(model_config_path.read_text(encoding="utf-8"))["selection"]["selected"])
    home = _team_state(history, home_team, prior, config["prior_strength"], config["xg_weight"])
    away = _team_state(history, away_team, prior, config["prior_strength"], config["xg_weight"])
    home_lambda = math.sqrt(home["attack_rate"] * away["defence_rate"]) * config["home_factor"]
    away_lambda = math.sqrt(away["attack_rate"] * home["defence_rate"]) / config["home_factor"]
    statistical = poisson_grid(home_lambda, away_lambda)
    explicit = {row["home_goals"] * 11 + row["away_goals"]: row["probability"]
                for row in market["distribution"] if row["label"] != "OTHER"}
    other = next(row["probability"] for row in market["distribution"] if row["label"] == "OTHER")
    missing_mass = sum(probability for index, probability in enumerate(statistical) if index not in explicit)
    expanded_market = [explicit.get(index, other * probability / missing_mass)
                       for index, probability in enumerate(statistical)]
    fused_raw = [s**statistical_weight * m**(1 - statistical_weight)
                 for s, m in zip(statistical, expanded_market, strict=True)]
    fused = [value / sum(fused_raw) for value in fused_raw]
    result = {
        "status": "RESEARCH_OUTPUT_NOT_VALIDATED", "confidence": None,
        "market_snapshot_observed_at": market["provenance"].get("observed_at"),
        "reason": "The fused model has no admitted out-of-sample evaluation report.",
        "match": {"home_team": home_team, "away_team": away_team,
                  "market_event": market["provenance"]["event_id"]},
        "inputs": {"home": home, "away": away, "league_xg_prior": prior,
                   "home_lambda": home_lambda, "away_lambda": away_lambda,
                   "statistical_weight": statistical_weight,
                   "validated_statistical_config": config,
                   "history_last_match": max(row["kickoff_at"] for row in history)},
        "distributions": {"market": _cells(expanded_market),
                          "statistical": _cells(statistical), "fused": _cells(fused)},
        "diagnostics": {"market": _diagnostics(expanded_market),
                        "statistical": _diagnostics(statistical), "fused": _diagnostics(fused)},
        "top3": sorted(_cells(fused), key=lambda row: row["probability"], reverse=True)[:3],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _team_state(matches: list[dict], team: str, prior: float, strength: float = 5,
                xg_weight: float = 1.0) -> dict:
    xg_for, xg_against, goals_for, goals_against, count = 0.0, 0.0, 0.0, 0.0, 0
    for row in matches:
        if row["home_team"] == team:
            xg_for += row["home_xg"]; xg_against += row["away_xg"]
            goals_for += row["home_goals"]; goals_against += row["away_goals"]; count += 1
        elif row["away_team"] == team:
            xg_for += row["away_xg"]; xg_against += row["home_xg"]
            goals_for += row["away_goals"]; goals_against += row["home_goals"]; count += 1
    attack = xg_weight * xg_for + (1 - xg_weight) * goals_for
    defence = xg_weight * xg_against + (1 - xg_weight) * goals_against
    return {"matches": count, "attack_rate": (attack + prior * strength) / (count + strength),
            "defence_rate": (defence + prior * strength) / (count + strength)}


def _cells(probabilities: list[float]) -> list[dict]:
    return [{"home_goals": index // 11, "away_goals": index % 11, "probability": probability}
            for index, probability in enumerate(probabilities)]


def _diagnostics(probabilities: list[float]) -> dict:
    entropy = -sum(p * math.log2(p) for p in probabilities if p)
    return {"entropy": entropy, "normalized_entropy": entropy / math.log2(len(probabilities)),
            "concentration": sum(p * p for p in probabilities),
            "top3_coverage": sum(sorted(probabilities, reverse=True)[:3])}


def main() -> None:
    result = fuse_match(Path("data/processed/statsbomb-international-xg.json"),
      Path("data/snapshots/polymarket-650891.json"), Path("data/reports/canada-morocco-fused.json"),
      "Canada", "Morocco", model_config_path=Path("data/reports/statistical-optimized-v2.json"))
    print(json.dumps({"status": result["status"], "inputs": result["inputs"],
      "diagnostics": result["diagnostics"], "top3": result["top3"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
