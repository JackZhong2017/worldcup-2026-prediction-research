import json
from pathlib import Path

import pytest

from sprp_worker import polymarket_snapshot


class Response:
    def __enter__(self): return self
    def __exit__(self, *_): return None
    def read(self): return json.dumps({"title": "A vs B", "slug": "a-b", "endDate": "2024-01-01",
      "active": True, "closed": False, "markets": [
        {"id": "1", "question": "Exact Score: A 0 - 0 B?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.4","0.6"]'},
        {"id": "2", "question": "Exact Score: Any Other Score?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.5","0.5"]'}]}).encode()


def test_snapshot_normalizes_and_saves(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(polymarket_snapshot, "urlopen", lambda *_args, **_kwargs: Response())
    output = tmp_path / "snapshot.json"
    snapshot = polymarket_snapshot.collect_event("1", output)
    assert sum(row["probability"] for row in snapshot["distribution"]) == pytest.approx(1)
    assert snapshot["distribution"][1]["label"] == "OTHER"
    assert output.exists()
