"""MLService: the single entry point to IntelliHome's ML.

    HomeState snapshot ──► features ──► FanUsagePredictor     ──► Prediction
    device power + state ──────────────► EnergyAnomalyDetector ──► AnomalyResult ──► EventStore (source=ml)

ML recommends and detects. It never executes a device command; there is no reference
to CommandService here by design.
"""

import logging
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.devices.base import DeviceSnapshot
from app.domain.home_state import HomeState, HomeStateSnapshot
from app.events.models import CommandSource, DeviceEvent
from app.events.store import EventStore
from app.ml.anomaly import MODEL_NAME as ANOMALY_MODEL
from app.ml.anomaly import EnergyAnomalyDetector
from app.ml.dataset import generate_fan_dataset, generate_power_dataset
from app.ml.errors import InvalidFeatureError, PredictionNotSupportedError
from app.ml.features import FAN_DEVICE_ID, describe_setting, fan_features, feature_errors, setting_level
from app.ml.models import (
    SIMULATED_DATA_NOTE,
    AnomalyReport,
    AnomalyResult,
    MLInsights,
    MLStatus,
    Prediction,
)
from app.ml.prediction import FanUsagePredictor

logger = logging.getLogger(__name__)

ENERGY_ANOMALY = "energy_anomaly"


@dataclass(frozen=True)
class TrainedModels:
    predictor: FanUsagePredictor
    detector: EnergyAnomalyDetector
    trained_at: datetime


@lru_cache(maxsize=4)
def train_models(seed: int = 7, days: int = 60, threshold: float = 0.5) -> TrainedModels:
    """Train both models on deterministic simulated data. Cached per process: models are read-only."""
    predictor = FanUsagePredictor(threshold=threshold)
    predictor.train(generate_fan_dataset(days=days, seed=seed))
    detector = EnergyAnomalyDetector()
    detector.train(generate_power_dataset(seed=seed + 4))
    logger.info("ML models trained (seed=%s, days=%s)", seed, days)
    return TrainedModels(predictor, detector, datetime.now(UTC))


