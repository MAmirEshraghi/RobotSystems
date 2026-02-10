import time
import logging

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

class PController:
    """Proportional steering controller.

    Expects offset in [-1, 1] where + means line is to the left, - to the right.
    Outputs steering angle in degrees.
    """
    def __init__(self, gain_deg: float = 28.0, max_angle_deg: float = 30.0):
        self.gain_deg = float(gain_deg)
        self.max_angle_deg = float(max_angle_deg)

    def steering_angle_deg(self, offset: float) -> float:
        angle = self.gain_deg * float(offset)
        return clamp(angle, -self.max_angle_deg, self.max_angle_deg)

def set_up_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

def rate_limit_hz(hz: float):
    """Return a function sleep() that enforces approx loop frequency."""
    period = 1.0 / float(hz)
    last = time.time()
    def sleep():
        nonlocal last
        now = time.time()
        dt = now - last
        if dt < period:
            time.sleep(period - dt)
        last = time.time()
    return sleep
