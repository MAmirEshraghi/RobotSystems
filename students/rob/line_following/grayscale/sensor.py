from typing import List

class GrayscaleSensor:
    """Reads the 3-channel grayscale module via Picarx.

    Returns [left, center, right] as integers (ADC-like readings).
    """
    def __init__(self, car):
        # car is students.rob.picarx_improved.Car
        self._car = car

    def read(self) -> List[int]:
        # SunFounder Picarx exposes get_grayscale_data()
        return self._car.px.get_grayscale_data()
