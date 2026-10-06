"""Energy anomaly detection with one Isolation Forest per device type.

Each model learns the normal relationship between a device's setting (0-100) and its
power draw. A reading is anomalous when its Isolation Forest score falls below a
threshold learned from normal training readings. The expected range reported with
each result comes from the same normal readings, binned by setting.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.ml.dataset import Dataset
from app.ml.features import POWER_FEATURES
from app.ml.models import DetectionMetrics, DetectorInfo, ExpectedRange

MODEL_NAME = "isolation_forest_v1"
CONTAMINATION = 0.02
NORMAL_PASS_QUANTILE = 0.002  # 99.8% of normal training readings stay below the alarm
LEVEL_BIN = 10


class DetectorNotTrainedError(RuntimeError):
    pass


@dataclass
class _DeviceModel:
    forest: IsolationForest
    threshold: float
    ranges: dict[int, tuple[float, float]]
    fallback: tuple[float, float]


@dataclass(frozen=True)
class Assessment:
    is_anomaly: bool
    score: float
    expected_range: ExpectedRange


def _bin(level: float) -> int:
    return int(round(level / LEVEL_BIN))


class EnergyAnomalyDetector:
    def __init__(self, *, seed: int = 13) -> None:
        self._seed = seed
        self._models: dict[str, _DeviceModel] = {}
        self.info: DetectorInfo | None = None

    @property
    def device_types(self) -> list[str]:
        return list(self._models)

    def train(self, datasets: dict[str, Dataset]) -> DetectorInfo:
        metrics: dict[str, DetectionMetrics] = {}
        samples: dict[str, int] = {}
        for device_type, dataset in datasets.items():
            x_train, x_test, y_train, y_test = train_test_split(
                dataset.features, dataset.labels, test_size=0.3, random_state=self._seed, stratify=dataset.labels
            )
            forest = IsolationForest(n_estimators=100, contamination=CONTAMINATION, random_state=self._seed)
            forest.fit(x_train)

            normal_train = x_train[y_train == 0]
            threshold = float(np.quantile(forest.decision_function(normal_train), NORMAL_PASS_QUANTILE))

            bins: dict[int, list[float]] = {}
            for level, power in normal_train:
                bins.setdefault(_bin(level), []).append(power)
            ranges = {
                b: (float(np.quantile(values, 0.005)), float(np.quantile(values, 0.995))) for b, values in bins.items()
            }
            fallback = (float(normal_train[:, 1].min()), float(normal_train[:, 1].max()))
            self._models[device_type] = _DeviceModel(forest, threshold, ranges, fallback)

            predicted = (forest.decision_function(x_test) < threshold).astype(int)
            negatives = y_test == 0
            metrics[device_type] = DetectionMetrics(
                precision=round(float(precision_score(y_test, predicted, zero_division=0)), 4),
                recall=round(float(recall_score(y_test, predicted, zero_division=0)), 4),
                f1=round(float(f1_score(y_test, predicted, zero_division=0)), 4),
                false_positive_rate=round(float(predicted[negatives].mean()) if negatives.any() else 0.0, 4),
                test_samples=len(y_test),
                injected_anomalies=int(y_test.sum()),
            )
            samples[device_type] = len(x_train)

        self.info = DetectorInfo(
            model=MODEL_NAME,
            algorithm="IsolationForest (100 trees) per device type",
            device_types=list(self._models),
            features=list(POWER_FEATURES),
            training_samples=samples,
            contamination=CONTAMINATION,
            metrics=metrics,
        )
        return self.info

    def assess(self, device_type: str, level: float, power_w: float) -> Assessment:
        model = self._models.get(device_type)
        if model is None:
            raise DetectorNotTrainedError(f"No anomaly model for device type '{device_type}'.")
        raw = float(model.forest.decision_function(np.array([[level, power_w]], dtype=float))[0])
        score = raw - model.threshold
        low, high = model.ranges.get(_bin(level), model.fallback)
        return Assessment(
            is_anomaly=score < 0,
            score=round(score, 4),
            expected_range=ExpectedRange(min=round(low, 2), max=round(high, 2)),
        )
