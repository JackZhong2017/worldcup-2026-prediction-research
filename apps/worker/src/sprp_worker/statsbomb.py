from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
DEFAULT_SEASONS = [(43, 3), (43, 106), (55, 43), (55, 282), (223, 282)]


@dataclass(frozen=True)
class MatchXg:
    match_id: int
    competition: str
    season: str
    kickoff_at: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: float
    away_xg: float
    source: str = "StatsBomb Open Data"


def collect(output: Path, seasons: list[tuple[int, int]] | None = None) -> list[MatchXg]:
    selected = seasons or DEFAULT_SEASONS
    matches: list[dict] = []
    for competition_id, season_id in selected:
        matches.extend(_json(f"{BASE}/matches/{competition_id}/{season_id}.json"))
    cache = output.parent / "statsbomb-events"
    cache.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as executor:
        records = list(executor.map(lambda match: _extract(match, cache), matches))
    records.sort(key=lambda row: (row.kickoff_at, row.match_id))
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provenance": {"provider": "StatsBomb Open Data",
          "repository": "https://github.com/statsbomb/open-data",
          "collected_at": datetime.now().astimezone().isoformat(),
          "seasons": selected, "matches": len(records)},
        "matches": [asdict(record) for record in records],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def _extract(match: dict, cache: Path | None = None) -> MatchXg:
    home = match["home_team"]["home_team_name"]
    away = match["away_team"]["away_team_name"]
    cached = cache / f"{match['match_id']}.json" if cache else None
    if cached and cached.exists():
        events = json.loads(cached.read_text(encoding="utf-8"))
    else:
        events = _json(f"{BASE}/events/{match['match_id']}.json")
        if cached:
            cached.write_text(json.dumps(events), encoding="utf-8")
    xg = {home: 0.0, away: 0.0}
    goals = {home: 0, away: 0}
    for event in events:
        if int(event.get("period", 0)) not in (1, 2):
            continue
        shot = event.get("shot")
        team = event.get("team", {}).get("name")
        if shot and team in xg:
            xg[team] += float(shot.get("statsbomb_xg", 0.0))
            if shot.get("outcome", {}).get("name") == "Goal":
                goals[team] += 1
        if event.get("type", {}).get("name") == "Own Goal For" and team in goals:
            goals[team] += 1
    kickoff = f"{match['match_date']}T{match.get('kick_off') or '00:00:00'}"
    return MatchXg(int(match["match_id"]), match["competition"]["competition_name"],
      match["season"]["season_name"], kickoff, home, away, goals[home], goals[away],
      xg[home], xg[away])


def _json(url: str):
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            request = Request(url, headers={"User-Agent": "sprp-research/0.1"})
            with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed official host
                return json.load(response)
        except Exception as error:  # network errors vary by platform
            last_error = error
            time.sleep(0.5 * 2**attempt)
    raise RuntimeError(f"failed to fetch {url} after 5 attempts") from last_error
