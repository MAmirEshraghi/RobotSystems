from dataclasses import dataclass
from typing import List

@dataclass
class GrayscaleInterpreter:
    """Convert 3 grayscale readings into a normalized lateral offset in [-1, 1].

    polarity:
      - "dark_line": line is darker than floor (common: black tape on light floor)
      - "light_line": line is lighter than floor (white tape on dark floor)

    sensitivity:
      minimum normalized contrast needed to trust left vs right decision.
    """
    polarity: str = "dark_line"
    sensitivity: float = 0.10  # 10% contrast
    deadband: float = 0.05     # ignore tiny offsets
    smooth: float = 0.35       # EMA smoothing factor

    def __post_init__(self):
        if self.polarity not in ("dark_line", "light_line"):
            raise ValueError("polarity must be 'dark_line' or 'light_line'")
        self._offset_ema = 0.0

    def _score(self, v: float) -> float:
        # For dark line, smaller values mean "more line".
        # For light line, larger values mean "more line".
        return (-v) if self.polarity == "dark_line" else (v)

    def interpret(self, values: List[int]) -> float:
        left, center, right = [float(x) for x in values]
        mean = (left + center + right) / 3.0
        # Normalize around mean to reduce lighting sensitivity
        eps = 1e-6
        nl = (left - mean) / (abs(mean) + eps)
        nc = (center - mean) / (abs(mean) + eps)
        nr = (right - mean) / (abs(mean) + eps)

        # Convert to "line-likelihood" score
        sl, sc, sr = self._score(nl), self._score(nc), self._score(nr)

        # If center strongly wins, treat as centered
        # If left vs right wins, output +/-1 with a mild continuous blend
        # Contrast check to avoid noise
        best = max(sl, sc, sr)
        second = sorted([sl, sc, sr])[-2]
        if (best - second) < self.sensitivity:
            raw = 0.0
        else:
            # Weighted position: left=+1, center=0, right=-1
            # Use softmax-like positive weights (shift by min)
            m = min(sl, sc, sr)
            wl, wc, wr = (sl - m), (sc - m), (sr - m)
            s = wl + wc + wr + eps
            raw = (wl * 1.0 + wc * 0.0 + wr * -1.0) / s

        # Deadband
        if abs(raw) < self.deadband:
            raw = 0.0

        # Smooth (EMA)
        self._offset_ema = (1.0 - self.smooth) * self._offset_ema + self.smooth * raw
        # Clamp
        if self._offset_ema > 1.0:
            self._offset_ema = 1.0
        if self._offset_ema < -1.0:
            self._offset_ema = -1.0
        return self._offset_ema
