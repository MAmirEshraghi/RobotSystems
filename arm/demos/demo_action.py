#!/usr/bin/env python3
# coding: utf-8
"""
Demo for the "separate action" check-in.

Run on the arm Pi with:
  sudo python3 arm/demos/demo_action.py

What it shows:
- Motion class can home, open/close gripper, and move to a safe point.
"""
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.motion import Motion  # noqa


def main():
    m = Motion()
    print("Homing...")
    m.home()
    time.sleep(0.5)

    print("Open gripper...")
    m.open_gripper()
    time.sleep(0.5)

    print("Close gripper...")
    m.close_gripper()
    time.sleep(0.5)

    print("Move to a safe point (0, 15, 10)...")
    ok, _ = m.move_to(0, 15, 10, pitch=-60, roll=-60, yaw=0, duration_ms=1200)
    print("Move ok:", ok)
    time.sleep(0.5)

    print("Back home...")
    m.home()
    print("Done.")


if __name__ == "__main__":
    main()
