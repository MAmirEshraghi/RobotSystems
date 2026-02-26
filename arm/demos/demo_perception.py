#!/usr/bin/env python3
# coding: utf-8
"""
Demo for the "separate perception" check-in.

Run on the arm Pi with:
  sudo python3 arm/demos/demo_perception.py

What it shows:
- camera feed
- largest detected target block (red/green/blue by default)
- world coordinate overlay (after calibration)

Press 'q' to quit.
"""
import os
import sys
import time

# Make repo src importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception import Perception  # noqa

# Prefer vendor Camera class
if os.path.isdir("/home/pi/ArmPi"):
    sys.path.append("/home/pi/ArmPi")
else:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "ArmPi")))

import cv2  # type: ignore
import Camera  # type: ignore


def main():
    cam = Camera.Camera()
    cam.camera_open()
    time.sleep(0.2)

    percep = Perception(target_colors=("red", "green", "blue"), min_area=2500)

    while True:
        frame = cam.frame
        if frame is None:
            time.sleep(0.01)
            continue

        det = percep.detect_largest(frame)
        vis = percep.annotate(frame, det)

        cv2.imshow("Perception Demo (q to quit)", vis)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cam.camera_close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
