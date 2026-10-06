"""Result models returned by the ML layer (plain Pydantic, no framework coupling)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SIMULATED_DATA_NOTE = (
    "Trained on simulated history generated from IntelliHome's sensor and device models, "
    "because no physical sensor history exists yet. Metrics describe the simulation, not real-world accuracy."
)


class FeatureFactor(BaseModel):
    """How one input influenced this prediction (one-at-a-time sensitivity)."""

    feature: str
    label: str
    value: float | None
    typical: float = Field(description="Median of this feature in the training data.")
    importance: float = Field(description="Global Random Forest feature importance (0-1).")
    effect: float = Field(description="Change in probability caused by this input vs. its typical value.")
    imputed: bool = False
    description: str


class Prediction(BaseModel):
    device_id: str
    device_name: str
    target: str
    prediction: Literal["ON", "OFF"]
    probability: float = Field(ge=0, le=1)
    threshold: float
    horizon_minutes: int
    features: dict[str, float | None]
    missing_features: list[str]
    # False when sensor inputs were missing and imputed: the probability is then low-confidence.
    reliable: bool = True
    factors: list[FeatureFactor]
    reason_features: dict[str, float | None]
    explanation: str
    model: str
    generated_at: datetime


class ClassificationMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: list[list[int]] = Field(description="[[TN, FP], [FN, TP]] on the held-out test split.")
    baseline_accuracy: float = Field(description="Accuracy of always predicting the majority class.")
    train_samples: int
    test_samples: int


class PredictorInfo(BaseModel):
    model: str
    algorithm: str
    target: str
    device_id: str
    features: list[str]
    feature_importances: dict[str, float]
    metrics: ClassificationMetrics
    dataset: dict[str, float | int | str]


class ExpectedRange(BaseModel):
    min: float
    max: float


class AnomalyResult(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    is_anomaly: bool
    score: float = Field(description="Isolation Forest score relative to the learned threshold; below 0 is anomalous.")
    observed_power_watts: float
    expected_range: ExpectedRange
    setting: str
    source: Literal["live", "reading"]
    timestamp: datetime
    explanation: str
    model: str
    event_id: str | None = None


class DetectionMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    test_samples: int
    injected_anomalies: int


class DetectorInfo(BaseModel):
    model: str
    algorithm: str
    device_types: list[str]
    features: list[str]
    training_samples: dict[str, int]
    contamination: float
    metrics: dict[str, DetectionMetrics]


class AnomalyReport(BaseModel):
    checked_at: datetime
    live: list[AnomalyResult]
    recent: list[AnomalyResult]
    active: list[AnomalyResult] = Field(description="Anomalies detected within the active window.")
    active_count: int
    model: str


class MLInsights(BaseModel):
    """ML results computed once for an AI request, so the planner and the response agree."""

    predictions: list[Prediction]
    anomalies: AnomalyReport


class MLStatus(BaseModel):
    enabled: bool
    predictor: PredictorInfo | None
    detector: DetectorInfo | None
    data_note: str
    trained_at: datetime | None
