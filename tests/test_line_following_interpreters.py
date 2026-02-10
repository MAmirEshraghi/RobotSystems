import numpy as np

from students.rob.line_following.grayscale.interpreter import GrayscaleInterpreter
from students.rob.line_following.camera.interpreter import CameraInterpreter

def test_grayscale_interpreter_dark_line_basic():
    interp = GrayscaleInterpreter(polarity="dark_line", sensitivity=0.0, smooth=1.0, deadband=0.0)
    # dark line under left sensor => left reading smaller
    offset = interp.interpret([100, 300, 320])
    assert offset > 0.2

    offset = interp.interpret([320, 300, 100])
    assert offset < -0.2

    offset = interp.interpret([200, 100, 210])
    # center sees darkest => near 0
    assert abs(offset) < 0.4

def test_camera_interpreter_synthetic():
    interp = CameraInterpreter(polarity="dark_line", thresh=120, smooth=1.0, roi_height_frac=1.0)
    # Create synthetic image with a vertical dark line slightly left of center
    h, w = 240, 320
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    x_line = int(w * 0.35)
    img[:, x_line-3:x_line+3, :] = 0
    offset, meta = interp.interpret(img)
    assert offset < 0  # line left => need steer left => positive? depends on convention
    # Our convention: + means line left, so offset should be negative here? Wait: raw=(x_mean-center)/center, x_mean<center => negative.
    # Controller will steer negative angle, which on Picarx typically turns wheels right; might be inverted depending on steering convention.
    # So this test just asserts sign matches math.
