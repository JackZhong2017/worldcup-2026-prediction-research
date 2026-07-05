from sprp_worker.backfill import _score, _team_key


def test_score_compares_market_statistical_and_fused() -> None:
    record = {"market": [0.8, 0.2], "statistical": [0.6, 0.4], "outcome_index": 0}
    market = _score([record], 0)
    statistical = _score([record], 1)
    fused = _score([record], 0.5)
    assert market["log_loss"] < fused["log_loss"] < statistical["log_loss"]
    assert market["sample_size"] == 1


def test_provider_team_aliases_match() -> None:
    assert _team_key("Türkiye") == _team_key("Turkey")
    assert _team_key("Côte d'Ivoire") == _team_key("Ivory Coast")
    assert _team_key("Bosnia and Herzegovina") == _team_key("Bosnia-Herzegovina")
