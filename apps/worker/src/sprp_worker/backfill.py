from __future__ import annotations

import json
import math
import os
import unicodedata
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request

import numpy as np

from .batch_pipeline import _load_json
from .fuse_current import fuse_match
from .metrics import brier_score, log_loss, top_label_calibration_curve
from .settle import _dotenv_token


def run_backfill(root: Path, tag_id: str = "102232") -> dict:
    events = _closed_exact_events(tag_id)
    football_results = _football_results(os.environ.get("FOOTBALL_DATA_API_TOKEN") or _dotenv_token(root / ".env"))
    records, skipped = [], []
    for event in events:
        try:
            snapshot_path = root / "data/backfill/snapshots" / f"polymarket-{event['id']}.json"
            if snapshot_path.exists():
                snapshot, market_actual = json.loads(snapshot_path.read_text()), None
            else:
                snapshot, market_actual = _historical_snapshot(event)
            actual = _find_football_result(football_results, event) or market_actual
            if actual is None:
                skipped.append({"event_id": event["id"], "reason": "exact regular-time score unavailable"}); continue
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
            teams = event["title"].removesuffix(" - Exact Score")
            home, away = teams.split(" vs. ", 1)
            report_path = root / "data/backfill/reports" / f"fused-{event['id']}.json"
            fused = fuse_match(root / "data/processed/statsbomb-international-xg.json", snapshot_path,
              report_path, home, away,
              model_config_path=root / "data/reports/statistical-optimized-v2.json")
            records.append({"event_id": str(event["id"]), "kickoff_at": event["endDate"],
              "home_team": home, "away_team": away, "actual": actual,
              "outcome_index": actual[0] * 11 + actual[1],
              "market": [row["probability"] for row in fused["distributions"]["market"]],
              "statistical": [row["probability"] for row in fused["distributions"]["statistical"]],
              "max_price_age_seconds": snapshot["provenance"]["max_price_age_seconds"]})
        except Exception as error:
            skipped.append({"event_id": str(event.get("id")), "reason": str(error)})
    records.sort(key=lambda row: row["kickoff_at"])
    report = _evaluate(records, skipped)
    output = root / "data/backfill/fused-out-of-sample-report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _historical_snapshot(event: dict) -> tuple[dict, tuple[int, int] | None]:
    cutoff = int(datetime.fromisoformat(event["endDate"].replace("Z", "+00:00")).timestamp()) - 300
    tokens, parsed = [], []
    actual = None
    for market in event["markets"]:
        labels = json.loads(market["outcomes"]); token_ids = json.loads(market["clobTokenIds"])
        yes_index = labels.index("Yes"); token = token_ids[yes_index]
        score = re.search(r"(\d+)\s*-\s*(\d+)", market["question"])
        label = (int(score.group(1)), int(score.group(2))) if score else None
        final_prices = [float(value) for value in json.loads(market["outcomePrices"])]
        if final_prices[yes_index] > 0.99: actual = label
        tokens.append(token); parsed.append((market, token, label))
    body = json.dumps({"markets": tokens, "start_ts": cutoff - 86400,
                       "end_ts": cutoff, "fidelity": 30}).encode()
    request = Request("https://clob.polymarket.com/batch-prices-history", data=body,
                      headers={"Content-Type": "application/json", "User-Agent": "sprp-research/0.1"})
    history = _load_json(request)["history"]
    rows, ages = [], []
    for market, token, label in parsed:
        points = [point for point in history.get(token, []) if point["t"] <= cutoff]
        if not points: raise ValueError(f"missing pre-match history for market {market['id']}")
        point = max(points, key=lambda value: value["t"]); ages.append(cutoff - point["t"])
        rows.append({"market_id": market["id"], "label": f"{label[0]}-{label[1]}" if label else "OTHER",
          "home_goals": label[0] if label else None, "away_goals": label[1] if label else None,
          "raw_yes_price": point["p"], "probability": point["p"]})
    if max(ages) > 21600: raise ValueError(f"price older than 6 hours: {max(ages)} seconds")
    total = sum(row["probability"] for row in rows)
    for row in rows: row["probability"] /= total
    return ({"provenance": {"provider": "Polymarket CLOB price history", "event_id": str(event["id"]),
              "observed_at": datetime.fromtimestamp(cutoff, timezone.utc).isoformat(),
              "cutoff_rule": "latest point at least 5 minutes before kickoff",
              "normalization_raw_sum": total, "max_price_age_seconds": max(ages)},
            "event": {"title": event["title"], "slug": event["slug"], "end_date": event["endDate"],
                      "active": False, "closed": True}, "distribution": rows}, actual)


