from __future__ import annotations

import numpy as np


def brier_score(probabilities: list[float], outcome_index: int) -> float:
    """Return the multiclass Brier score for one observation."""
    values = np.asarray(probabilities, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("probabilities must be a non-empty vector")
    if np.any((values < 0) | (values > 1)) or not np.isclose(values.sum(), 1.0):
        raise ValueError("probabilities must be in [0, 1] and sum to 1")
    if outcome_index < 0 or outcome_index >= values.size:
        raise ValueError("outcome_index is outside the distribution")
    observed = np.zeros_like(values)
    observed[outcome_index] = 1.0
    return float(np.sum((values - observed) ** 2))


def log_loss(probabilities: list[float], outcome_index: int) -> float:
    values = _validated(probabilities, outcome_index)
    return float(-np.log(max(values[outcome_index], 1e-15)))


def calibration_curve(
    forecasts: list[list[float]], outcomes: list[int], bins: int = 10
) -> list[dict[str, float | int]]:
    if len(forecasts) != len(outcomes) or not forecasts:
        raise ValueError("forecasts and outcomes must have the same non-zero length")
    rows: list[tuple[float, int]] = []
    for probabilities, outcome in zip(forecasts, outcomes, strict=True):
        values = _validated(probabilities, outcome)
        rows.extend((float(value), int(index == outcome)) for index, value in enumerate(values))
    result = []
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        selected = [(p, y) for p, y in rows if p >= lower and (p <= upper if index == bins - 1 else p < upper)]
        result.append({
            "lower": lower, "upper": upper, "count": len(selected),
            "mean_forecast": float(np.mean([p for p, _ in selected])) if selected else 0.0,
            "observed_rate": float(np.mean([y for _, y in selected])) if selected else 0.0,
        })
    return result


def top_label_calibration_curve(
    forecasts: list[list[float]], outcomes: list[int], bins: int = 10
) -> list[dict[str, float | int]]:
    """Calibrate the most likely class; avoids dilution by many near-zero score cells."""
    if len(forecasts) != len(outcomes) or not forecasts:
        raise ValueError("forecasts and outcomes must have the same non-zero length")
    rows: list[tuple[float, int]] = []
    for probabilities, outcome in zip(forecasts, outcomes, strict=True):
        values = _validated(probabilities, outcome)
        prediction = int(np.argmax(values))
        rows.append((float(values[prediction]), int(prediction == outcome)))
    result = []
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        selected = [(p, y) for p, y in rows if p >= lower and (p <= upper if index == bins - 1 else p < upper)]
        result.append({"lower": lower, "upper": upper, "count": len(selected),
          "mean_forecast": float(np.mean([p for p, _ in selected])) if selected else 0.0,
          "observed_rate": float(np.mean([y for _, y in selected])) if selected else 0.0})
    return result


def _validated(probabilities: list[float], outcome_index: int) -> np.ndarray:
    values = np.asarray(probabilities, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("probabilities must be a non-empty vector")
    if np.any((values < 0) | (values > 1)) or not np.isclose(values.sum(), 1.0):
        raise ValueError("probabilities must be in [0, 1] and sum to 1")
    if outcome_index < 0 or outcome_index >= values.size:
        raise ValueError("outcome_index is outside the distribution")
    return values
