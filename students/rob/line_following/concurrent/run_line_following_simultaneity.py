#!/usr/bin/env python3
"""
Week 4 demo: line following with simultaneity.

Implements the manual's architecture:
- busses (broadcast)
- producer / consumer-producer / consumer loops
- concurrent execution with ThreadPoolExecutor
- graceful shutdown + exception reporting
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
    ap.add_argument("--speed", type=float, default=25.0, help="forward speed (0-100)")
    ap.add_argument("--polarity", choices=["dark_line", "light_line"], default="dark_line")
    ap.add_argument("--gain", type=float, default=28.0, help="steering gain (deg per unit offset)")

    ap.add_argument("--sensor_hz", type=float, default=30.0)
    ap.add_argument("--interp_hz", type=float, default=30.0)
    ap.add_argument("--ctrl_hz", type=float, default=40.0)
    ap.add_argument("--drive_hz", type=float, default=40.0)

    # camera params
    ap.add_argument("--thresh", type=int, default=110)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--fps", type=int, default=30)

    # runtime
    ap.add_argument("--runtime_s", type=float, default=0.0, help="auto-stop after N seconds (0 = Ctrl+C)")
    ap.add_argument("--csv", type=str, default="", help="optional telemetry CSV output path")
    ap.add_argument("--log", choices=["INFO", "DEBUG"], default="INFO")
    args = ap.parse_args()

    set_up_logging(getattr(logging, args.log))
    log = logging.getLogger("simultaneity")

    shutdown_event = Event()
    terminate_bus = Bus[bool]("terminate", initial=False)

    # Serialize I2C-heavy operations to reduce garbage readings (grayscale + motors share I2C)
    hw_lock = HardwareLock()

    car = Car()
    cam = None

    # --- choose line-following sensor + interpreter
    if args.lf_sensor == "grayscale":
        sensor = GrayscaleSensor(car)
        interp = GrayscaleInterpreter(polarity=args.polarity)
        values_bus = Bus("gray_values")
        def produce_values():
            return sensor.read()
        def interpret_values(vals):
            return interp.interpret(vals)
        telemetry_fields = ["t", "gray_l", "gray_c", "gray_r", "offset", "angle_deg", "speed"]
    else:
        cam = CameraSensor(width=args.width, height=args.height, fps=args.fps)
        interp = CameraInterpreter(polarity=args.polarity, thresh=args.thresh)
        values_bus = Bus("camera_frame")
        def produce_values():
            return cam.read()
        def interpret_values(frame):
            offset, _meta = interp.interpret(frame)
            return offset
        telemetry_fields = ["t", "offset", "angle_deg", "speed"]

    offset_bus = Bus[float]("offset")
    angle_bus = Bus[float]("angle_deg")
    speed_bus = Bus[float]("speed", initial=float(args.speed))

    telemetry = TelemetryCSV(args.csv, telemetry_fields) if args.csv else None

    ctrl = PController(gain_deg=args.gain)

    # --- tasks
    sensor_task = Producer(
        name=f"{args.lf_sensor}_sensor",
        delay_s=1.0 / max(args.sensor_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        output_bus=values_bus,
        produce=produce_values,
        hardware_lock=hw_lock if args.lf_sensor == "grayscale" else None,
    )

    interp_task = ConsumerProducer(
        name=f"{args.lf_sensor}_interpreter",
        delay_s=1.0 / max(args.interp_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[values_bus],
        output_buses=[offset_bus],
        transform=interpret_values,
    )

    steer_task = ConsumerProducer(
        name="steering_controller",
        delay_s=1.0 / max(args.ctrl_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[offset_bus],
        output_buses=[angle_bus],
        transform=lambda off: ctrl.steering_angle_deg(off),
    )

    def drive(angle_deg: float, speed: float) -> None:
        car.steer(angle_deg)
        if speed > 0:
            car.forward(speed)
        else:
            car.stop()

        if telemetry is not None:
            row = {"t": time.time(), "angle_deg": angle_deg, "speed": speed}
            if args.lf_sensor == "grayscale":
                vals = values_bus.read()
                off = offset_bus.read()
                if vals is not None:
                    row.update({"gray_l": vals[0], "gray_c": vals[1], "gray_r": vals[2]})
                if off is not None:
                    row["offset"] = float(off)
            else:
                off = offset_bus.read()
                if off is not None:
                    row["offset"] = float(off)
            telemetry.write(row)

    drive_task = Consumer(
        name="drive_actuation",
        delay_s=1.0 / max(args.drive_hz, 1e-6),
        shutdown_event=shutdown_event,
        termination_bus=terminate_bus,
        input_buses=[angle_bus, speed_bus],
        consume=drive,
        hardware_lock=hw_lock,
    )

    tasks = [sensor_task.run, interp_task.run, steer_task.run, drive_task.run]

    # Optional timer (manual's RossROS Timer idea)
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

    log.info("Starting line following with simultaneity (%s). Ctrl+C to stop.", args.lf_sensor)
    try:
        runner = ConcurrentRunner(tasks=tasks, shutdown_event=shutdown_event, max_workers=len(tasks))
        runner.run()
    finally:
        # ensure the termination bus is True so loops end quickly
        terminate_bus.write(True)
        shutdown_event.set()

        # clean up hardware
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
