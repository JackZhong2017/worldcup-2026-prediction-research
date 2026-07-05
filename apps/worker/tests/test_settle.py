import json
from pathlib import Path

from sprp_worker.settle import record_result


def test_result_recording_is_idempotent_and_keeps_gate_closed(tmp_path: Path) -> None:
    distribution = [{"home_goals": i // 11, "away_goals": i % 11, "probability": 1 / 121}
                    for i in range(121)]
    report, store = tmp_path / "report.json", tmp_path / "store.json"
    report.write_text(json.dumps({"distributions": {
        "market": distribution, "statistical": distribution, "fused": distribution
    }}))
    record_result(report, store, "1", 1, 0, "2024-01-01")
    result = record_result(report, store, "1", 1, 0, "2024-01-01")
    assert result["metrics"]["fused-v2"]["sample_size"] == 1
    assert result["metrics"]["fused-v2"]["log_loss_ci95"][0] == result["metrics"]["fused-v2"]["log_loss_ci95"][1]
    assert len(result["observations"]) == 3
    assert result["admission"]["admitted"] is False
