#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import cv2
import numpy as np

# Prefer vendor install path
if os.path.isdir("/home/pi/ArmPi"):
    sys.path.append("/home/pi/ArmPi")
else:
    repo_vendor = os.path.join(os.path.dirname(__file__), "..", "vendor", "ArmPi")
    sys.path.append(os.path.abspath(repo_vendor))

from LABConfig import color_range
from ArmIK.Transform import getROI, getCenter, convertCoordinate
from CameraCalibration.CalibrationConfig import square_length, calibration_size

# Vendor uses calibration_size for board, but resize size is usually fixed
# Most ArmPi demos use (640, 480)
size = (640, 480)


class Perception:

    def __init__(self, target_colors=("red", "green", "blue"), min_area=2500):
        self.target_colors = target_colors
        self.min_area = min_area

    def _area_max_contour(self, contours):
        contour_area_max = 0
        area_max_contour = None

        for c in contours:
            a = abs(cv2.contourArea(c))
            if a > contour_area_max:
                contour_area_max = a
                if a > 300:
                    area_max_contour = c

        return area_max_contour, contour_area_max

    def detect_largest(self, frame_bgr):

        img_copy = frame_bgr.copy()

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

            best = {
                "color": c,
                "area": area,
                "box": box,
                "center_px": (int(cx), int(cy)),
                "world_xy": (float(wx), float(wy))
            }

        return best

    def annotate(self, frame_bgr, det):

        if det is None:
            return frame_bgr

        cv2.drawContours(frame_bgr, [det["box"]], -1, (0, 255, 255), 2)

        text = "{} ({:.1f},{:.1f})".format(
            det["color"],
            det["world_xy"][0],
            det["world_xy"][1]
        )

        cv2.putText(
            frame_bgr,
            text,
            (det["center_px"][0], det["center_px"][1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2
        )

        return frame_bgr