class MLService:
    def __init__(
        self,
        home: HomeState,
        events: EventStore,
        models: TrainedModels,
        *,
        clock: Callable[[], datetime] = datetime.now,
        active_window: timedelta = timedelta(minutes=15),
        recent_limit: int = 20,
    ) -> None:
        self._home = home
        self._events = events
        self._models = models
        self._clock = clock
        self._active_window = active_window
        self._recent: deque[AnomalyResult] = deque(maxlen=recent_limit)
        self._live_flagged: set[str] = set()

    @property
    def prediction_devices(self) -> list[str]:
        return [FAN_DEVICE_ID]

    # --- Prediction ----------------------------------------------------------------------

    def predict(
        self,
        device_id: str = FAN_DEVICE_ID,
        *,
        overrides: Mapping[str, float | None] | None = None,
        snapshot: HomeStateSnapshot | None = None,
    ) -> Prediction:
        if device_id not in self.prediction_devices:
            raise PredictionNotSupportedError(device_id, self.prediction_devices)
        device = self._home.devices.get(device_id)
        snapshot = snapshot or self._home.snapshot()
        features = fan_features(snapshot, self._clock(), self._events.recent(limit=50), fan_id=device_id)
        if overrides:
            errors = feature_errors(overrides)
            if errors:
                raise InvalidFeatureError(
                    "Invalid features: " + "; ".join(f"{e['feature']}: {e['message']}" for e in errors), errors
                )
            features.update(overrides)
        try:
            return self._models.predictor.predict(features, device_name=device.name, now=datetime.now(UTC))
        except ValueError as exc:
            raise InvalidFeatureError(str(exc)) from exc

    def predictions(self, snapshot: HomeStateSnapshot | None = None) -> list[Prediction]:
        return [self.predict(device_id, snapshot=snapshot) for device_id in self.prediction_devices]

    # --- Anomaly detection ---------------------------------------------------------------

    def _assess(self, device: DeviceSnapshot, power_w: float, source: str, timestamp: datetime) -> AnomalyResult:
        level = setting_level(device.device_type, device.state)
        assessment = self._models.detector.assess(device.device_type, level, power_w)
        setting = describe_setting(device.device_type, device.state)
        low, high = assessment.expected_range.min, assessment.expected_range.max
        if assessment.is_anomaly:
            explanation = (
                f"Isolation Forest classified this reading as anomalous: the {device.name} drew {power_w:.1f} W while "
                f"{setting}, outside its learned normal range of {low:.1f}–{high:.1f} W at this setting."
            )
        else:
            explanation = (
                f"Within the learned normal pattern: {power_w:.1f} W while {setting} (normal {low:.1f}–{high:.1f} W)."
            )
        return AnomalyResult(
            device_id=device.id,
            device_name=device.name,
            device_type=device.device_type,
            is_anomaly=assessment.is_anomaly,
            score=assessment.score,
            observed_power_watts=round(power_w, 2),
            expected_range=assessment.expected_range,
            setting=setting,
            source=source,
            timestamp=timestamp,
            explanation=explanation,
            model=ANOMALY_MODEL,
        )

    def _record(self, result: AnomalyResult, device: DeviceSnapshot) -> AnomalyResult:
        """Log an anomaly in the existing event system (source=ml, no state change)."""
        event = DeviceEvent(
            device_id=device.id,
            action=ENERGY_ANOMALY,
            event_type=ENERGY_ANOMALY,
            value=result.observed_power_watts,
            previous_state=device.state,
            new_state=device.state,
            source=CommandSource.ML,
            timestamp=result.timestamp,
            details={
                "score": result.score,
                "expected_range": result.expected_range.model_dump(),
                "setting": result.setting,
                "origin": result.source,
                "model": result.model,
            },
        )
        self._events.append(event)
        logger.warning("energy anomaly: %s", result.explanation)
        return result.model_copy(update={"event_id": event.event_id})

    def scan(self, snapshot: HomeStateSnapshot | None = None) -> list[AnomalyResult]:
        """Assess every device's current power. Logs an event when a device *becomes* anomalous."""
        snapshot = snapshot or self._home.snapshot()
        now = datetime.now(UTC)
        results = []
        for device in snapshot.devices:
            result = self._assess(device, device.power_w, "live", now)
            if result.is_anomaly and device.id not in self._live_flagged:
                self._live_flagged.add(device.id)
                result = self._record(result, device)
                self._recent.append(result)
            elif not result.is_anomaly:
                self._live_flagged.discard(device.id)
            results.append(result)
        return results

    def check_reading(self, device_id: str, power_w: float, timestamp: datetime | None = None) -> AnomalyResult:
        """Assess an externally reported power reading (e.g. a future hardware power meter)."""
        self._home.devices.get(device_id)  # raises DeviceNotFoundError for unknown devices
        device = next(d for d in self._home.snapshot().devices if d.id == device_id)
        result = self._assess(device, power_w, "reading", timestamp or datetime.now(UTC))
        if result.is_anomaly:
            result = self._record(result, device)
            self._recent.append(result)
        return result

    def anomaly_report(self, snapshot: HomeStateSnapshot | None = None) -> AnomalyReport:
        live = self.scan(snapshot)
        now = datetime.now(UTC)
        recent = list(reversed(self._recent))
        active = [r for r in recent if now - r.timestamp <= self._active_window]
        return AnomalyReport(
            checked_at=now, live=live, recent=recent, active=active, active_count=len(active), model=ANOMALY_MODEL
        )

    # --- For the AI agent and status -----------------------------------------------------

    def insights(self, snapshot: HomeStateSnapshot | None = None) -> MLInsights:
        """Predictions and anomalies from one snapshot, so every consumer sees the same numbers."""
        snapshot = snapshot or self._home.snapshot()
        return MLInsights(predictions=self.predictions(snapshot), anomalies=self.anomaly_report(snapshot))

    def status(self) -> MLStatus:
        return MLStatus(
            enabled=True,
            predictor=self._models.predictor.info,
            detector=self._models.detector.info,
            data_note=SIMULATED_DATA_NOTE,
            trained_at=self._models.trained_at,
        )
