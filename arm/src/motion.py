#!/usr/bin/env python3
# coding: utf-8
"""
Action (motion) module extracted from vendor ArmPi Functions scripts.

Goal:
- Keep vendor code untouched
- Wrap arm movements + gripper control as a clean class
- Use it from demo scripts (arm/demos/*)

This uses the vendor ArmIK + Board layers. On the real arm, many calls
need sudo due to I2C/GPIO access, so run demos as:
  sudo python3 arm/demos/demo_action.py
"""
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

# Prefer the vendor install path used by their scripts
if os.path.isdir("/home/pi/ArmPi"):
    sys.path.append("/home/pi/ArmPi")
else:
    repo_vendor = os.path.join(os.path.dirname(__file__), "..", "vendor", "ArmPi")
    sys.path.append(os.path.abspath(repo_vendor))

import HiwonderSDK.Board as Board  # type: ignore
from ArmIK.ArmMoveIK import ArmIK  # type: ignore
from ArmIK.Transform import getAngle  # type: ignore


@dataclass
class PlacePose:
    x: float
    y: float
    z: float = 1.5


class Motion:
    """
    Clean interface for the manipulator.
    Mirrors core primitives used in ColorTracking/ColorSorting:
    - home pose
    - open/close gripper
    - rotate wrist (servo2) by computed angle
    - move to world coordinates using ArmIK.setPitchRangeMoving
    """
    def __init__(self,
                 servo_gripper_closed: int = 500,
                 gripper_open_delta: int = 280,
                 wrist_center: int = 500):
        self.AK = ArmIK()
        self.servo1 = int(servo_gripper_closed)
        self.open_delta = int(gripper_open_delta)
        self.wrist_center = int(wrist_center)

    def open_gripper(self, duration_ms: int = 500) -> None:
        Board.setBusServoPulse(1, self.servo1 - self.open_delta, duration_ms)
        time.sleep(duration_ms / 1000.0 + 0.1)

    def close_gripper(self, duration_ms: int = 500) -> None:
        Board.setBusServoPulse(1, self.servo1, duration_ms)
        time.sleep(duration_ms / 1000.0 + 0.1)

    def set_wrist_angle_for(self, x: float, y: float, rotation_angle_deg: float, duration_ms: int = 500) -> int:
        """Compute and set wrist servo pulse to align with block rotation angle."""
        pulse = int(getAngle(x, y, rotation_angle_deg))
        Board.setBusServoPulse(2, pulse, duration_ms)
        time.sleep(duration_ms / 1000.0 + 0.1)
        return pulse

    def wrist_centered(self, duration_ms: int = 500) -> None:
        Board.setBusServoPulse(2, self.wrist_center, duration_ms)
        time.sleep(duration_ms / 1000.0 + 0.1)

    def move_to(self,
                x: float, y: float, z: float,
                pitch: float = -90, roll: float = -90, yaw: float = 0,
                duration_ms: Optional[int] = None,
                speed: Optional[int] = None) -> Tuple[bool, float]:
        """
        Move to (x,y,z) in world coordinates.
        Returns (ok, seconds_waited).
        """
        if duration_ms is None:
            result = self.AK.setPitchRangeMoving((x, y, z), pitch, roll, yaw)
            if result is False:
                return False, 0.0
            wait_s = result[2] / 1000.0
        else:
            # vendor uses a last param sometimes as speed or duration; keep duration explicit
            result = self.AK.setPitchRangeMoving((x, y, z), pitch, roll, yaw, duration_ms)
            if result is False:
                return False, 0.0
            wait_s = duration_ms / 1000.0
        time.sleep(wait_s + 0.05)
        return True, wait_s

    def home(self) -> None:
        # vendor init pose similar to their initMove()
        self.wrist_centered()
        self.open_gripper(duration_ms=300)
        # Safe home-ish pose
        self.move_to(0, 10, 10, pitch=-30, roll=-30, yaw=-90, duration_ms=1500)

    def pick_and_place_simple(self,
                              pick_xy: Tuple[float, float],
                              place_pose: PlacePose,
                              approach_z: float = 5.0,
                              pick_z: float = 2.0) -> bool:
        """
        Minimal pick & place sequence (no tracking loop).
        Designed for a simple demo after perception gives (world_x, world_y).
        """
        x, y = pick_xy

        # Approach
        ok, _ = self.move_to(x, y - 2, approach_z, pitch=-90, roll=-90, yaw=0)
        if not ok:
            return False

        self.open_gripper()

        # Descend and grasp
        ok, _ = self.move_to(x, y, pick_z, pitch=-90, roll=-90, yaw=0, duration_ms=1000)
        if not ok:
            return False

        self.close_gripper()
        self.wrist_centered()

        # Lift
        self.move_to(x, y, 12, pitch=-90, roll=-90, yaw=0, duration_ms=1000)

        # Move to place
        ok, _ = self.move_to(place_pose.x, place_pose.y, 12, pitch=-90, roll=-90, yaw=0)
        if not ok:
            return False

        # Lower and release
        self.move_to(place_pose.x, place_pose.y, place_pose.z + 3, pitch=-90, roll=-90, yaw=0, duration_ms=500)
        self.move_to(place_pose.x, place_pose.y, place_pose.z, pitch=-90, roll=-90, yaw=0, duration_ms=1000)
        self.open_gripper(duration_ms=500)

        # Lift and go home
        self.move_to(place_pose.x, place_pose.y, 12, pitch=-90, roll=-90, yaw=0, duration_ms=800)
        self.home()
        return True
