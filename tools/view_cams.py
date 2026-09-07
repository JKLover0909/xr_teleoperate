"""View every robot camera stream side by side in a single window.

teleimager's own client (`python -m teleimager.image_client`) opens one OpenCV
window per camera. This shows the same streams as one horizontal strip instead.

    conda activate tv
    export PYTHONNOUSERSITE=1
    python /home/jkl/Projects/Humanoid/xr_teleoperate/tools/view_cams.py --host 192.168.123.164

Press q in the window to quit.

Only cameras with `enable_zmq: true` in the server's cam_config_server.yaml are
shown -- WebRTC-only cameras do not reach this client. A camera that stops
delivering frames keeps its slot and turns into a NO SIGNAL placeholder, so the
strip never reflows and a dead stream is obvious.
"""
import argparse
import socket
import time

import cv2
import numpy as np
import logging_mp

# Must run before anything calls getLogger(); importing teleimager does.
logging_mp.basicConfig(level=logging_mp.INFO)
logger_mp = logging_mp.getLogger(__name__)

from teleimager.image_client import ImageClient  # noqa: E402

# (config key, window label, ImageClient getter name)
CAMERAS = [
    ("head_camera", "HEAD", "get_head_frame"),
    ("left_wrist_camera", "LEFT WRIST", "get_left_wrist_frame"),
    ("right_wrist_camera", "RIGHT WRIST", "get_right_wrist_frame"),
]

WINDOW = "Robot Cameras"

# Cameras drawn rotated 90 degrees counter-clockwise. The wrist cameras are
# mounted sideways, so their streams arrive on their side; this only turns them
# upright for viewing and does not change what the server publishes or what
# gets recorded. Kept in step with ROTATE_CCW_CAMS in unitree_lerobot's
# data_editor_EN.py so the live view and the dataset player agree.
ROTATE_CCW = {"left_wrist_camera", "right_wrist_camera"}

# Subscriber threads need a moment to connect before the first frame lands;
# do not accuse the server of being down during that window.
STARTUP_GRACE = 3.0


def scale_to_height(frame, height):
    """Scale preserving aspect ratio, so a binocular head cam stays undistorted."""
    h, w = frame.shape[:2]
    if h == height:
        return frame
    return cv2.resize(frame, (max(1, round(w * height / h)), height), interpolation=cv2.INTER_AREA)


def placeholder(height, width, label, stale_for):
    tile = np.zeros((height, width, 3), np.uint8)
    lines = [f"{label}: NO SIGNAL"]
    if stale_for is not None:
        lines.append(f"last frame {stale_for:.0f}s ago")
    else:
        lines.append("no frame yet")
    y = (height // 2) - 10
    for line in lines:
        (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(tile, line, ((width - tw) // 2, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 60, 220), 2, cv2.LINE_AA)
        y += th + 14
    return tile


def server_reachable(host, ports, timeout=0.3):
    """TCP-connect to the publisher ports.

    A ZMQ PUB socket accepts connections whenever its process is alive, so this
    separates 'image_server died' (refused) from 'server up but a camera stopped
    producing frames' (accepted, yet no data arriving).
    """
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def banner(strip, text, colour):
    h, w = strip.shape[:2]
    bar_h = 46
    overlay = strip.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, strip, 0.35, 0, strip)
    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
    cv2.putText(strip, text, (max(12, (w - tw) // 2), h - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, colour, 2, cv2.LINE_AA)
    return strip


def annotate(tile, label, fps):
    cv2.rectangle(tile, (0, 0), (tile.shape[1] - 1, tile.shape[0] - 1), (255, 255, 255), 2)
    text = label if fps is None else f"{label}  {fps:5.1f} fps"
    for colour, thickness in ((0, 0, 0), 4), ((255, 255, 255), 2):
        cv2.putText(tile, text, (14, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, thickness, cv2.LINE_AA)
    return tile


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="192.168.123.164", help="IP of the teleimager server (PC2)")
    parser.add_argument("--height", type=int, default=480, help="height of each camera tile")
    parser.add_argument("--max-width", type=int, default=1920,
                        help="shrink the finished strip if it is wider than this")
    parser.add_argument("--no-rotate", action="store_true",
                        help=f"show every camera as received, without the 90-degree CCW "
                             f"correction applied to {', '.join(sorted(ROTATE_CCW))}")
    args = parser.parse_args()
    rotate = set() if args.no_rotate else ROTATE_CCW

    client = ImageClient(host=args.host, request_bgr=True)
    cam_config = client.get_cam_config()

    active = [(key, label, getattr(client, getter))
              for key, label, getter in CAMERAS
              if cam_config.get(key, {}).get("enable_zmq")]

    if not active:
        logger_mp.error("No camera has enable_zmq: true on the server -- nothing to show.")
        client.close()
        return

    logger_mp.info(f"Showing {len(active)} camera(s): {', '.join(label for _, label, _ in active)}")
    logger_mp.info("Press q to quit.")
    start_time = time.time()

    # Remember each slot's width so a dropped stream keeps its place in the strip.
    widths = {}
    last_ok = {}
    ports = [cam_config[key]["zmq_port"] for key, _, _ in active]
    probe_at = 0.0
    reachable = True
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    try:
        while True:
            now = time.time()
            tiles = []
            live = 0
            for key, label, getter in active:
                image = getter()
                if image is not None and image.bgr is not None:
                    live += 1
                    last_ok[key] = now
                    frame = image.bgr
                    if key in rotate:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    tile = scale_to_height(frame, args.height).copy()
                    widths[key] = tile.shape[1]
                    tiles.append(annotate(tile, label, image.fps))
                else:
                    # Fall back to the config's aspect ratio until we have seen a frame.
                    shape = cam_config[key].get("image_shape") or [args.height, args.height]
                    if key in rotate:            # rotation swaps the two dimensions
                        shape = [shape[1], shape[0]]
                    default_w = max(1, round(shape[1] * args.height / shape[0]))
                    stale_for = now - last_ok[key] if key in last_ok else None
                    tiles.append(placeholder(args.height, widths.get(key, default_w),
                                             label, stale_for))

            strip = np.hstack(tiles)

            # Every camera silent at once is almost never three simultaneous camera
            # faults -- it means the publisher process itself is gone. Probing the
            # ports says which, so the window does not blame the cameras for a
            # dead server. (A couple of seconds of silence at startup is normal
            # while the subscriber threads connect, hence the grace period.)
            if live == 0 and now - start_time > STARTUP_GRACE:
                if now - probe_at > 3.0:
                    reachable = server_reachable(args.host, ports)
                    probe_at = now
                strip = banner(
                    strip,
                    f"ALL CAMERAS SILENT - teleimager on {args.host} is "
                    + ("UP (ports open, no frames)" if reachable else "DOWN (ports refused)"),
                    (80, 80, 255),
                )
            elif live < len(active):
                dead = [label for (key, label, _) in active if key not in last_ok
                        or now - last_ok[key] > 1.0]
                strip = banner(strip, f"{len(active) - live} of {len(active)} cameras silent: "
                                      + ", ".join(dead), (80, 200, 255))
            if strip.shape[1] > args.max_width:
                scale = args.max_width / strip.shape[1]
                strip = cv2.resize(strip, (args.max_width, max(1, round(strip.shape[0] * scale))),
                                   interpolation=cv2.INTER_AREA)

            cv2.imshow(WINDOW, strip)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger_mp.info("Exiting on user request.")
                break
            time.sleep(0.002)
    except KeyboardInterrupt:
        logger_mp.info("Interrupted.")
    finally:
        client.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
