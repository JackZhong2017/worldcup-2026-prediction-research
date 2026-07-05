import json
from pathlib import Path

import pytest

from sprp_worker.fuse_current import fuse_match


def test_fusion_saves_three_complete_distributions(tmp_path: Path) -> None:
    history = {"matches": [{"kickoff_at": "2024-01-01", "home_team": "A", "away_team": "B",
      "home_xg": 1.5, "away_xg": 0.7, "home_goals": 1, "away_goals": 0}]}
    market = {"provenance": {"event_id": "1"}, "distribution": [
      {"label": "0-0", "home_goals": 0, "away_goals": 0, "probability": 0.3},
      {"label": "OTHER", "home_goals": None, "away_goals": None, "probability": 0.7}]}
    history_path, market_path, output = tmp_path / "h.json", tmp_path / "m.json", tmp_path / "o.json"
    history_path.write_text(json.dumps(history)); market_path.write_text(json.dumps(market))
    result = fuse_match(history_path, market_path, output, "A", "B")
    assert all(len(values) == 121 for values in result["distributions"].values())
    assert sum(result["distributions"]["fused"][i]["probability"] for i in range(121)) == pytest.approx(1)
    assert result["status"] == "RESEARCH_OUTPUT_NOT_VALIDATED"
    assert result["confidence"] is None
