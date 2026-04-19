import logging
import os

import cv2
import mss
import numpy as np

from .settings import SCREENSHOTS_DIR

logger = logging.getLogger(__name__)

ANNOTATION_BOX_HALF = 32


def take_screenshot() -> np.ndarray:
    """Capture the full desktop and return it as an RGB numpy array."""
    logger.info("Taking screenshot...")
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[0])
    return cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2RGB)


def annotate_screenshot(screenshot: np.ndarray, center: tuple[int, int], label: str) -> np.ndarray:
    """Draw a green bounding box and label on a copy of the screenshot."""
    x, y = center
    annotated = screenshot.copy()
    tl = (x - ANNOTATION_BOX_HALF, y - ANNOTATION_BOX_HALF)
    br = (x + ANNOTATION_BOX_HALF, y + ANNOTATION_BOX_HALF)
    cv2.rectangle(annotated, tl, br, (0, 255, 0), 2)
    cv2.putText(annotated, label, (tl[0], tl[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return annotated


def save_annotated_screenshot(screenshot: np.ndarray, post_id: int) -> None:
    """Save an annotated screenshot as post_{id}_annotated.png in screenshots/."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOTS_DIR, f"post_{post_id}_annotated.png")
    cv2.imwrite(path, cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR))
    logger.info("Saved annotated screenshot to %s", path)
