"""
Ultrasonic sensor wrapper.

The underlying SunFounder Ultrasonic returns distance in centimeters, and may
return -1 or -2 for errors (see robot_hat/modules.Ultrasonic._read()).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UltrasonicSensor:
    car: object
    max_tries: int = 3

    def read_cm(self) -> Optional[float]:
        # Picarx exposes self.ultrasonic = Ultrasonic(...)
        d = self.car.px.ultrasonic.read(times=self.max_tries)
        # error codes are negative
        if d is None:
            return None
        try:
            d = float(d)
        except Exception:
            return None
        if d <= 0:
            return None
        return d
