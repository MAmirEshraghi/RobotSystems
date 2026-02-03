# students/rob/maneuvers.py
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DEFAULT_SPEED = 30
TURN_ANGLE = 25


def drive_for(car, seconds, speed, angle=0):
    log.info(f"cmd: steer={angle} speed={speed} t={seconds}")
    car.steer(angle)
    if speed >= 0:
        car.forward(speed)
    else:
        car.backward(abs(speed))
    time.sleep(seconds)
    car.stop()


def parallel_park_left(car):
    # simple time-based sequence (good enough for demo)
    drive_for(car, 0.6, +DEFAULT_SPEED, +TURN_ANGLE)
    drive_for(car, 0.9, -DEFAULT_SPEED, -2 * TURN_ANGLE)
    drive_for(car, 0.4, -DEFAULT_SPEED, 0)


def k_turn_left(car):
    drive_for(car, 0.8, +DEFAULT_SPEED, -2 * TURN_ANGLE)
    drive_for(car, 0.7, -DEFAULT_SPEED, +2 * TURN_ANGLE)
    drive_for(car, 0.6, +DEFAULT_SPEED, 0)
