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


def _print_calls(title, calls):
    print(f"\n{title}")
    for c in calls:
        print(c)


def test_parallel_park_left_ends_with_stop():
    car = FakeCar()
    parallel_park_left(car)

    # Visible trace for checkoff/demo
    _print_calls("parallel_park_left command sequence:", car.calls)

    # Assertions (offline verification)
    assert any(c[0] == "steer" for c in car.calls)
    assert any(c[0] in ("forward", "backward") for c in car.calls)
    assert car.calls[-1][0] == "stop"


def test_k_turn_left_has_multiple_moves():
    car = FakeCar()
    k_turn_left(car)

    # Keep this one quiet (or print if you want)
    moves = [c for c in car.calls if c[0] in ("forward", "backward")]
    assert len(moves) >= 2