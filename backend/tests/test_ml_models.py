"""ML core: deterministic simulated data, the fan predictor and the energy anomaly detector."""

from datetime import UTC, datetime

import numpy as np
import pytest

from app.devices.specs.ac import AcState
from app.devices.specs.door import DoorLockState
from app.devices.specs.fan import FanState
from app.devices.specs.light import LightState
from app.ml.dataset import _power_for, generate_fan_dataset, generate_power_dataset
from app.ml.features import FAN_FEATURES, setting_level
from app.ml.service import train_models

NOW = datetime(2026, 10, 6, 15, 0, tzinfo=UTC)
HOT_OCCUPIED = {
    "hour": 15.0, "day_of_week": 1.0, "temperature_c": 30.4, "humidity_pct": 50.0, "occupied": 1.0,
    "occupant_count": 2.0, "ambient_light_lux": 400.0, "fan_on": 0.0, "fan_recently_on": 0.0,
}
COOL_VACANT = {**HOT_OCCUPIED, "temperature_c": 23.0, "occupied": 0.0, "occupant_count": 0.0, "hour": 11.0}


@pytest.fixture(scope="module")
def models():
    return train_models(7, 60, 0.5)


# --- Dataset ------------------------------------------------------------------------------


def test_fan_dataset_is_deterministic_and_sized_for_a_demonstration() -> None:
    first, second = generate_fan_dataset(seed=7), generate_fan_dataset(seed=7)
    assert np.array_equal(first.features, second.features)
    assert np.array_equal(first.labels, second.labels)
    assert first.features.shape == (first.metadata["samples"], len(FAN_FEATURES))
    assert first.metadata["samples"] > 5000
    assert first.metadata["source"] == "simulated"
    assert not np.array_equal(generate_fan_dataset(seed=8).labels, first.labels)


def test_fan_dataset_has_realistic_correlations() -> None:
    data = generate_fan_dataset(seed=7)
    x, y = data.features, data.labels
    temp, occupied = x[:, FAN_FEATURES.index("temperature_c")], x[:, FAN_FEATURES.index("occupied")]
    hot_home = y[(temp > 28.5) & (occupied == 1)].mean()
    cool_away = y[(temp < 25) & (occupied == 0)].mean()
    assert hot_home > 0.5 > cool_away
    assert 0.1 < y.mean() < 0.5  # imbalanced, like real usage


def test_power_dataset_contains_a_small_share_of_injected_faults() -> None:
    datasets = generate_power_dataset(seed=11)
    assert set(datasets) == {"light", "fan", "ac", "door_lock"}
    for dataset in datasets.values():
        assert 0.005 < dataset.labels.mean() < 0.05


# --- Prediction ---------------------------------------------------------------------------


def test_prediction_is_valid_and_explained(models) -> None:
    prediction = models.predictor.predict(HOT_OCCUPIED, device_name="Living Room Fan", now=NOW)

    assert prediction.device_id == "fan_living_room"
    assert prediction.target == "FAN_ON_SOON"
    assert 0 <= prediction.probability <= 1
    assert prediction.prediction == ("ON" if prediction.probability >= 0.5 else "OFF")
    assert prediction.model == "random_forest_v1"
    assert set(prediction.features) == set(FAN_FEATURES)
    assert prediction.reason_features
    assert f"{round(prediction.probability * 100)}%" in prediction.explanation
    assert "Random Forest" in prediction.explanation


def test_prediction_follows_the_simulated_comfort_pattern(models) -> None:
    hot = models.predictor.predict(HOT_OCCUPIED, device_name="Fan", now=NOW)
    cool = models.predictor.predict(COOL_VACANT, device_name="Fan", now=NOW)
    assert hot.prediction == "ON" and cool.prediction == "OFF"
    assert hot.probability > cool.probability + 0.4
    assert "temperature_c" in hot.reason_features


def test_prediction_is_deterministic(models) -> None:
    a = models.predictor.predict(HOT_OCCUPIED, device_name="Fan", now=NOW)
    b = train_models.__wrapped__(7, 60, 0.5).predictor.predict(HOT_OCCUPIED, device_name="Fan", now=NOW)
    assert a.probability == b.probability


def test_missing_features_are_imputed_and_reported(models) -> None:
    features = {**HOT_OCCUPIED, "temperature_c": None}
    features.pop("humidity_pct")

    prediction = models.predictor.predict(features, device_name="Fan", now=NOW)

    assert set(prediction.missing_features) == {"temperature_c", "humidity_pct"}
    assert prediction.features["temperature_c"] is None
    assert 0 <= prediction.probability <= 1
    assert all(f.imputed for f in prediction.factors if f.feature in prediction.missing_features)


def test_unknown_features_are_rejected(models) -> None:
    with pytest.raises(ValueError, match="Unknown features"):
        models.predictor.predict({**HOT_OCCUPIED, "rain": 1.0}, device_name="Fan", now=NOW)


def test_evaluation_metrics_beat_the_majority_baseline(models) -> None:
    metrics = models.predictor.info.metrics
    assert metrics.accuracy > metrics.baseline_accuracy
    assert 0 < metrics.f1 <= 1
    assert sum(map(sum, metrics.confusion_matrix)) == metrics.test_samples


# --- Anomaly detection -----------------------------------------------------------------------

VIRTUAL_STATES = (
    [("light", LightState(is_on=o, brightness=b)) for o in (True, False) for b in range(1, 101, 3)]
    + [("fan", FanState(is_on=o, speed=s)) for o in (True, False) for s in range(1, 101, 3)]
    + [("ac", AcState(is_on=o, target_temperature_c=t)) for o in (True, False) for t in range(16, 31)]
    + [("door_lock", DoorLockState(is_locked=lock)) for lock in (True, False)]
)


def test_normal_readings_from_every_virtual_state_are_not_anomalies(models) -> None:
    flagged = [
        (kind, state)
        for kind, state in VIRTUAL_STATES
        if models.detector.assess(kind, setting_level(kind, state.model_dump()), _power_for(kind, state)).is_anomaly
    ]
    assert flagged == []


def test_injected_anomaly_is_flagged_with_score_and_range(models) -> None:
    level = setting_level("fan", {"is_on": True, "speed": 60})

    normal = models.detector.assess("fan", level, 40.8)
    surge = models.detector.assess("fan", level, 170)

    assert normal.is_anomaly is False and normal.score > 0
    assert surge.is_anomaly is True and surge.score < 0
    assert surge.expected_range.min <= 40.8 <= surge.expected_range.max
    assert surge.expected_range.max < 170


@pytest.mark.parametrize(
    ("kind", "state", "power"),
    [
        ("fan", {"is_on": True, "speed": 60}, 2.0),  # stalled motor
        ("light", {"is_on": False}, 45.0),  # drawing power while off
        ("ac", {"is_on": False}, 600.0),
    ],
)
def test_other_fault_patterns_are_flagged(models, kind, state, power) -> None:
    assert models.detector.assess(kind, setting_level(kind, state), power).is_anomaly


def test_detector_metrics_are_reported_per_device(models) -> None:
    info = models.detector.info
    assert info.model == "isolation_forest_v1"
    assert set(info.metrics) == {"light", "fan", "ac", "door_lock"}
    for metrics in info.metrics.values():
        assert metrics.false_positive_rate < 0.02
        assert metrics.recall > 0.5
