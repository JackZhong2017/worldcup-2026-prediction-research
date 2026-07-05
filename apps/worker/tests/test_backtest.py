import json
from pathlib import Path

import pytest

from sprp_worker.backtest import poisson_grid, run_backtest


def test_poisson_grid_is_complete_and_normalized() -> None:
    grid = poisson_grid(1.4, 1.1)
    assert len(grid) == 121
    assert sum(grid) == pytest.approx(1.0)


def test_chronological_backtest_stays_unvalidated(tmp_path: Path) -> None:
    matches = []
    for index in range(10):
        matches.append({"match_id": index, "kickoff_at": f"2024-01-{index + 1:02}T12:00:00",
          "home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0,
          "home_xg": 1.2, "away_xg": 0.7})
    input_path, output_path = tmp_path / "input.json", tmp_path / "report.json"
    input_path.write_text(json.dumps({"provenance": {}, "matches": matches}))
    report = run_backtest(input_path, output_path)
    assert report["split"]["test_size"] == 2
    assert report["status"] == "RESEARCH_OUTPUT_NOT_VALIDATED"
    assert not report["admission"]["admitted"]
    assert len(report["forecasts"][0]["distribution"]) == 121
