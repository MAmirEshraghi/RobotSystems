"""
Ultrasonic interpreter that outputs a stop flag with hysteresis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UltrasonicStopInterpreter:
    stop_cm: float = 20.0
    hysteresis_cm: float = 5.0
    invalid_is_clear: bool = True

    def __post_init__(self) -> None:
        self._stopping = False

    def interpret_stop(self, distance_cm: Optional[float]) -> bool:
        # Treat invalid readings as "no update" or "clear" depending on preference
        if distance_cm is None:
            return False if self.invalid_is_clear else True

        d = float(distance_cm)

        if self._stopping:
            # resume only when we are comfortably far
            if d >= (self.stop_cm + self.hysteresis_cm):
                self._stopping = False
        else:
            if d <= self.stop_cm:
                self._stopping = True

        return self._stopping
