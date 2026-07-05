from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np

from .metrics import brier_score, log_loss, top_label_calibration_curve


def record_result(report_path: Path, store_path: Path, external_match_id: str,
                  home_goals: int, away_goals: int, confirmed_at: str) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if home_goals > 10 or away_goals > 10:
        raise ValueError("score is outside the saved 0-10 grid")
    outcome_index = home_goals * 11 + away_goals
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store = json.loads(store_path.read_text()) if store_path.exists() else {"observations": []}
    for source in ("market", "statistical", "fused"):
        model = f"{source}-v2"
        observation = {"external_match_id": external_match_id, "model": model,
          "forecast_observed_at": report.get("market_snapshot_observed_at"),
          "confirmed_at": confirmed_at, "home_goals": home_goals, "away_goals": away_goals,
          "probabilities": [row["probability"] for row in report["distributions"][source]],
          "outcome_index": outcome_index}
        existing = next((i for i, row in enumerate(store["observations"])
                         if row["external_match_id"] == external_match_id and row["model"] == model), None)
        if existing is None: store["observations"].append(observation)
        else: store["observations"][existing] = observation
    metrics = {model: _model_metrics(store["observations"], model)
               for model in ("market-v2", "statistical-v2", "fused-v2")}
    fused_size = metrics["fused-v2"]["sample_size"]
    fused, market = metrics["fused-v2"], metrics["market-v2"]
    incremental = _paired_log_loss_interval(store["observations"], "fused-v2", "market-v2")
    checks = {"minimum_sample_size": fused_size >= 200,
      "brier_score": fused["brier_score_ci95"][1] <= 0.85,
      "log_loss": fused["log_loss_ci95"][1] <= 3.20,
      "top_label_calibration_error": fused["top_label_calibration_error"] <= 0.05,
      "incremental_log_loss": incremental["ci95"][1] <= -0.01}
    admitted = all(checks.values())
    store.update({"updated_at": datetime.now(timezone.utc).isoformat(), "metrics": metrics,
      "admission": {"admitted": admitted, "checks": checks, "incremental_log_loss": incremental,
        "reason": None if admitted else f"Admission checks failed; {fused_size}/200 fused observations collected."}})
    store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    return store


def _model_metrics(observations: list[dict], model: str) -> dict:
    rows = [row for row in observations if row["model"] == model]
    forecasts, outcomes = [row["probabilities"] for row in rows], [row["outcome_index"] for row in rows]
    curve = top_label_calibration_curve(forecasts, outcomes)
    brier_values = np.asarray([brier_score(p, y) for p, y in zip(forecasts, outcomes, strict=True)])
    log_values = np.asarray([log_loss(p, y) for p, y in zip(forecasts, outcomes, strict=True)])
    return {"sample_size": len(outcomes),
      "brier_score": float(np.mean(brier_values)), "brier_score_ci95": _bootstrap_mean_ci(brier_values),
      "log_loss": float(np.mean(log_values)), "log_loss_ci95": _bootstrap_mean_ci(log_values),
      "top_label_calibration_error": sum(row["count"] * abs(row["mean_forecast"] - row["observed_rate"])
                                         for row in curve) / len(outcomes),
      "top_label_calibration_curve": curve}


def _bootstrap_mean_ci(values: np.ndarray, samples: int = 2000) -> list[float]:
    rng = np.random.default_rng(20260705)
    means = np.mean(rng.choice(values, size=(samples, len(values)), replace=True), axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def _paired_log_loss_interval(observations: list[dict], model: str, control: str) -> dict:
    model_rows = {row["external_match_id"]: row for row in observations if row["model"] == model}
    control_rows = {row["external_match_id"]: row for row in observations if row["model"] == control}
    ids = sorted(model_rows.keys() & control_rows.keys())
    differences = np.asarray([log_loss(model_rows[i]["probabilities"], model_rows[i]["outcome_index"])
                              - log_loss(control_rows[i]["probabilities"], control_rows[i]["outcome_index"])
                              for i in ids])
    return {"mean": float(np.mean(differences)), "ci95": _bootstrap_mean_ci(differences), "sample_size": len(ids)}


def fetch_and_record(match_id: str, report_path: Path, store_path: Path, token: str) -> dict | None:
    request = Request(f"https://api.football-data.org/v4/matches/{match_id}",
                      headers={"X-Auth-Token": token, "User-Agent": "sprp-research/0.1"})
    match = None
    error: Exception | None = None
    for attempt in range(5):
        try:
            with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed provider host
                match = json.load(response)
            break
        except Exception as exc:
            error = exc
            retry_after = getattr(exc, "headers", {}).get("Retry-After") if getattr(exc, "headers", None) else None
            time.sleep(float(retry_after) if retry_after else 0.5 * 2**attempt)
    if match is None: raise RuntimeError(f"failed to fetch match {match_id}") from error
    if match["status"] != "FINISHED":
        return None
    score = match["score"]["fullTime"]
    return record_result(report_path, store_path, match_id, int(score["home"]), int(score["away"]),
                         match["lastUpdated"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("match_id")
    parser.add_argument("--report", type=Path, default=Path("data/reports/canada-morocco-fused.json"))
    parser.add_argument("--store", type=Path, default=Path("data/evaluations/fused-observations.json"))
    args = parser.parse_args()
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN") or _dotenv_token(Path(".env"))
    if not token:
        raise SystemExit("FOOTBALL_DATA_API_TOKEN is required")
    result = fetch_and_record(args.match_id, args.report, args.store, token)
    print(json.dumps(result or {"status": "WAITING_FOR_FINISHED_MATCH"}, ensure_ascii=False, indent=2))


def _dotenv_token(path: Path) -> str | None:
    if not path.exists(): return None
    for line in path.read_text().splitlines():
        if line.startswith("FOOTBALL_DATA_API_TOKEN="):
            return line.split("=", 1)[1].strip()
    return None


if __name__ == "__main__":
    main()
