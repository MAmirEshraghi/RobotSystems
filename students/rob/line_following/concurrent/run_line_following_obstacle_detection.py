#!/usr/bin/env python3
"""
Week 5 demo: line following with obstacle detection.

Runs TWO concurrent pipelines:
1) Line following (grayscale or camera): sensor -> interpreter -> steering controller
2) Obstacle detection (ultrasonic): sensor -> interpreter(stop flag) -> speed controller

A final drive consumer applies (steering angle, speed) to the car.
"""
from __future__ import annotations

import argparse
import logging
import time
import csv
from threading import Event

from students.rob.picarx_improved import Car
from students.rob.line_following.common.controller import PController, set_up_logging
from students.rob.line_following.grayscale.sensor import GrayscaleSensor
from students.rob.line_following.grayscale.interpreter import GrayscaleInterpreter
from students.rob.line_following.camera.sensor import CameraSensor
from students.rob.line_following.camera.interpreter import CameraInterpreter
from students.rob.line_following.ultrasonic.sensor import UltrasonicSensor
from students.rob.line_following.ultrasonic.interpreter import UltrasonicStopInterpreter

from students.rob.line_following.concurrent.bus import Bus, HardwareLock
from students.rob.line_following.concurrent.tasks import Producer, ConsumerProducer, Consumer, Timer
from students.rob.line_following.concurrent.runner import ConcurrentRunner


