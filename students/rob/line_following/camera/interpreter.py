from dataclasses import dataclass
from typing import Tuple, Optional

import numpy as np
import cv2

@dataclass
class CameraInterpreter:
    """Find line center from a frame and return offset in [-1,1].

    Strategy (simple + reliable for demos):
      - crop a bottom ROI
      - grayscale + blur
      - threshold to isolate line
      - compute centroid x of mask pixels
    """
    polarity: str = "dark_line"     # "dark_line" or "light_line"
    roi_height_frac: float = 0.40  # bottom 40% of frame
    thresh: int = 110              # starting threshold; tune on your floor
    smooth: float = 0.25

    def __post_init__(self):
        if self.polarity not in ("dark_line", "light_line"):
            raise ValueError("polarity must be 'dark_line' or 'light_line'")
        self._offset_ema = 0.0

    def interpret(self, frame_bgr: np.ndarray) -> Tuple[float, Optional[dict]]:
        h, w = frame_bgr.shape[:2]
        roi_h = int(h * self.roi_height_frac)
        y0 = h - roi_h
        roi = frame_bgr[y0:h, :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.polarity == "dark_line":
            _, mask = cv2.threshold(gray, self.thresh, 255, cv2.THRESH_BINARY_INV)
        else:
            _, mask = cv2.threshold(gray, self.thresh, 255, cv2.THRESH_BINARY)

        # clean small noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        xs = np.where(mask > 0)[1]  # x indices of white pixels
        if xs.size == 0:
            raw = 0.0
            meta = {"roi_y0": y0, "roi": roi, "mask": mask, "found": False}
        else:
            x_mean = float(xs.mean())
            raw = (x_mean - (w / 2.0)) / (w / 2.0)  # [-1,1]
            raw = max(-1.0, min(1.0, raw))
            meta = {"roi_y0": y0, "roi": roi, "mask": mask, "found": True, "x_mean": x_mean}

        # Smooth
        self._offset_ema = (1.0 - self.smooth) * self._offset_ema + self.smooth * raw
        return self._offset_ema, meta
