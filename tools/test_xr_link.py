"""Standalone XR-link check: no robot, no PC2, no camera.

Serves a synthetic image to the headset over the televuer websocket and prints
the head / controller / hand poses it receives back. Use it to confirm the
HTTPS certificate and the headset connection work before wiring up the robot.

    source /home/jkl/miniconda3/etc/profile.d/conda.sh
    conda activate tv
    export PYTHONNOUSERSITE=1
    python /home/jkl/Projects/Humanoid/xr_teleoperate/tools/test_xr_link.py          # controllers
    python /home/jkl/Projects/Humanoid/xr_teleoperate/tools/test_xr_link.py --hand   # hand tracking

Then open  https://<host-ip>:8012/?ws=wss://<host-ip>:8012  in the headset
browser, accept the certificate warning, and press "Virtual Reality".
Non-zero poses in the log mean the XR link works.
"""
import argparse
import time

import numpy as np
import logging_mp
from televuer import TeleVuer

logging_mp.basicConfig(level=logging_mp.INFO)
logger_mp = logging_mp.getLogger(__name__)

IMG_SHAPE = (480, 1280)  # binocular: left and right eye side by side


def make_test_frame(tick: int) -> np.ndarray:
    """A moving colour gradient, so a frozen stream is obvious at a glance."""
    h, w = IMG_SHAPE
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :, 0] = (np.linspace(0, 255, w, dtype=np.int32) + tick * 4) % 256
    img[:, :, 1] = (np.linspace(0, 255, h, dtype=np.int32)[:, None]) % 256
    img[:, : w // 2, 2] = 80    # left eye tinted
    img[:, w // 2 :, 2] = 200   # right eye tinted
    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hand", action="store_true", help="hand tracking instead of controllers")
    args = parser.parse_args()

    tv = TeleVuer(use_hand_tracking=args.hand,
                  binocular=True,
                  img_shape=IMG_SHAPE,
                  display_fps=30.0,
                  display_mode="immersive",
                  zmq=True,      # frames come from render_to_xr via shared memory
                  webrtc=False,
                  webrtc_url=None)

    logger_mp.info("televuer up on https://0.0.0.0:8012 -- connect the headset, then Ctrl-C to stop")
    tick = 0
    try:
        while True:
            tv.render_to_xr(make_test_frame(tick))
            if tick % 30 == 0:
                logger_mp.info(f"head_pose:\n{tv.head_pose}")
                logger_mp.info(f"left_arm_pose:\n{tv.left_arm_pose}")
                logger_mp.info(f"right_arm_pose:\n{tv.right_arm_pose}")
            tick += 1
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        logger_mp.info("stopped")


if __name__ == "__main__":
    main()
