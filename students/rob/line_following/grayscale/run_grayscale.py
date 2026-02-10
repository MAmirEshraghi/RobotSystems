import argparse
import logging

from students.rob.picarx_improved import Car
from students.rob.line_following.common.controller import PController, set_up_logging, rate_limit_hz
from students.rob.line_following.grayscale.sensor import GrayscaleSensor
from students.rob.line_following.grayscale.interpreter import GrayscaleInterpreter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=25.0, help="forward speed (0-100)")
    ap.add_argument("--hz", type=float, default=20.0, help="control loop rate")
    ap.add_argument("--polarity", choices=["dark_line", "light_line"], default="dark_line")
    ap.add_argument("--gain", type=float, default=28.0, help="steering gain (deg per unit offset)")
    ap.add_argument("--log", choices=["INFO", "DEBUG"], default="INFO")
    args = ap.parse_args()

    set_up_logging(getattr(logging, args.log))
    log = logging.getLogger(__name__)

    car = Car()
    sensor = GrayscaleSensor(car)
    interp = GrayscaleInterpreter(polarity=args.polarity)
    ctrl = PController(gain_deg=args.gain)

    sleep = rate_limit_hz(args.hz)

    log.info("Starting grayscale line follower (Ctrl+C to stop)")
    try:
        while True:
            vals = sensor.read()
            offset = interp.interpret(vals)
            angle = ctrl.steering_angle_deg(offset)

            car.steer(angle)
            car.forward(args.speed)

            log.debug(f"vals={vals} offset={offset:.3f} angle={angle:.1f}")
            sleep()
    except KeyboardInterrupt:
        log.info("Stopping...")
    finally:
        car.stop()
        car.steer(0)

if __name__ == "__main__":
    main()
