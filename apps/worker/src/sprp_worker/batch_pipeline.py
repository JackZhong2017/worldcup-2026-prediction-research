from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .fuse_current import fuse_match
from .polymarket_snapshot import collect_event
from .settle import _dotenv_token


def run_batch(root: Path, tag_id: str = "102232") -> dict:
    events = _discover(tag_id)
    now = datetime.now(timezone.utc)
    exact = [event for event in events if event.get("title", "").endswith("- Exact Score")
             and datetime.fromisoformat(event["endDate"].replace("Z", "+00:00")) > now]
    records = []
    fixtures = _football_matches(os.environ.get("FOOTBALL_DATA_API_TOKEN") or _dotenv_token(root / ".env"))
    for event in exact:
        event_id = str(event["id"])
        snapshot_path = root / "data" / "snapshots" / f"polymarket-{event_id}.json"
        snapshot = collect_event(event_id, snapshot_path)
        teams = snapshot["event"]["title"].removesuffix(" - Exact Score")
        home, away = teams.split(" vs. ", 1)
        report_path = root / "data" / "reports" / f"fused-{event_id}.json"
        result = fuse_match(root / "data" / "processed" / "statsbomb-international-xg.json",
          snapshot_path, report_path, home, away,
          model_config_path=root / "data" / "reports" / "statistical-optimized-v2.json")
        fixture = next((match for match in fixtures if match["home"] == home and match["away"] == away
                        and match["utcDate"] == event["endDate"]), None)
        records.append({"event_id": event_id, "football_data_match_id": fixture["id"] if fixture else None,
          "end_date": event["endDate"], "home_team": home,
          "away_team": away, "snapshot": str(snapshot_path.relative_to(root)),
          "report": str(report_path.relative_to(root)), "history_matches": {
            "home": result["inputs"]["home"]["matches"], "away": result["inputs"]["away"]["matches"]},
          "status": result["status"]})
    manifest = {"generated_at": now.isoformat(), "tag_id": tag_id, "count": len(records),
                "records": records}
    path = root / "data" / "manifests" / "active-fused-samples.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _discover(tag_id: str) -> list[dict]:
    events = []
    for offset in range(0, 1000, 100):
        query = urlencode({"active": "true", "closed": "false", "limit": 100, "offset": offset,
                           "tag_id": tag_id, "related_tags": "true", "order": "end_date", "ascending": "true"})
        request = Request(f"https://gamma-api.polymarket.com/events?{query}",
                          headers={"User-Agent": "sprp-research/0.1"})
        page = _load_json(request)
        events.extend(page)
        if len(page) < 100: break
    return events


def _football_matches(token: str | None) -> list[dict]:
    if not token: return []
    query = urlencode({"dateFrom": "2026-07-01", "dateTo": "2026-07-10", "competitions": "WC"})
    request = Request(f"https://api.football-data.org/v4/matches?{query}",
                      headers={"X-Auth-Token": token, "User-Agent": "sprp-research/0.1"})
    payload = _load_json(request)
    return [{"id": str(row["id"]), "utcDate": row["utcDate"],
             "home": row["homeTeam"]["name"], "away": row["awayTeam"]["name"]}
            for row in payload["matches"]]


def _load_json(request: Request):
    error: Exception | None = None
    for attempt in range(5):
        try:
            with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed provider hosts
                return json.load(response)
        except Exception as exc:
            error = exc
            time.sleep(0.5 * 2**attempt)
    raise RuntimeError("provider request failed after 5 attempts") from error


def main() -> None:
    manifest = run_batch(Path.cwd())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
