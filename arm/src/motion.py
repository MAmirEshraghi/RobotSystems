#!/usr/bin/env python3
# coding: utf-8
"""arm/src/motion.py

Separated *action* code for the ArmPi.

Purpose (Week 8 / action separation check-in):
- Keep vendor code untouched under arm/vendor/ArmPi (and/or /home/pi/ArmPi on the Pi image)
- Provide a small, clean Motion interface you can call from your own scripts
- Demonstrate motion primitives (home, move, gripper open/close) without perception

Run demo with:
  sudo python3 arm/demos/demo_action.py
"""

import os
import sys
import time

# Prefer the vendor install path used by their scripts
if os.path.isdir("/home/pi/ArmPi"):
    sys.path.append("/home/pi/ArmPi")
else:
    repo_vendor = os.path.join(os.path.dirname(__file__), "..", "vendor", "ArmPi")
    sys.path.append(os.path.abspath(repo_vendor))

import HiwonderSDK.Board as Board  # vendor hardware layer
from ArmIK.ArmMoveIK import ArmIK  # vendor IK / motion layer


class Motion:
    """Minimal, stable motion wrapper around the vendor ArmIK + Board APIs."""

    def __init__(self,
                 gripper_closed_pulse=500,
                 gripper_open_delta=280,
                 wrist_center_pulse=500):
        self.AK = ArmIK()
        self.gripper_closed = int(gripper_closed_pulse)
        self.gripper_open = int(gripper_closed_pulse - gripper_open_delta)
        self.wrist_center = int(wrist_center_pulse)

    # ---- Basic primitives ----

    def home(self):
        """Safe startup pose (matches the vendor initMove in ColorSorting)."""
        # Slightly open gripper, center wrist
        Board.setBusServoPulse(1, self.gripper_closed - 50, 300)
        Board.setBusServoPulse(2, self.wrist_center, 500)
        # Move arm to a safe pose above the mat
        self.AK.setPitchRangeMoving((0, 10, 10), -30, -30, -90, 1500)

    def open_gripper(self, duration_ms=300):
        Board.setBusServoPulse(1, self.gripper_open, int(duration_ms))

    def close_gripper(self, duration_ms=300):
        Board.setBusServoPulse(1, self.gripper_closed, int(duration_ms))

    def set_wrist(self, pulse, duration_ms=300):
        Board.setBusServoPulse(2, int(pulse), int(duration_ms))

    def move_to(self, x, y, z, pitch=-30, roll=-30, yaw=-90, duration_ms=1200):
        """Move end-effector to (x,y,z) in world coordinates using vendor IK.

        Returns (ok, result) where ok is True/False.
        """
        return self.AK.setPitchRangeMoving((float(x), float(y), float(z)),
                                          float(pitch), float(roll), float(yaw),
                                          int(duration_ms))

    @staticmethod
    def sleep(sec):
        time.sleep(sec)
