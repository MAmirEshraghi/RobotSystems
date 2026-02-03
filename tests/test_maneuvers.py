# tests/test_maneuvers.py
from students.rob.maneuvers import parallel_park_left, k_turn_left


class FakeCar:
    def __init__(self):
        self.calls = []

    def steer(self, angle):
        self.calls.append(("steer", angle))

    def forward(self, speed):
        self.calls.append(("forward", speed))

    def backward(self, speed):
        self.calls.append(("backward", speed))

    def stop(self):
        self.calls.append(("stop",))


def test_parallel_park_left_ends_with_stop():
    car = FakeCar()
    parallel_park_left(car)
    assert car.calls[-1][0] == "stop"


def test_k_turn_left_has_multiple_moves():
    car = FakeCar()
    k_turn_left(car)
    # should have more than one forward/backward call
    moves = [c for c in car.calls if c[0] in ("forward", "backward")]
    assert len(moves) >= 2