def _evaluate(records: list[dict], skipped: list[dict]) -> dict:
    validation_start, test_start = int(len(records) * 0.6), int(len(records) * 0.8)
    weights = [index / 10 for index in range(11)]
    candidates = [{"statistical_weight": weight,
      "validation_log_loss": _score(records[validation_start:test_start], weight)["log_loss"]}
      for weight in weights]
    selected = min(candidates, key=lambda row: row["validation_log_loss"])
    test = records[test_start:]
    return {"status": "RESEARCH_OUTPUT_NOT_VALIDATED", "model": "historical-market-xg-fusion-v1",
      "snapshot_rule": "last CLOB point no later than kickoff minus 5 minutes; maximum age 6 hours",
      "split": {"method": "chronological-60-20-20", "train_size": validation_start,
        "validation_size": test_start - validation_start, "test_size": len(test)},
      "selection": {"selected": selected, "candidates": candidates},
      "test": {"market_only": _score(test, 0), "statistical_only": _score(test, 1),
               "fused": _score(test, selected["statistical_weight"])},
      "admission": {"admitted": False,
        "reason": f"Only {len(test)}/200 untouched fused test observations are available."},
      "usable_matches": len(records), "skipped": skipped, "records": records}


def _score(records: list[dict], statistical_weight: float) -> dict:
    forecasts, outcomes = [], []
    for row in records:
        raw = [max(s, 1e-12) ** statistical_weight * max(m, 1e-12) ** (1 - statistical_weight)
               for s, m in zip(row["statistical"], row["market"], strict=True)]
        forecasts.append([value / sum(raw) for value in raw]); outcomes.append(row["outcome_index"])
    if not forecasts: return {"sample_size": 0, "brier_score": math.nan, "log_loss": math.nan,
                              "top_label_calibration_error": math.nan, "top_label_calibration_curve": []}
    curve = top_label_calibration_curve(forecasts, outcomes)
    return {"sample_size": len(forecasts),
      "brier_score": float(np.mean([brier_score(p, y) for p, y in zip(forecasts, outcomes, strict=True)])),
      "log_loss": float(np.mean([log_loss(p, y) for p, y in zip(forecasts, outcomes, strict=True)])),
      "top_label_calibration_error": sum(bin_["count"] * abs(bin_["mean_forecast"] - bin_["observed_rate"])
                                         for bin_ in curve) / len(forecasts),
      "top_label_calibration_curve": curve}


def _closed_exact_events(tag_id: str) -> list[dict]:
    result = []
    for offset in range(0, 2000, 100):
        query = urlencode({"closed": "true", "limit": 100, "offset": offset, "tag_id": tag_id,
                           "related_tags": "true", "order": "end_date", "ascending": "true"})
        page = _load_json(Request(f"https://gamma-api.polymarket.com/events?{query}",
                                  headers={"User-Agent": "sprp-research/0.1"}))
        result.extend(event for event in page if event.get("title", "").endswith("- Exact Score"))
        if len(page) < 100: break
    return result


def _football_results(token: str | None) -> list[dict]:
    if not token: return []
    results: list[dict] = []
    # football-data treats dateTo as an exclusive boundary.
    for date_from, date_to in (("2026-06-11", "2026-06-21"), ("2026-06-21", "2026-07-01"),
                               ("2026-07-01", "2026-07-11")):
        query = urlencode({"dateFrom": date_from, "dateTo": date_to, "competitions": "WC"})
        request = Request(f"https://api.football-data.org/v4/matches?{query}",
                          headers={"X-Auth-Token": token, "User-Agent": "sprp-research/0.1"})
        payload = _load_json(request)
        for match in payload["matches"]:
            if match["status"] != "FINISHED": continue
            score = match["score"]
            regular = score.get("regularTime") or (score.get("fullTime") if score.get("duration") == "REGULAR" else None)
            if regular and regular.get("home") is not None and regular.get("away") is not None:
                results.append({"utc_date": match["utcDate"], "home": match["homeTeam"]["name"],
                  "away": match["awayTeam"]["name"], "score": (int(regular["home"]), int(regular["away"]))})
    return results


def _find_football_result(results: list[dict], event: dict) -> tuple[int, int] | None:
    teams = event["title"].removesuffix(" - Exact Score")
    home, away = teams.split(" vs. ", 1)
    kickoff = datetime.fromisoformat(event["endDate"].replace("Z", "+00:00"))
    candidates = [row for row in results if _team_key(row["home"]) == _team_key(home)
                  and _team_key(row["away"]) == _team_key(away)]
    candidates = [row for row in candidates if abs((datetime.fromisoformat(row["utc_date"].replace("Z", "+00:00"))
                  - kickoff).total_seconds()) <= 7200]
    return min(candidates, key=lambda row: abs((datetime.fromisoformat(row["utc_date"].replace("Z", "+00:00"))
               - kickoff).total_seconds()))["score"] if candidates else None


def _team_key(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    key = re.sub(r"[^a-z]", "", ascii_name.lower())
    aliases = {"turkiye": "turkey", "cotedivoire": "ivorycoast", "korearepublic": "southkorea",
      "iriran": "iran", "drcongo": "congodr", "caboverde": "capeverdeislands",
      "bosniaandherzegovina": "bosniaherzegovina"}
    return aliases.get(key, key)


def main() -> None:
    report = run_backfill(Path.cwd())
    summary = {key: report[key] for key in ("status", "split", "selection", "test", "admission", "usable_matches")}
    summary["skipped_count"] = len(report["skipped"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