class TelemetryCSV:
    def __init__(self, path: str, fieldnames: list[str]):
        self._f = open(path, "w", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=fieldnames)
        self._w.writeheader()
        self._f.flush()

    def write(self, row: dict):
        self._w.writerow(row)
        self._f.flush()

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lf_sensor", choices=["grayscale", "camera"], default="grayscale")
    ap.add_argument("--speed", type=float, default=22.0, help="base forward speed (0-100)")
    ap.add_argument("--polarity", choices=["dark_line", "light_line"], default="dark_line")
    ap.add_argument("--gain", type=float, default=28.0)

    ap.add_argument("--sensor_hz", type=float, default=25.0)
    ap.add_argument("--interp_hz", type=float, default=25.0)
    ap.add_argument("--ctrl_hz", type=float, default=35.0)
    ap.add_argument("--ultra_hz", type=float, default=15.0)
    ap.add_argument("--drive_hz", type=float, default=35.0)

    ap.add_argument("--stop_cm", type=float, default=20.0)
    ap.add_argument("--hysteresis_cm", type=float, default=6.0)

    # camera params
    ap.add_argument("--thresh", type=int, default=110)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--fps", type=int, default=30)

    ap.add_argument("--runtime_s", type=float, default=0.0)
    ap.add_argument("--csv", type=str, default="", help="optional telemetry CSV output path")
    ap.add_argument("--log", choices=["INFO", "DEBUG"], default="INFO")
    args = ap.parse_args()

    set_up_logging(getattr(logging, args.log))
    log = logging.getLogger("obstacle_demo")

    shutdown_event = Event()
    terminate_bus = Bus[bool]("terminate", initial=False)

    # Single lock for I2C-heavy reads/writes (grayscale + ultrasonic + motors)
    hw_lock = HardwareLock()

    car = Car()
    cam = None

    # --- line following components
    if args.lf_sensor == "grayscale":
        lf_sensor = GrayscaleSensor(car)
        lf_interp = GrayscaleInterpreter(polarity=args.polarity)
        lf_values_bus = Bus("gray_values")
        def lf_produce():
            return lf_sensor.read()
        def lf_interpret(vals):
            return lf_interp.interpret(vals)
        telemetry_fields = ["t", "gray_l", "gray_c", "gray_r", "offset", "angle_deg", "base_speed", "drive_speed", "dist_cm", "stop"]
    else:
        cam = CameraSensor(width=args.width, height=args.height, fps=args.fps)
        lf_interp = CameraInterpreter(polarity=args.polarity, thresh=args.thresh)
        lf_values_bus = Bus("camera_frame")
        def lf_produce():
            return cam.read()
        def lf_interpret(frame):
            offset, _ = lf_interp.interpret(frame)
            return offset
        telemetry_fields = ["t", "offset", "angle_deg", "base_speed", "drive_speed", "dist_cm", "stop"]

    lf_offset_bus = Bus[float]("offset")
    lf_angle_bus = Bus[float]("angle_deg")

    ctrl = PController(gain_deg=args.gain)

    # --- ultrasonic components
    ultra_sensor = UltrasonicSensor(car=car)
    ultra_interp = UltrasonicStopInterpreter(stop_cm=args.stop_cm, hysteresis_cm=args.hysteresis_cm, invalid_is_clear=True)
    dist_bus = Bus[float]("dist_cm")
    stop_bus = Bus[bool]("stop_flag", initial=False)

    # --- speed arbitration
    base_speed_bus = Bus[float]("base_speed", initial=float(args.speed))
    drive_speed_bus = Bus[float]("drive_speed", initial=float(args.speed))

    def compute_drive_speed(base_speed: float, stop_flag: bool) -> float:
        return 0.0 if stop_flag else float(base_speed)

    telemetry = TelemetryCSV(args.csv, telemetry_fields) if args.csv else None

    # --- tasks
    lf_sensor_task = Producer(
        name=f"{args.lf_sensor}_sensor",
        delay_s=1.0 / max(args.sensor_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        output_bus=lf_values_bus,
        produce=lf_produce,
        hardware_lock=hw_lock if args.lf_sensor == "grayscale" else None,
    )

    lf_interp_task = ConsumerProducer(
        name=f"{args.lf_sensor}_interpreter",
        delay_s=1.0 / max(args.interp_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[lf_values_bus],
        output_buses=[lf_offset_bus],
        transform=lf_interpret,
    )

    lf_steer_task = ConsumerProducer(
        name="steering_controller",
        delay_s=1.0 / max(args.ctrl_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[lf_offset_bus],
        output_buses=[lf_angle_bus],
        transform=lambda off: ctrl.steering_angle_deg(off),
    )

    ultra_task = Producer(
        name="ultrasonic_sensor",
        delay_s=1.0 / max(args.ultra_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        output_bus=dist_bus,
        produce=lambda: ultra_sensor.read_cm(),
        hardware_lock=hw_lock,
    )

    stop_interp_task = ConsumerProducer(
        name="ultrasonic_interpreter",
        delay_s=1.0 / max(args.ultra_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[dist_bus],
        output_buses=[stop_bus],
        transform=lambda d: ultra_interp.interpret_stop(d),
    )

    speed_task = ConsumerProducer(
        name="speed_controller",
        delay_s=1.0 / max(args.ultra_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[base_speed_bus, stop_bus],
        output_buses=[drive_speed_bus],
        transform=compute_drive_speed,
    )

    def drive(angle_deg: float, speed: float) -> None:
        car.steer(angle_deg)
        if speed > 0:
            car.forward(speed)
        else:
            car.stop()

        if telemetry is not None:
            row = {
                "t": time.time(),
                "angle_deg": angle_deg,
                "base_speed": base_speed_bus.read(),
                "drive_speed": speed,
                "dist_cm": dist_bus.read(),
                "stop": stop_bus.read(),
            }
            off = lf_offset_bus.read()
            if off is not None:
                row["offset"] = float(off)
            if args.lf_sensor == "grayscale":
                vals = lf_values_bus.read()
                if vals is not None:
                    row.update({"gray_l": vals[0], "gray_c": vals[1], "gray_r": vals[2]})
            telemetry.write(row)

    drive_task = Consumer(
        name="drive_actuation",
        delay_s=1.0 / max(args.drive_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[lf_angle_bus, drive_speed_bus],
        consume=drive,
        hardware_lock=hw_lock,
    )

    tasks = [
        lf_sensor_task.run,
        lf_interp_task.run,
        lf_steer_task.run,
        ultra_task.run,
        stop_interp_task.run,
        speed_task.run,
        drive_task.run,
    ]

    if args.runtime_s and args.runtime_s > 0:
        timer_task = Timer(
            name="timer",
            delay_s=0.1,
            shutdown_event=shutdown_event,
            termination_bus=terminate_bus,
            output_bus=terminate_bus,
            produce=lambda: False,
            duration_s=float(args.runtime_s),
        )
        tasks.append(timer_task.run)

    log.info("Starting line following + obstacle detection (%s). Ctrl+C to stop.", args.lf_sensor)
    try:
        runner = ConcurrentRunner(tasks=tasks, shutdown_event=shutdown_event, max_workers=len(tasks))
        runner.run()
    finally:
        terminate_bus.write(True)
        shutdown_event.set()

        try:
            car.stop()
            car.steer(0)
        except Exception:
            pass
        if cam is not None:
            try:
                cam.close()
            except Exception:
                pass
        if telemetry is not None:
            telemetry.close()

        log.info("Done.")

if __name__ == "__main__":
    main()
