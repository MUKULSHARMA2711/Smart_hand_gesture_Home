import time
from collections.abc import Callable

_WATT_SECONDS_PER_KWH = 3_600_000


class EnergyMeter:
    """Integrates power draw over time into consumed energy (kWh).

    Power only changes when a device changes state, so callers must call
    :meth:`accumulate` with the current draw right *before* any change.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._last_sample = clock()
        self._energy_kwh = 0.0

    def accumulate(self, power_w: float) -> None:
        now = self._clock()
        elapsed_s = max(0.0, now - self._last_sample)
        self._energy_kwh += power_w * elapsed_s / _WATT_SECONDS_PER_KWH
        self._last_sample = now

    @property
    def energy_kwh(self) -> float:
        return self._energy_kwh
