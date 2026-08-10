import cv2
import numpy as np


QUAD_CAMERA_LABELS = (
    "HEAD",
    "HEAD 2 (NO CAMERA)",
    "LEFT WRIST",
    "RIGHT WRIST",
)


def _fit_frame(frame, slot_shape):
    slot_height, slot_width = slot_shape
    if frame is None or frame.size == 0:
        return np.zeros((slot_height, slot_width, 3), dtype=np.uint8)

    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.shape[2] == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    frame_height, frame_width = frame.shape[:2]
    scale = min(slot_width / frame_width, slot_height / frame_height)
    resized_width = max(1, round(frame_width * scale))
    resized_height = max(1, round(frame_height * scale))
    resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)

    fitted = np.zeros((slot_height, slot_width, 3), dtype=np.uint8)
    x_offset = (slot_width - resized_width) // 2
    y_offset = (slot_height - resized_height) // 2
    fitted[y_offset:y_offset + resized_height, x_offset:x_offset + resized_width] = resized
    return fitted


def compose_quad_camera_view(head_frame, left_wrist_frame, right_wrist_frame, slot_shape):
    """Build head/blank/left-wrist/right-wrist 2x2 BGR view for XR display."""
    slots = [
        _fit_frame(head_frame, slot_shape),
        _fit_frame(None, slot_shape),
        _fit_frame(left_wrist_frame, slot_shape),
        _fit_frame(right_wrist_frame, slot_shape),
    ]

    for slot, label in zip(slots, QUAD_CAMERA_LABELS):
        cv2.rectangle(slot, (0, 0), (slot.shape[1] - 1, slot.shape[0] - 1), (255, 255, 255), 2)
        cv2.putText(slot, label, (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(slot, label, (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    return np.vstack((np.hstack(slots[:2]), np.hstack(slots[2:])))
