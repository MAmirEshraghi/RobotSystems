#!/usr/bin/env python3
# coding: utf-8
"""
Perception module extracted from the vendor ArmPi Functions scripts.

Goal:
- Keep vendor code untouched under arm/vendor/ArmPi
- Put perception (vision + coordinate conversion) here as a clean class
- Use it from small demo scripts (arm/demos/*)

Runs on the Arm Pi image. It tries /home/pi/ArmPi first (vendor default),
and falls back to the repo copy if you run from RobotSystems.
"""
import os
import sys
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# Prefer the vendor install path used by their scripts
if os.path.isdir("/home/pi/ArmPi"):
    sys.path.append("/home/pi/ArmPi")
else:
    # fallback: repo snapshot
    repo_vendor = os.path.join(os.path.dirname(__file__), "..", "vendor", "ArmPi")
    sys.path.append(os.path.abspath(repo_vendor))

import cv2  # type: ignore
import numpy as np  # type: ignore

from LABConfig import color_range  # LAB thresholds
from ArmIK.Transform import getROI, getCenter, convertCoordinate  # coordinate helpers
from CameraCalibration.CalibrationConfig import square_length, size  # image resize + board size


@dataclass
class Detection:
    color: str
    area: float
    box: np.ndarray              # 4x2 int points (image coords in original frame)
    center_px: Tuple[int, int]   # center in resized space
    world_xy: Tuple[float, float]


class Perception:
    """
    Detects the largest block of target colors in the current frame.

    This mirrors the vendor approach in ColorTracking.py:
    - resize -> blur -> LAB -> inRange -> open/close -> contours -> max contour
    - minAreaRect -> box -> ROI -> refined center -> pixel->world conversion
    """
    def __init__(self,
                 target_colors: Sequence[str] = ("red", "green", "blue"),
                 min_area: float = 2500.0):
        self.target_colors = tuple(target_colors)
        self.min_area = float(min_area)

    @staticmethod
    def _area_max_contour(contours) -> Tuple[Optional[np.ndarray], float]:
        """Return (largest_contour, area). Vendor filters small areas to reduce noise."""
        contour_area_max = 0.0
        area_max_contour = None
        for c in contours:
            a = float(abs(cv2.contourArea(c)))
            if a > contour_area_max:
                contour_area_max = a
                if a > 300:  # vendor threshold to filter interference
                    area_max_contour = c
        return area_max_contour, contour_area_max

    def detect_largest(self, frame_bgr: np.ndarray) -> Optional[Detection]:
        """
        Returns the best detection (largest area) or None.
        frame_bgr is a full-resolution BGR frame (e.g., 640x480).
        """
        img_copy = frame_bgr.copy()

        # Resize to vendor "size" and smooth
        frame_resize = cv2.resize(img_copy, size, interpolation=cv2.INTER_NEAREST)
        frame_gb = cv2.GaussianBlur(frame_resize, (11, 11), 11)
        frame_lab = cv2.cvtColor(frame_gb, cv2.COLOR_BGR2LAB)

        best = None

        for c in self.target_colors:
            if c not in color_range:
                continue

            mask = cv2.inRange(frame_lab, color_range[c][0], color_range[c][1])
            opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((6, 6), np.uint8))
            closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((6, 6), np.uint8))
            contours = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]
            area_max_contour, area = self._area_max_contour(contours)

            if area_max_contour is None or area < self.min_area:
                continue

            rect = cv2.minAreaRect(area_max_contour)
            box = np.int0(cv2.boxPoints(rect))

            roi = getROI(box)
            cx, cy = getCenter(rect, roi, size, square_length)
            wx, wy = convertCoordinate(cx, cy, size)

            det = Detection(
                color=c,
                area=area,
                box=box,
                center_px=(int(cx), int(cy)),
                world_xy=(float(wx), float(wy)),
            )

            if best is None or det.area > best.area:
                best = det

        return best

    @staticmethod
    def annotate(frame_bgr: np.ndarray, det: Optional[Detection]) -> np.ndarray:
        """Draw detection on the frame and return a copy."""
        out = frame_bgr.copy()
        h, w = out.shape[:2]
        # crosshair like vendor
        cv2.line(out, (0, h // 2), (w, h // 2), (0, 0, 200), 1)
        cv2.line(out, (w // 2, 0), (w // 2, h), (0, 0, 200), 1)

        if det is None:
            cv2.putText(out, "No target detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
            return out

        cv2.drawContours(out, [det.box], -1, (0, 255, 0), 2)
        txt = f"{det.color}  world=({det.world_xy[0]:.1f},{det.world_xy[1]:.1f})  area={det.area:.0f}"
        x = int(min(det.box[:, 0]))
        y = int(max(20, min(det.box[:, 1]) - 10))
        cv2.putText(out, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return out
