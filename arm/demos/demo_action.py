#!/usr/bin/env python3
# coding: utf-8
"""arm/demos/demo_action.py

Week 8 in-class check-in: Demonstrate having separated out the action code.

What this demo proves:
- You can move the arm using *your* module (arm/src/motion.py)
- No perception is involved
- Vendor scripts remain untouched

Run on the Arm Pi:
  sudo python3 arm/demos/demo_action.py
"""

import os
import sys
import time

# allow: from src.motion import Motion
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.motion import Motion  # noqa


def main():
    m = Motion()

    print("1) Home pose")
    m.home()
    time.sleep(1.0)

    print("2) Open / close gripper (no motion)")
    m.open_gripper()
    time.sleep(0.8)
    m.close_gripper()
    time.sleep(0.8)

    print("3) Small safe move (no pick/place)")
    # Safe-ish point above the mat; adjust if your setup differs
    ret = m.move_to(0, 15, 10, pitch=-60, roll=-60, yaw=0, duration_ms=1200)
    print("move_to returned:", ret)
    time.sleep(1.0)

    print("4) Back home")
    m.home()
    print("Done.")


if __name__ == "__main__":
    main()
