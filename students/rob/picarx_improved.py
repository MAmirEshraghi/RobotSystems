# students/rob/picarx_improved.py
import os
import atexit

# 1) Hardware import fallback (manual pattern)
try:
    from picarx import Picarx as _RealPicarx
    ON_ROBOT = True
except Exception:
    ON_ROBOT = False
    _RealPicarx = None


class Car:
    """
    Thin wrapper around Picarx with safety and a consistent interface
    for your maneuvers + tests.
    """

    def __init__(self):
        if not ON_ROBOT:
            raise RuntimeError(
                "Car() should only be constructed on the robot. "
                "For laptop tests, use FakeCar in your tests."
            )

        self.px = _RealPicarx()
        atexit.register(self.stop)

    # convenience wrappers you will use everywhere
    def steer(self, angle):
        self.px.set_dir_servo_angle(angle)

    def forward(self, speed):
        self.px.forward(speed)

    def backward(self, speed):
        self.px.backward(speed)

    def stop(self):
        try:
            self.px.stop()
        except Exception:
            pass
