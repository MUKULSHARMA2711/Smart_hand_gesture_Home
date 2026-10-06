"""Predictive automation: will the living-room fan be needed soon?"""

from collections.abc import Mapping
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.ml.dataset import Dataset
from app.ml.features import FAN_DEVICE_ID, FEATURE_LABELS
from app.ml.models import ClassificationMetrics, FeatureFactor, Prediction, PredictorInfo

MODEL_NAME = "random_forest_v1"
TARGET = "FAN_ON_SOON"
_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class PredictorNotTrainedError(RuntimeError):
    pass


def describe_factor(feature: str, value: float | None, typical: float) -> str:
    """Human-readable input, e.g. 'Temperature 30.2 °C (typical 26.1 °C)'."""
    label = FEATURE_LABELS.get(feature, feature)
    if value is None:
        return f"{label} unknown"
    match feature:
        case "temperature_c":
            return f"{label} {value:.1f} °C (typical {typical:.1f} °C)"
        case "humidity_pct":
            return f"{label} {value:.0f}% (typical {typical:.0f}%)"
        case "occupied":
            return "Room occupied" if value >= 0.5 else "Room vacant"
        case "occupant_count":
            return f"{int(value)} {'person' if int(value) == 1 else 'people'} home"
        case "ambient_light_lux":
            return f"{label} {value:.0f} lux"
        case "hour":
            return f"Time {int(value):02d}:{int(round((value % 1) * 60)) % 60:02d}"
        case "day_of_week":
            return _DAYS[int(value) % 7]
        case "fan_on":
            return "Fan is on now" if value >= 0.5 else "Fan is off now"
        case "fan_recently_on":
            return "Fan used in the last 30 min" if value >= 0.5 else "Fan not used recently"
    return f"{label} {value}"


class FanUsagePredictor:
    """Random Forest classifier for FAN_ON_SOON (fan on within the next 30 minutes)."""

    def __init__(self, *, threshold: float = 0.5, seed: int = 42) -> None:
        self.threshold = threshold
        self._seed = seed
        self._model: RandomForestClassifier | None = None
        self._feature_names: tuple[str, ...] = ()
        self._medians: np.ndarray | None = None
        self._horizon = 30
        self.info: PredictorInfo | None = None

    def train(self, dataset: Dataset) -> PredictorInfo:
        x_train, x_test, y_train, y_test = train_test_split(
            dataset.features, dataset.labels, test_size=0.25, random_state=self._seed, stratify=dataset.labels
        )
        model = RandomForestClassifier(
            n_estimators=120, max_depth=8, min_samples_leaf=5, random_state=self._seed, n_jobs=1
        )
        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        majority = int(np.bincount(y_train).argmax())

        self._model = model
        self._feature_names = dataset.feature_names
        self._medians = np.median(x_train, axis=0)
        self._horizon = int(dataset.metadata.get("horizon_minutes", 30))
        self.info = PredictorInfo(
            model=MODEL_NAME,
            algorithm="RandomForestClassifier (120 trees, max depth 8)",
            target=TARGET,
            device_id=FAN_DEVICE_ID,
            features=list(dataset.feature_names),
            feature_importances={
                name: round(float(imp), 4) for name, imp in zip(dataset.feature_names, model.feature_importances_)
            },
            metrics=ClassificationMetrics(
                accuracy=round(float(accuracy_score(y_test, y_pred)), 4),
                precision=round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
                recall=round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
                f1=round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
                confusion_matrix=confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist(),
                baseline_accuracy=round(float(np.mean(y_test == majority)), 4),
                train_samples=len(y_train),
                test_samples=len(y_test),
            ),
            dataset=dataset.metadata,
        )
        return self.info

    def predict(self, features: Mapping[str, float | None], *, device_name: str, now: datetime) -> Prediction:
        if self._model is None or self._medians is None:
            raise PredictorNotTrainedError("The fan usage model has not been trained.")

        unknown = set(features) - set(self._feature_names)
        if unknown:
            raise ValueError(f"Unknown features: {sorted(unknown)}")

        # Missing inputs are imputed with the training median and reported.
        missing = [name for name in self._feature_names if features.get(name) is None]
        row = np.array(
            [features[name] if features.get(name) is not None else self._medians[i] for i, name in enumerate(self._feature_names)],
            dtype=float,
        )

        # One-at-a-time sensitivity: reset each input to its typical value, in one batch.
        variants = np.tile(row, (len(row) + 1, 1))
        for i in range(len(row)):
            variants[i + 1, i] = self._medians[i]
        probabilities = self._model.predict_proba(variants)[:, 1]
        probability = float(probabilities[0])

        importances = self._model.feature_importances_
        factors = sorted(
            (
                FeatureFactor(
                    feature=name,
                    label=FEATURE_LABELS.get(name, name),
                    value=None if name in missing else round(float(row[i]), 3),
                    typical=round(float(self._medians[i]), 3),
                    importance=round(float(importances[i]), 4),
                    effect=round(probability - float(probabilities[i + 1]), 4),
                    imputed=name in missing,
                    description=describe_factor(name, None if name in missing else float(row[i]), float(self._medians[i])),
                )
                for i, name in enumerate(self._feature_names)
            ),
            key=lambda factor: abs(factor.effect),
            reverse=True,
        )
        top = [f for f in factors if abs(f.effect) >= 0.01 and not f.imputed][:3]
        percent = round(probability * 100)
        reasons = "; ".join(f.description for f in top) if top else "no single input stands out"
        explanation = (
            f"Random Forest predicted a {percent}% probability that the {device_name} will be needed within "
            f"{self._horizon} minutes. Main factors: {reasons}."
        )
        return Prediction(
            device_id=FAN_DEVICE_ID,
            device_name=device_name,
            target=TARGET,
            prediction="ON" if probability >= self.threshold else "OFF",
            probability=round(probability, 4),
            threshold=self.threshold,
            horizon_minutes=self._horizon,
            features={name: (None if name in missing else round(float(row[i]), 3)) for i, name in enumerate(self._feature_names)},
            missing_features=missing,
            factors=factors,
            reason_features={f.feature: f.value for f in top},
            explanation=explanation,
            model=MODEL_NAME,
            generated_at=now,
        )
