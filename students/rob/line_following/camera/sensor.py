from typing import Optional
import numpy as np

class CameraSensor:
    """Camera frame provider.

    Tries (in order):
      1) picamera2 (recommended on Pi OS Bookworm)
      2) OpenCV VideoCapture(0)

    Returns BGR frames (OpenCV convention).
    """
    def __init__(self, width: int = 320, height: int = 240, fps: int = 30):
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)

        self._mode = None
        self._cap = None
        self._picam2 = None

        # Try picamera2 first
        try:
            from picamera2 import Picamera2  # type: ignore
            import cv2  # noqa: F401
            self._picam2 = Picamera2()
            cfg = self._picam2.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"}
            )
            self._picam2.configure(cfg)
            self._picam2.start()
            self._mode = "picamera2"
        except Exception:
            self._picam2 = None

        if self._mode is None:
            import cv2
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            self._cap = cap
            self._mode = "opencv"

    def read(self) -> np.ndarray:
        import cv2
        if self._mode == "picamera2":
            # picamera2 gives RGB; convert to BGR
            frame_rgb = self._picam2.capture_array()
            return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        else:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                raise RuntimeError("Camera read failed")
            return frame

    def close(self):
        try:
            if self._cap is not None:
                self._cap.release()
        except Exception:
            pass
        try:
            if self._picam2 is not None:
                self._picam2.stop()
        except Exception:
            pass
