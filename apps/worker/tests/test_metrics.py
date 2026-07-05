import numpy as np
import pytest

from sprp_worker.metrics import brier_score, calibration_curve, log_loss, top_label_calibration_curve


def test_brier_score_for_multiclass_observation() -> None:
    assert brier_score([0.5, 0.3, 0.2], 0) == pytest.approx(0.38)


def test_log_loss_and_calibration_curve() -> None:
    assert log_loss([0.7, 0.2, 0.1], 0) == pytest.approx(-np.log(0.7))
    curve = calibration_curve([[0.7, 0.3], [0.2, 0.8]], [0, 1], bins=5)
    assert sum(item["count"] for item in curve) == 4
    top_curve = top_label_calibration_curve([[0.7, 0.3], [0.2, 0.8]], [0, 1], bins=5)
    assert sum(item["count"] for item in top_curve) == 2
    assert sum(item["observed_rate"] * item["count"] for item in top_curve) == 2


@pytest.mark.parametrize(
    ("probabilities", "outcome_index"),
    [([], 0), ([0.4, 0.4], 0), ([0.5, 0.5], 2)],
)
def test_brier_score_rejects_invalid_inputs(
    probabilities: list[float], outcome_index: int
) -> None:
    with pytest.raises(ValueError):
        brier_score(probabilities, outcome_index)
