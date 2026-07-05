import json
from pathlib import Path

from sprp_worker import statsbomb


def test_collect_saves_xg_and_provenance(tmp_path: Path, monkeypatch) -> None:
    match = {"match_id": 1, "match_date": "2024-01-01", "kick_off": "12:00:00",
             "competition": {"competition_name": "Cup"}, "season": {"season_name": "2024"},
             "home_team": {"home_team_name": "A"}, "away_team": {"away_team_name": "B"},
             "home_score": 1, "away_score": 0}
    events = [{"period": 1, "team": {"name": "A"}, "type": {"name": "Shot"},
               "shot": {"statsbomb_xg": 0.7, "outcome": {"name": "Goal"}}},
              {"period": 2, "team": {"name": "B"}, "type": {"name": "Shot"},
               "shot": {"statsbomb_xg": 0.2, "outcome": {"name": "Saved"}}},
              {"period": 3, "team": {"name": "B"}, "type": {"name": "Shot"},
               "shot": {"statsbomb_xg": 0.9, "outcome": {"name": "Goal"}}}]
    monkeypatch.setattr(statsbomb, "_json", lambda url: [match] if "/matches/" in url else events)
    output = tmp_path / "xg.json"
    records = statsbomb.collect(output, [(1, 2)])
    saved = json.loads(output.read_text())
    assert records[0].home_xg == 0.7
    assert saved["provenance"]["matches"] == 1
    assert saved["matches"][0]["away_xg"] == 0.2
    assert saved["matches"][0]["home_goals"] == 1
    assert saved["matches"][0]["away_goals"] == 0
