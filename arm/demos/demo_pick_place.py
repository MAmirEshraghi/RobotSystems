#!/usr/bin/env python3
# coding: utf-8
"""
Optional combined demo (perception + action).
Useful if your instructor expects "combine perception and motion for a basic pick-and-place".

Run:
  sudo python3 arm/demos/demo_pick_place.py

It will:
- detect the largest red/green/blue block
- if stable for a short moment, pick and place it to a fixed bin pose by color

Press 'q' to quit at any time.
"""
import os
import sys
import time
from collections import deque

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.perception import Perception
from src.motion import Motion, PlacePose

# Prefer vendor Camera class
if os.path.isdir("/home/pi/ArmPi"):
    sys.path.append("/home/pi/ArmPi")
else:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "ArmPi")))

import cv2  # type: ignore
import Camera  # type: ignore


PLACE_BY_COLOR = {
    "red": PlacePose(-14.5, 11.5, 1.5),
    "green": PlacePose(-14.5, 5.5, 1.5),
    "blue": PlacePose(-14.5, -0.5, 1.5),
}


def main():
    cam = Camera.Camera()
    cam.camera_open()
    time.sleep(0.2)

    percep = Perception(target_colors=("red", "green", "blue"), min_area=2500)
    motion = Motion()

    # stabilize detection a bit
    hist = deque(maxlen=10)
    last_pick_time = 0.0

    while True:
        frame = cam.frame
        if frame is None:
            time.sleep(0.01)
            continue

        det = percep.detect_largest(frame)
        vis = percep.annotate(frame, det)

        if det is not None:
            hist.append(det.world_xy)
        else:
            hist.clear()

        cv2.imshow("Pick&Place Demo (q to quit)", vis)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        # Trigger pick if stable and cooldown passed
        now = time.time()
        if det is None or det.color not in PLACE_BY_COLOR:
            continue
        if now - last_pick_time < 8.0:
            continue
        if len(hist) < hist.maxlen:
            continue

        # stability: max deviation small
        xs = [p[0] for p in hist]
        ys = [p[1] for p in hist]
        if (max(xs) - min(xs) > 1.0) or (max(ys) - min(ys) > 1.0):
            continue

        print(f"Picking {det.color} at {det.world_xy} ...")
        ok = motion.pick_and_place_simple(det.world_xy, PLACE_BY_COLOR[det.color])
        print("Pick&place ok:", ok)
        last_pick_time = time.time()
        hist.clear()

    cam.camera_close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
