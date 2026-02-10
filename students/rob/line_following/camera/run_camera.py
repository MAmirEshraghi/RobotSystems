import argparse
import logging
import cv2

from students.rob.picarx_improved import Car
from students.rob.line_following.common.controller import PController, set_up_logging, rate_limit_hz
from students.rob.line_following.camera.sensor import CameraSensor
from students.rob.line_following.camera.interpreter import CameraInterpreter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=22.0)
    ap.add_argument("--hz", type=float, default=15.0)
    ap.add_argument("--polarity", choices=["dark_line", "light_line"], default="dark_line")
    ap.add_argument("--gain", type=float, default=26.0)
    ap.add_argument("--thresh", type=int, default=110)
    ap.add_argument("--show", action="store_true", help="show debug windows (needs desktop/VNC)")
    ap.add_argument("--log", choices=["INFO", "DEBUG"], default="INFO")
    args = ap.parse_args()

    set_up_logging(getattr(logging, args.log))
    log = logging.getLogger(__name__)

    car = Car()
    cam = CameraSensor(width=320, height=240, fps=30)
    interp = CameraInterpreter(polarity=args.polarity, thresh=args.thresh)
    ctrl = PController(gain_deg=args.gain)

    sleep = rate_limit_hz(args.hz)

    log.info("Starting camera line follower (Ctrl+C to stop)")
    try:
        while True:
            frame = cam.read()
            offset, meta = interp.interpret(frame)
            angle = ctrl.steering_angle_deg(offset)

            car.steer(angle)
            car.forward(args.speed)

            if args.show and meta is not None:
                roi = meta["roi"]
                mask = meta["mask"]
                # draw center line on ROI
                h, w = roi.shape[:2]
                cv2.line(roi, (w//2, 0), (w//2, h), (0, 255, 0), 1)
                if meta.get("found", False) and "x_mean" in meta:
                    xm = int(meta["x_mean"])
                    cv2.line(roi, (xm, 0), (xm, h), (0, 0, 255), 2)
                cv2.imshow("roi", roi)
                cv2.imshow("mask", mask)
                cv2.waitKey(1)

            log.debug(f"offset={offset:.3f} angle={angle:.1f}")
            sleep()
    except KeyboardInterrupt:
        log.info("Stopping...")
    finally:
        cam.close()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        car.stop()
        car.steer(0)

if __name__ == "__main__":
    main()
