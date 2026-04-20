import logging
import os

import cv2
import mss
import numpy as np

from .settings import SCREENSHOTS_DIR

logger = logging.getLogger(__name__)

ANNOTATION_BOX_HALF = 32
FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN = (0, 255, 0)


def take_screenshot() -> np.ndarray:
    """Capture the full desktop and return it as an RGB numpy array."""
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[0])
    return cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2RGB)


def annotate_screenshot(
    screenshot: np.ndarray,
    center: tuple[int, int],
    label: str,
    confidence: float,
    method: str,
) -> np.ndarray:
    """Draw a detection box and overlay confidence, coordinates, and method on the screenshot."""
    x, y = center
    annotated = screenshot.copy()

    tl = (x - ANNOTATION_BOX_HALF, y - ANNOTATION_BOX_HALF)
    br = (x + ANNOTATION_BOX_HALF, y + ANNOTATION_BOX_HALF)
    cv2.rectangle(annotated, tl, br, GREEN, 2)

    lines = [
        f"{label}",
        f"Method : {method}",
        f"Confidence: {confidence * 100:.1f}%",
        f"Coords : ({x}, {y})",
    ]
    line_height = 18
    text_y = tl[1] - (len(lines) * line_height) - 4
    for line in lines:
        cv2.putText(annotated, line, (tl[0], text_y), FONT, 0.5, GREEN, 1, cv2.LINE_AA)
        text_y += line_height

    return annotated


def save_annotated_screenshot(screenshot: np.ndarray, post_id: int) -> None:
    """Save the annotated screenshot as annotated_post{id}.png in screenshots/."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOTS_DIR, f"annotated_post{post_id}.png")
    cv2.imwrite(path, cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR))
    logger.info("Saved annotated screenshot to %s", path)
