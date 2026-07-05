import json
from pathlib import Path

from sprp_worker.optimize import optimize


def test_optimizer_uses_chronological_validation_and_keeps_gate_closed(tmp_path: Path) -> None:
    matches = [{"match_id": i, "kickoff_at": f"2024-{i // 28 + 1:02}-{i % 28 + 1:02}",
      "home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0,
      "home_xg": 1.2, "away_xg": 0.6} for i in range(20)]
    source, output = tmp_path / "source.json", tmp_path / "report.json"
    source.write_text(json.dumps({"provenance": {}, "matches": matches}))
    report = optimize(source, output)
    assert report["split"] == {"method": "chronological-60-20-20", "train_size": 12,
                                "validation_size": 4, "test_size": 4}
    assert report["selection"]["candidate_count"] == 27
    assert report["admission"]["admitted"] is False
