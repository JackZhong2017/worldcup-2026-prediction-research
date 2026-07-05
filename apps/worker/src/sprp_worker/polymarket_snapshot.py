from __future__ import annotations

import argparse
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def collect_event(event_id: str, output: Path) -> dict:
    url = f"https://gamma-api.polymarket.com/events/{event_id}"
    request = Request(url, headers={"User-Agent": "sprp-research/0.1"})
    event = None
    error: Exception | None = None
    for attempt in range(5):
        try:
            with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed provider host
                event = json.load(response)
            break
        except Exception as exc:
            error = exc
            time.sleep(0.5 * 2**attempt)
    if event is None:
        raise RuntimeError(f"failed to fetch Polymarket event {event_id}") from error
    outcomes = []
    for market in event["markets"]:
        question = market["question"]
        labels, prices = json.loads(market["outcomes"]), json.loads(market["outcomePrices"])
        yes = float(prices[labels.index("Yes")])
        score = re.search(r"(\d+)\s*-\s*(\d+)", question)
        if score:
            label, home, away = f"{score.group(1)}-{score.group(2)}", int(score.group(1)), int(score.group(2))
        elif "Other Score" in question:
            label, home, away = "OTHER", None, None
        else:
            continue
        outcomes.append({"market_id": market["id"], "label": label, "home_goals": home,
          "away_goals": away, "raw_yes_price": yes, "probability": yes})
    total = sum(row["probability"] for row in outcomes)
    for row in outcomes:
        row["probability"] /= total
    probabilities = [row["probability"] for row in outcomes]
    entropy = -sum(p * math.log2(p) for p in probabilities if p)
    snapshot = {
        "provenance": {"provider": "Polymarket Gamma API", "event_id": event_id,
          "url": url, "observed_at": datetime.now(timezone.utc).isoformat(),
          "normalization_raw_sum": total},
        "event": {"title": event["title"], "slug": event["slug"], "end_date": event["endDate"],
          "active": event["active"], "closed": event["closed"]},
        "distribution": outcomes,
        "diagnostics": {"entropy": entropy,
          "normalized_entropy": entropy / math.log2(len(probabilities)),
          "concentration": sum(p * p for p in probabilities),
          "top3_coverage": sum(sorted(probabilities, reverse=True)[:3])},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("event_id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(f"data/snapshots/polymarket-{args.event_id}.json")
    snapshot = collect_event(args.event_id, output)
    print(json.dumps({"saved": str(output), "event": snapshot["event"],
                      "diagnostics": snapshot["diagnostics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
